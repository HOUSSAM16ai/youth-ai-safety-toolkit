"""
Idempotency Middleware for CogniForge.

Ensures that API requests with the same 'Idempotency-Key' header are processed only once.
This is critical for preventing duplicate missions or side-effects in a distributed system.
"""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import Request, Response
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.settings.base import get_settings

logger = logging.getLogger(__name__)


async def _async_iterator_wrapper(content: bytes) -> AsyncIterator[bytes]:
    yield content


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self.redis: Redis | None = None
        # Initialize Redis connection if URL is available
        if self.settings.REDIS_URL:
            try:
                self.redis = Redis.from_url(
                    self.settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2
                )
            except Exception as e:
                logger.error(f"Failed to initialize Redis for IdempotencyMiddleware: {e}")
        else:
            logger.warning("REDIS_URL not set. Idempotency middleware disabled.")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 1. Bypass if Redis is not configured
        if not self.redis:
            return await call_next(request)

        # 2. Check for Idempotency-Key header
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        # 3. Create a unique cache key based on key + method + path
        cache_key = f"idempotency:{idempotency_key}:{request.method}:{request.url.path}"

        # 4. Attempt to acquire lock atomically
        # set(..., nx=True) returns True if key was set (lock acquired), None/False otherwise
        lock_acquired = await self.redis.set(cache_key, "PROCESSING", ex=60, nx=True)

        if lock_acquired:
            # We own the request processing
            try:
                # 6. Process request
                response = await call_next(request)

                # 7. Cache successful responses
                if 200 <= response.status_code < 300:
                    # Capture body
                    response_body_chunks = []
                    async for chunk in response.body_iterator:
                        response_body_chunks.append(chunk)

                    body_content = b"".join(response_body_chunks)

                    # Restore iterator for the actual response
                    response.body_iterator = _async_iterator_wrapper(body_content)

                    try:
                        # Attempt to parse JSON
                        json_body = json.loads(body_content.decode("utf-8"))

                        # Store in Redis (24h expiry)
                        cache_data = {
                            "status_code": response.status_code,
                            "body": json_body,
                            "headers": dict(response.headers),
                        }
                        # Overwrite "PROCESSING" with result
                        await self.redis.set(
                            cache_key, json.dumps(cache_data), ex=86400
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Not a JSON response, release lock but don't cache
                        await self.redis.delete(cache_key)
                else:
                    # For errors, release lock so client can retry
                    await self.redis.delete(cache_key)

                return response

            except Exception as e:
                # Release lock on exception
                if self.redis:
                    await self.redis.delete(cache_key)
                raise e

        else:
            # 5. Lock failed - Key exists. Check if it's PROCESSING or a Result.
            cached_value = await self.redis.get(cache_key)

            if cached_value == "PROCESSING":
                # 409 Conflict: Request is currently being processed
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": "Request with this Idempotency-Key is currently being processed"
                    },
                )

            if cached_value:
                try:
                    # Return cached response
                    data = json.loads(cached_value)
                    return JSONResponse(
                        status_code=data["status_code"],
                        content=data["body"],
                        headers=data.get("headers", {}),
                    )
                except json.JSONDecodeError:
                    logger.error(f"Corrupted idempotency cache for key {cache_key}")
                    # If corrupted, we could delete and retry, but let's return error for safety
                    return JSONResponse(
                        status_code=500,
                        content={"detail": "Idempotency cache corrupted"},
                    )

            # Edge case: Key expired or deleted between set(nx) and get()
            # Retry processing? For safety, return 409 to ask client to retry.
            return JSONResponse(
                status_code=409,
                content={"detail": "Idempotency check failed, please retry"},
            )
