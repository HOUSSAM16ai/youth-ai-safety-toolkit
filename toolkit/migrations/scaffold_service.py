import argparse
from pathlib import Path

# --- Templates ---

ALEMBIC_INI_TEMPLATE = """# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = migrations

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false


# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

ENV_PY_TEMPLATE = """import asyncio
import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# --- 1. ENVIRONMENT BOOTSTRAP ---
# Ensure we can import the app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../.."))
sys.path.append(root_dir)

# Import Service Specific Models and Settings
# adjustments may be needed depending on service structure
try:
    from microservices.{service_name}.models import *  # noqa
    from microservices.{service_name}.settings import get_settings
except ImportError as e:
    print(f"Error importing service modules: {{e}}")
    sys.exit(1)

settings = get_settings()

# --- 2. LOGGING CONFIGURATION ---
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# --- 3. METADATA CONFIGURATION ---
target_metadata = SQLModel.metadata

# --- 4. SCHEMA CONFIGURATION ---
target_schema = "{schema_name}"

# --- 5. MIGRATION MODES ---

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        # Only include tables in the target schema
        if object.schema != target_schema:
            return False
    return True

def run_migrations_offline() -> None:
    \"\"\"Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    \"\"\"
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={{"paramstyle": "named"}},
        compare_type=True,
        version_table_schema=target_schema,
        include_schemas=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        version_table_schema=target_schema,
        include_schemas=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    \"\"\"Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    \"\"\"

    connect_args = {{}}
    if "postgresql" in settings.DATABASE_URL or "asyncpg" in settings.DATABASE_URL:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0

    connectable = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        future=True,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        # Set search path to target schema
        if "postgresql" in settings.DATABASE_URL or "asyncpg" in settings.DATABASE_URL:
            await connection.execute(text(f"SET search_path TO {{target_schema}}"))
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    \"\"\"Run migrations in 'online' mode.\"\"\"

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        logger.warning("Alembic is running inside an existing event loop.")
        asyncio.ensure_future(run_async_migrations())
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""

SCRIPT_PY_MAKO_TEMPLATE = """\"\"\"${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

\"\"\"
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
"""


def scaffold_service(service_name: str, schema_name: str):
    root_dir = Path(__file__).resolve().parent.parent.parent
    service_dir = root_dir / "microservices" / service_name

    if not service_dir.exists():
        print(f"Service directory {service_dir} does not exist.")
        return

    migrations_dir = service_dir / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    # versions dir
    (migrations_dir / "versions").mkdir(exist_ok=True)

    # Write alembic.ini
    with open(service_dir / "alembic.ini", "w") as f:
        f.write(ALEMBIC_INI_TEMPLATE)

    # Write env.py
    env_py_content = ENV_PY_TEMPLATE.format(service_name=service_name, schema_name=schema_name)

    with open(migrations_dir / "env.py", "w") as f:
        f.write(env_py_content)

    # Write script.py.mako
    with open(migrations_dir / "script.py.mako", "w") as f:
        f.write(SCRIPT_PY_MAKO_TEMPLATE)

    print(f"Scaffolded migrations for {service_name} with schema {schema_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("service_name", help="Name of the service (folder name)")
    parser.add_argument("schema_name", help="Name of the database schema")
    args = parser.parse_args()

    scaffold_service(args.service_name, args.schema_name)
