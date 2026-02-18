import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from datetime import timedelta

from microservices.orchestrator_service.src.core.gateway.protocols.cache import (
    CacheProviderProtocol,
)

logger = logging.getLogger(__name__)


class InMemoryCacheProvider(CacheProviderProtocol):
    """
    موفر التخزين المؤقت في الذاكرة - In-Memory Cache Provider

    A high-performance, thread-safe, asynchronous in-memory caching implementation
    designed for the API Gateway. It uses an LRU (Least Recently Used) eviction
    policy and supports Time-To-Live (TTL) expiration.

    Design Principles (Harvard Standard):
    1.  **Thread Safety**: Uses asyncio primitives for safe concurrent access.
    2.  **Efficiency**: O(1) complexity for get/put operations using OrderedDict.
    3.  **Clarity**: Extensive Arabic/English documentation for beginners.

    Attributes:
        max_size_items (int): Maximum number of items to hold before eviction.
        default_ttl (int): Default expiration time in seconds.
    """

    def __init__(self, max_size_items: int = 1000, default_ttl: int = 300):
        """
        Initialize the in-memory cache.

        Args:
            max_size_items: The maximum number of entries to keep in memory.
            default_ttl: Default Time-To-Live in seconds for entries without explicit TTL.
        """
        self.max_size = max_size_items
        self.default_ttl = default_ttl

        # storage: maps key -> (value, expire_at_timestamp)
        self._storage: OrderedDict[str, tuple[object, float]] = OrderedDict()

        # Statistics
        self._stats = self._reset_stats()

        # Async lock for thread safety in async context
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> object | None:
        """
        استرجاع عنصر من الذاكرة المؤقتة.
        Retrieves an item if it exists and hasn't expired.
        """
        async with self._lock:
            if key not in self._storage:
                self._stats["misses"] += 1
                return None

            value, expire_at = self._storage[key]

            # Check expiration (time.time() is more efficient than datetime for simple comparisons)
            if time.time() > expire_at:
                # Expired: Remove lazily
                del self._storage[key]
                self._stats["misses"] += 1
                return None

            # Move to end (LRU policy: recently used is at the end)
            self._storage.move_to_end(key)
            self._stats["hits"] += 1
            return value

    async def put(self, key: str, value: object, ttl: int | timedelta | None = None) -> bool:
        """
        تخزين عنصر في الذاكرة.
        Stores an item. If cache is full, evicts the least recently used item.
        """
        ttl_seconds = self._normalize_ttl(ttl)

        expire_at = time.time() + ttl_seconds

        async with self._lock:
            # If updating existing key, remove it first to handle order correctly
            if key in self._storage:
                self._storage.move_to_end(key)
                self._storage[key] = (value, expire_at)
            else:
                self._storage[key] = (value, expire_at)

                # Check capacity
                if len(self._storage) > self.max_size:
                    # Pop first item (LRU is at the beginning of OrderedDict)
                    self._storage.popitem(last=False)
                    self._stats["evictions"] += 1

            self._stats["sets"] += 1
            return True

    def _normalize_ttl(self, ttl: int | timedelta | None) -> float:
        """
        تطبيع قيمة TTL إلى ثوانٍ قابلة للحساب.

        يضمن هذا التابع أن قيمة TTL غير سالبة لتجنب إدخالات غير صالحة.
        """
        if ttl is None:
            ttl_seconds = float(self.default_ttl)
        elif isinstance(ttl, timedelta):
            ttl_seconds = ttl.total_seconds()
        else:
            ttl_seconds = float(ttl)
        if ttl_seconds < 0:
            raise ValueError("TTL must be a non-negative value.")
        return ttl_seconds

    async def delete(self, key: str) -> bool:
        """
        حذف عنصر محدد.
        Removes a specific item from the cache.
        """
        async with self._lock:
            if key in self._storage:
                del self._storage[key]
                return True
            return False

    async def clear(self) -> bool:
        """
        مسح كافة البيانات.
        Clears the entire cache.
        """
        async with self._lock:
            self._storage.clear()
            self._stats = self._reset_stats()
            return True

    async def get_stats(self) -> dict[str, object]:
        """
        الحصول على الإحصائيات.
        Returns a snapshot of the cache statistics.
        """
        async with self._lock:
            total_ops = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_ops) if total_ops > 0 else 0.0

            return {
                "type": "InMemory",
                "size": len(self._storage),
                "max_size": self.max_size,
                "hit_rate": round(hit_rate, 4),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "sets": self._stats["sets"],
            }

    def _reset_stats(self) -> dict[str, int]:
        """
        إعادة تعيين عدادات التخزين المؤقت إلى الصفر.

        يحافظ هذا التابع على اتساق شكل الإحصائيات عبر دورة حياة المزود.
        """
        return {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}


class CacheFactory:
    """
    مصنع الذاكرة المؤقتة - Cache Factory

    Implements the Factory Pattern to instantiate the appropriate cache provider
    based on configuration.
    """

    @staticmethod
    def get_provider(provider_type: str = "memory", **kwargs) -> CacheProviderProtocol:
        if provider_type == "memory":
            return InMemoryCacheProvider(
                max_size_items=kwargs.get("max_size_items", 1000),
                default_ttl=kwargs.get("ttl", 300),
            )
        # Future: elif provider_type == "redis": ...
        logger.warning(f"Unknown provider type '{provider_type}', falling back to memory.")
        return InMemoryCacheProvider()


# Backwards compatibility helper for key generation
def generate_cache_key(data: object) -> str:
    """
    Generates a deterministic SHA256 hash for a dictionary or string.
    """
    try:
        key_data = json.dumps(data, sort_keys=True) if isinstance(data, dict) else str(data)
    except (TypeError, ValueError):
        key_data = str(data)

    return hashlib.sha256(key_data.encode()).hexdigest()
