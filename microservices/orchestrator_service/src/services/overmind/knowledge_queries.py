"""استعلامات قاعدة البيانات المستخدمة في معرفة Overmind."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.orchestrator_service.src.services.overmind.database_tools.validators import (
    quote_identifier,
    validate_identifier,
)


async def fetch_all_tables(session: AsyncSession) -> list[str]:
    """يسترجع قائمة الجداول في قاعدة البيانات الحالية."""
    query = text(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
    )

    result = await session.execute(query)
    return list(result.scalars().all())


async def fetch_table_count(session: AsyncSession, table_name: str) -> int:
    """يسترجع عدد السجلات داخل جدول محدد."""
    safe_table = quote_identifier(validate_identifier(table_name))
    query = text(f"SELECT COUNT(*) FROM {safe_table}")
    result = await session.execute(query)
    count = result.scalar()
    return count or 0


async def fetch_table_columns(
    session: AsyncSession,
    table_name: str,
) -> list[dict[str, object]]:
    """يسترجع معلومات الأعمدة لجدول محدد."""
    validate_identifier(table_name)
    columns_query = text(
        """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
        ORDER BY ordinal_position
        """
    )

    result = await session.execute(columns_query, {"table_name": table_name})

    columns: list[dict[str, object]] = []
    for row in result:
        columns.append(
            {
                "name": row.column_name,
                "type": row.data_type,
                "nullable": row.is_nullable == "YES",
                "default": row.column_default,
                "max_length": row.character_maximum_length,
            }
        )

    return columns


async def fetch_primary_keys(session: AsyncSession, table_name: str) -> list[str]:
    """يسترجع المفاتيح الأساسية لجدول محدد."""
    validate_identifier(table_name)
    pk_query = text(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid
                           AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = :table_name::regclass
          AND i.indisprimary
        """
    )

    pk_result = await session.execute(pk_query, {"table_name": table_name})
    return [row.attname for row in pk_result]


async def fetch_foreign_keys(
    session: AsyncSession,
    table_name: str,
) -> list[dict[str, str]]:
    """يسترجع المفاتيح الأجنبية لجدول محدد."""
    validate_identifier(table_name)
    fk_query = text(
        """
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name = :table_name
        """
    )

    fk_result = await session.execute(fk_query, {"table_name": table_name})

    foreign_keys: list[dict[str, str]] = []
    for row in fk_result:
        foreign_keys.append(
            {
                "column": row.column_name,
                "references_table": row.foreign_table_name,
                "references_column": row.foreign_column_name,
            }
        )

    return foreign_keys
