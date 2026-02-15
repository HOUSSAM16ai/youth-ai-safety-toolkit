import asyncio
import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# --- 1. ENVIRONMENT BOOTSTRAP ---
# Ensure we can import the app modules
sys.path.append(os.getcwd())

# REMOVED: from app.core.engine_factory import FatalEngineError, create_unified_async_engine
from sqlmodel import SQLModel

from app.core.config import get_settings

settings = get_settings()

# --- 2. LOGGING CONFIGURATION ---
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# --- 3. METADATA CONFIGURATION ---
target_metadata = SQLModel.metadata

# --- 4. MIGRATION MODES ---

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """
    Run migrations using a synchronous connection.
    This is called by both synchronous and asynchronous wrappers.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Create engine directly using sqlalchemy.ext.asyncio
    # We apply the same critical settings as the app (e.g. statement_cache_size=0 for Supabase)

    connect_args = {}
    # Apply Supabase/PgBouncer compatibility fix if using PostgreSQL
    # Note: asyncpg requires prepared_statement_cache_size=0 alongside statement_cache_size=0
    # to fully disable prepared statements for transaction poolers.
    if "postgresql" in settings.DATABASE_URL or "asyncpg" in settings.DATABASE_URL:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0

    connectable = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        future=True,
        poolclass=pool.NullPool,  # NullPool is used for migrations to avoid locking
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # Check if we are running in an async loop (unlikely for standard alembic CLI, but possible)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        logger.warning("Alembic is running inside an existing event loop.")
        # If already in a loop, we must await the task
        asyncio.ensure_future(run_async_migrations())
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
