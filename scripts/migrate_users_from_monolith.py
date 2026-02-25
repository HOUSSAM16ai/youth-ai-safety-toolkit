import asyncio
import logging
import os
import sys

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine

# Add root directory to path to allow imports
sys.path.append(os.getcwd())

from microservices.user_service.models import SQLModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

# Default to Docker network defaults for internal migration
SOURCE_DB_URL = os.getenv(
    "SOURCE_DB_URL", "postgresql+asyncpg://postgres:password@postgres-core:5432/core_db"
)
DEST_DB_URL = os.getenv(
    "DEST_DB_URL",
    "postgresql+asyncpg://postgres:password@postgres-user:5432/user_db?options=-c%20search_path%3Duser_service",
)


def get_engine(url_str):
    url = make_url(url_str)
    connect_args = {}

    # Handle sslmode compatibility for asyncpg
    if "sslmode" in url.query:
        ssl_mode = url.query["sslmode"]
        # Remove sslmode from query to avoid kwargs error
        # SQLAlchemy 1.4/2.0 URL object modification
        query_dict = dict(url.query)
        del query_dict["sslmode"]
        url = url.set(query=query_dict)

        if ssl_mode == "require":
            connect_args["ssl"] = "require"
        elif ssl_mode == "disable":
            connect_args["ssl"] = False

    # If using sqlite, check_same_thread=False
    if "sqlite" in url.drivername:
        connect_args = {"check_same_thread": False}

    return create_async_engine(url, connect_args=connect_args)


async def migrate():
    logger.info("Starting migration...")
    logger.info(f"Source: {SOURCE_DB_URL}")
    logger.info(f"Dest: {DEST_DB_URL}")

    source_engine = get_engine(SOURCE_DB_URL)
    dest_engine = get_engine(DEST_DB_URL)

    try:
        # 0. Initialize Destination Schema
        logger.info("Initializing Destination Schema...")
        async with dest_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        async with source_engine.connect() as source_conn:
            async with dest_engine.connect() as dest_conn:
                # 1. Migrate Users
                logger.info("Migrating Users...")
                try:
                    result = await source_conn.execute(text("SELECT * FROM users"))
                    users = result.mappings().all()

                    if users:
                        columns = [
                            "id",
                            "external_id",
                            "full_name",
                            "email",
                            "password_hash",
                            "is_admin",
                            "is_active",
                            "status",
                            "created_at",
                            "updated_at",
                        ]
                        keys = users[0].keys()
                        valid_columns = [k for k in columns if k in keys]

                        cols_str = ", ".join(valid_columns)
                        vals_str = ", ".join([f":{k}" for k in valid_columns])

                        stmt = text(f"""
                            INSERT INTO users ({cols_str})
                            VALUES ({vals_str})
                            ON CONFLICT (id) DO NOTHING
                        """)

                        for user in users:
                            data = {k: user[k] for k in valid_columns}
                            await dest_conn.execute(stmt, data)

                        logger.info(f"Migrated {len(users)} users.")
                    else:
                        logger.info("No users found in source.")
                except Exception as e:
                    logger.error(f"Error migrating users: {e}")

                # 2. Migrate Roles
                logger.info("Migrating Roles...")
                try:
                    result = await source_conn.execute(text("SELECT * FROM roles"))
                    roles = result.mappings().all()
                    if roles:
                        valid_columns = ["id", "name", "description", "created_at", "updated_at"]
                        keys = roles[0].keys()
                        valid_columns = [k for k in valid_columns if k in keys]

                        cols_str = ", ".join(valid_columns)
                        vals_str = ", ".join([f":{k}" for k in valid_columns])

                        stmt = text(
                            f"INSERT INTO roles ({cols_str}) VALUES ({vals_str}) ON CONFLICT (id) DO NOTHING"
                        )
                        for role in roles:
                            await dest_conn.execute(stmt, {k: role[k] for k in valid_columns})
                        logger.info(f"Migrated {len(roles)} roles.")
                except Exception as e:
                    logger.error(f"Error migrating roles: {e}")

                # 3. Migrate Permissions
                logger.info("Migrating Permissions...")
                try:
                    result = await source_conn.execute(text("SELECT * FROM permissions"))
                    permissions = result.mappings().all()
                    if permissions:
                        valid_columns = ["id", "name", "description", "created_at", "updated_at"]
                        keys = permissions[0].keys()
                        valid_columns = [k for k in valid_columns if k in keys]

                        cols_str = ", ".join(valid_columns)
                        vals_str = ", ".join([f":{k}" for k in valid_columns])

                        stmt = text(
                            f"INSERT INTO permissions ({cols_str}) VALUES ({vals_str}) ON CONFLICT (id) DO NOTHING"
                        )
                        for perm in permissions:
                            await dest_conn.execute(stmt, {k: perm[k] for k in valid_columns})
                        logger.info(f"Migrated {len(permissions)} permissions.")
                except Exception as e:
                    logger.error(f"Error migrating permissions: {e}")

                # 4. Migrate UserRoles
                logger.info("Migrating User Roles...")
                try:
                    result = await source_conn.execute(text("SELECT * FROM user_roles"))
                    user_roles = result.mappings().all()
                    if user_roles:
                        valid_columns = ["user_id", "role_id", "created_at"]
                        keys = user_roles[0].keys()
                        valid_columns = [k for k in valid_columns if k in keys]

                        cols_str = ", ".join(valid_columns)
                        vals_str = ", ".join([f":{k}" for k in valid_columns])

                        stmt = text(
                            f"INSERT INTO user_roles ({cols_str}) VALUES ({vals_str}) ON CONFLICT (user_id, role_id) DO NOTHING"
                        )
                        for ur in user_roles:
                            await dest_conn.execute(stmt, {k: ur[k] for k in valid_columns})
                        logger.info(f"Migrated {len(user_roles)} user_roles.")
                except Exception as e:
                    logger.error(f"Error migrating user_roles: {e}")

                # 5. Migrate RolePermissions
                logger.info("Migrating Role Permissions...")
                try:
                    result = await source_conn.execute(text("SELECT * FROM role_permissions"))
                    role_perms = result.mappings().all()
                    if role_perms:
                        valid_columns = ["role_id", "permission_id", "created_at"]
                        keys = role_perms[0].keys()
                        valid_columns = [k for k in valid_columns if k in keys]

                        cols_str = ", ".join(valid_columns)
                        vals_str = ", ".join([f":{k}" for k in valid_columns])

                        stmt = text(
                            f"INSERT INTO role_permissions ({cols_str}) VALUES ({vals_str}) ON CONFLICT (role_id, permission_id) DO NOTHING"
                        )
                        for rp in role_perms:
                            await dest_conn.execute(stmt, {k: rp[k] for k in valid_columns})
                        logger.info(f"Migrated {len(role_perms)} role_permissions.")
                except Exception as e:
                    logger.error(f"Error migrating role_permissions: {e}")

                await dest_conn.commit()

    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        await source_engine.dispose()
        await dest_engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
