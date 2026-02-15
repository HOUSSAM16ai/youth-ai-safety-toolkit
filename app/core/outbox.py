"""
Core Outbox implementation for CogniForge.

Provides utilities to transactionally write events to the outbox table.
This ensures that database changes and event publishing happen atomically.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings.base import get_settings
from app.domain.models.outbox import MissionOutbox

logger = logging.getLogger(__name__)

# Type definition for a session factory that returns an async context manager yielding an AsyncSession
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


async def emit_event(
    session: AsyncSession, event_type: str, payload: dict[str, Any]
) -> MissionOutbox:
    """
    Writes an event to the outbox within the current transaction.
    MUST be called within an active session transaction.
    """
    event = MissionOutbox(event_type=event_type, payload=payload)
    session.add(event)
    logger.debug(f"Outbox event staged: {event_type}")
    return event


async def process_outbox(session: AsyncSession, batch_size: int = 10):
    """
    Worker function to process pending outbox events.
    In a real production setup, this would run in a separate worker process.
    """
    settings = get_settings()
    redis_client: Redis | None = None

    if settings.REDIS_URL:
        try:
            redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to connect to Redis for Outbox: {e}")

    stmt = (
        select(MissionOutbox)
        .where(MissionOutbox.status == "PENDING")
        .order_by(MissionOutbox.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )

    result = await session.execute(stmt)
    events = result.scalars().all()

    for event in events:
        try:
            if redis_client:
                # Publish to Redis Stream
                stream_key = "cogniforge:events"
                # Redis Streams keys/values must be strings/bytes
                event_data = {
                    "event_type": event.event_type,
                    "payload": json.dumps(event.payload),
                    "event_id": str(event.id),
                    "timestamp": event.created_at.isoformat(),
                }
                await redis_client.xadd(stream_key, event_data)
                logger.info(f"Published event {event.id} ({event.event_type}) to {stream_key}")
            else:
                logger.warning(f"Redis not configured. Simulating publish for {event.event_type}")

            event.status = "PROCESSED"
            event.processed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Failed to process event {event.id}: {e}")
            event.status = "FAILED"
            event.retry_count += 1

    await session.commit()

    if redis_client:
        await redis_client.close()


async def run_outbox_worker(session_factory: SessionFactory, interval: float = 5.0):
    """
    Background task that continuously processes the outbox using the provided session factory.
    This allows the worker to be used by any microservice with its own DB connection.
    """
    logger.info("Starting Outbox Worker...")
    while True:
        try:
            async with session_factory() as session:
                await process_outbox(session)
        except Exception as e:
            logger.error(f"Outbox worker crashed (restarting in {interval}s): {e}")

        await asyncio.sleep(interval)
