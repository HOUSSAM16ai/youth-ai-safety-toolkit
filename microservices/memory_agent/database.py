"""
وحدة قاعدة البيانات لوكيل الذاكرة.

تُبقي هذه الوحدة التهيئة محلية ومقيدة بحدود الخدمة.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from microservices.memory_agent.models import SQLModel
from microservices.memory_agent.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
runtime_settings = settings
if os.getenv("ENVIRONMENT") == "testing":
    runtime_settings = settings.model_copy(update={"DATABASE_URL": "sqlite+aiosqlite:///:memory:"})


def create_db_engine(*, database_url: str, echo: bool, service_name: str) -> AsyncEngine:
    """إنشاء محرك قاعدة البيانات الخاص بالوكيل بشكل صريح."""

    if not database_url:
        raise ValueError("DATABASE_URL غير مُعدّ لوكيل الذاكرة.")
    logger.info("🔌 Database Ready: %s", service_name)
    return create_async_engine(database_url, echo=echo, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """إنشاء مصنع جلسات لقاعدة بيانات وكيل الذاكرة."""

    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


engine = create_db_engine(
    database_url=runtime_settings.DATABASE_URL,
    echo=runtime_settings.DEBUG,
    service_name=runtime_settings.SERVICE_NAME,
)
async_session_factory = create_session_factory(engine)

_init_lock = asyncio.Lock()
_is_initialized = False


async def init_db() -> None:
    """
    تهيئة مخطط قاعدة البيانات.

    يُسمح بذلك فقط في التطوير والاختبار.
    """

    if settings.ENVIRONMENT not in ("development", "testing"):
        return

    # Deduplicate indexes to handle potential accumulation from multiple test runs
    for table in SQLModel.metadata.tables.values():
        unique_indexes = {}
        if hasattr(table, "indexes"):
            for index in table.indexes:
                if index.name not in unique_indexes:
                    unique_indexes[index.name] = index
            table.indexes = set(unique_indexes.values())

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def _ensure_initialized() -> None:
    """ضمان تهيئة قاعدة البيانات مرة واحدة فقط."""

    global _is_initialized
    if _is_initialized:
        return
    async with _init_lock:
        if _is_initialized:
            return
        await init_db()
        _is_initialized = True


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """توفير جلسة قاعدة بيانات ضمن حدود الخدمة."""

    await _ensure_initialized()
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
