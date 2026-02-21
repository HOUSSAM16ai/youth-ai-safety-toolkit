"""
وحدة قاعدة البيانات لخدمة المستخدمين.

تُبقي هذه الوحدة التهيئة محلية لخدمة المستخدمين دون اعتماد مشترك.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from microservices.user_service.models import SQLModel
from microservices.user_service.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
runtime_settings = settings
if os.getenv("ENVIRONMENT") == "testing":
    runtime_settings = settings.model_copy(update={"DATABASE_URL": "sqlite+aiosqlite:///:memory:"})


def create_db_engine(
    *,
    database_url: str,
    environment: str,
    echo: bool,
    service_name: str,
) -> AsyncEngine:
    """إنشاء محرك قاعدة البيانات بشكل صريح ومبسّط."""

    if not database_url:
        raise ValueError("DATABASE_URL غير مُعدّ لخدمة المستخدمين.")

    engine_args: dict[str, object] = {
        "echo": echo,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

    url_obj = make_url(database_url)
    if "sqlite" in url_obj.drivername:
        engine_args["connect_args"] = {"check_same_thread": False}
        logger.info("🔌 Database (SQLite): %s", service_name)
    elif "postgresql" in url_obj.drivername:
        if url_obj.drivername == "postgresql":
            url_obj = url_obj.set(drivername="postgresql+asyncpg")
            database_url = url_obj.render_as_string(hide_password=False)

        is_dev = environment in ("development", "testing")
        engine_args["pool_size"] = 5 if is_dev else 40
        engine_args["max_overflow"] = 10 if is_dev else 60
        logger.info("🔌 Database (Postgres): %s", service_name)

    return create_async_engine(database_url, **engine_args)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """إنشاء مصنع جلسات لقاعدة البيانات."""

    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


engine = create_db_engine(
    database_url=runtime_settings.DATABASE_URL,
    environment=runtime_settings.ENVIRONMENT,
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
    # This prevents "index already exists" errors in tests where metadata is shared
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
    global _is_initialized
    if _is_initialized:
        return
    async with _init_lock:
        if _is_initialized:
            return
        await init_db()
        _is_initialized = True


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """اعتماد جلسة قاعدة بيانات لخدمة المستخدمين."""

    await _ensure_initialized()
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
