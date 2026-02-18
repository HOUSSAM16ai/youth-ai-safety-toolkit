"""
مدير الجداول (Table Manager).

مسؤول عن إدارة الجداول: إنشاء، حذف، قائمة، تفاصيل.
"""

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.database_tools.operations_logger import (
    OperationsLogger,
)
from microservices.orchestrator_service.src.services.overmind.database_tools.validators import (
    ensure_table_exists,
    quote_identifier,
    validate_column_type,
    validate_identifier,
)

logger = get_logger(__name__)


class TableManager:
    """مدير الجداول في قاعدة البيانات."""

    def __init__(
        self,
        session: AsyncSession,
        metadata: MetaData,
        operations_logger: OperationsLogger,
    ) -> None:
        """
        تهيئة مدير الجداول.

        Args:
            session: جلسة قاعدة البيانات
            metadata: معلومات البيانات الوصفية
            operations_logger: مسجل العمليات
        """
        self._session = session
        self.metadata = metadata
        self._logger = operations_logger

    async def list_all_tables(self) -> list[str]:
        """
        عرض جميع الجداول في قاعدة البيانات.

        Returns:
            list[str]: أسماء جميع الجداول
        """
        try:
            query = text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            result = await self._session.execute(query)
            tables = [row[0] for row in result]

            self._logger.log_operation("list_tables", {"count": len(tables)})
            return tables

        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            self._logger.log_operation("list_tables", {"error": str(e)}, success=False)
            return []

    async def get_table_details(self, table_name: str) -> dict[str, object]:
        """
        الحصول على تفاصيل كاملة عن جدول.

        Args:
            table_name: اسم الجدول

        Returns:
            dict: تفاصيل شاملة تشمل:
                - columns: الأعمدة مع أنواعها
                - primary_keys: المفاتيح الأساسية
                - foreign_keys: المفاتيح الأجنبية
                - indexes: الفهارس
                - constraints: القيود
                - row_count: عدد الصفوف
        """
        try:
            await ensure_table_exists(self._session, table_name)
            # جمع جميع التفاصيل
            columns = await self._get_columns(table_name)
            primary_keys = await self._get_primary_keys(table_name)
            foreign_keys = await self._get_foreign_keys(table_name)
            indexes = await self._get_indexes(table_name)
            row_count = await self._get_row_count(table_name)

            details = self._build_table_details(
                table_name, columns, primary_keys, foreign_keys, indexes, row_count
            )

            self._logger.log_operation("get_table_details", {"table": table_name})
            return details

        except Exception as e:
            logger.error(f"Error getting table details: {e}")
            self._logger.log_operation(
                "get_table_details",
                {"table": table_name, "error": str(e)},
                success=False,
            )
            return {}

    async def _get_columns(self, table_name: str) -> list[dict[str, object]]:
        """
        استعلام معلومات الأعمدة.

        Query column information.

        Args:
            table_name: اسم الجدول

        Returns:
            قائمة بمعلومات الأعمدة
        """
        columns_query = text("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """)

        result = await self._session.execute(columns_query, {"table_name": table_name})

        columns = []
        for row in result:
            columns.append(
                {
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "default": row[3],
                }
            )

        return columns

    async def _get_primary_keys(self, table_name: str) -> list[str]:
        """
        استعلام المفاتيح الأساسية.

        Query primary keys.

        Args:
            table_name: اسم الجدول

        Returns:
            قائمة بأسماء أعمدة المفاتيح الأساسية
        """
        pk_query = text("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = :table_name
                AND tc.constraint_type = 'PRIMARY KEY'
        """)

        result = await self._session.execute(pk_query, {"table_name": table_name})
        return [row[0] for row in result]

    async def _get_foreign_keys(self, table_name: str) -> list[dict[str, str]]:
        """
        استعلام المفاتيح الأجنبية.

        Query foreign keys.

        Args:
            table_name: اسم الجدول

        Returns:
            قائمة بمعلومات المفاتيح الأجنبية
        """
        fk_query = text("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = :table_name
                AND tc.constraint_type = 'FOREIGN KEY'
        """)

        result = await self._session.execute(fk_query, {"table_name": table_name})

        foreign_keys = []
        for row in result:
            foreign_keys.append(
                {
                    "column": row[0],
                    "references_table": row[1],
                    "references_column": row[2],
                }
            )

        return foreign_keys

    async def _get_indexes(self, table_name: str) -> list[dict[str, str]]:
        """
        استعلام الفهارس.

        Query indexes.

        Args:
            table_name: اسم الجدول

        Returns:
            قائمة بمعلومات الفهارس
        """
        idx_query = text("""
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = :table_name
        """)

        result = await self._session.execute(idx_query, {"table_name": table_name})

        indexes = []
        for row in result:
            indexes.append(
                {
                    "name": row[0],
                    "definition": row[1],
                }
            )

        return indexes

    async def _get_row_count(self, table_name: str) -> int:
        """
        حساب عدد الصفوف في الجدول.

        Count table rows.

        Args:
            table_name: اسم الجدول

        Returns:
            عدد الصفوف
        """
        await ensure_table_exists(self._session, table_name)
        count_query = text(f"SELECT COUNT(*) FROM {quote_identifier(table_name)}")
        result = await self._session.execute(count_query)
        return result.scalar() or 0

    def _build_table_details(
        self,
        table_name: str,
        columns: list[dict[str, object]],
        primary_keys: list[str],
        foreign_keys: list[dict[str, str]],
        indexes: list[dict[str, str]],
        row_count: int,
    ) -> dict[str, object]:
        """
        بناء كائن التفاصيل من المكونات المجمعة.

        Build details object from collected components.

        Args:
            table_name: اسم الجدول
            columns: قائمة الأعمدة
            primary_keys: قائمة المفاتيح الأساسية
            foreign_keys: قائمة المفاتيح الأجنبية
            indexes: قائمة الفهارس
            row_count: عدد الصفوف

        Returns:
            كائن التفاصيل الكامل
        """
        return {
            "table_name": table_name,
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "constraints": [],  # Reserved for future use
            "row_count": row_count,
        }

    async def create_table(
        self,
        table_name: str,
        columns: dict[str, str],
    ) -> dict[str, object]:
        """
        إنشاء جدول جديد.

        Args:
            table_name: اسم الجدول
            columns: قاموس الأعمدة {اسم: نوع}
                مثال: {"id": "INTEGER PRIMARY KEY", "name": "VARCHAR(255)"}

        Returns:
            dict: نتيجة الإنشاء
        """
        try:
            # بناء استعلام CREATE TABLE
            validate_identifier(table_name)
            columns_sql = ", ".join(
                [
                    f"{quote_identifier(col_name)} {validate_column_type(col_type)}"
                    for col_name, col_type in columns.items()
                ]
            )

            create_sql = f"CREATE TABLE {quote_identifier(table_name)} ({columns_sql})"

            await self._session.execute(text(create_sql))
            await self._session.commit()

            result = {
                "success": True,
                "table_name": table_name,
                "columns": columns,
            }

            self._logger.log_operation("create_table", result)
            return result

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Error creating table: {e}")

            result = {
                "success": False,
                "table_name": table_name,
                "error": str(e),
            }
            self._logger.log_operation("create_table", result, success=False)
            return result

    async def drop_table(
        self,
        table_name: str,
        cascade: bool = False,
    ) -> dict[str, object]:
        """
        حذف جدول.

        Args:
            table_name: اسم الجدول
            cascade: حذف التبعيات أيضاً

        Returns:
            dict: نتيجة الحذف

        تحذير:
            ⚠️ هذه عملية خطيرة - البيانات ستُحذف نهائياً!
        """
        try:
            validate_identifier(table_name)
            cascade_sql = " CASCADE" if cascade else ""
            drop_sql = f"DROP TABLE IF EXISTS {quote_identifier(table_name)}{cascade_sql}"

            await self._session.execute(text(drop_sql))
            await self._session.commit()

            result = {
                "success": True,
                "table_name": table_name,
                "cascade": cascade,
            }

            self._logger.log_operation("drop_table", result)
            return result

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Error dropping table: {e}")

            result = {
                "success": False,
                "table_name": table_name,
                "error": str(e),
            }
            self._logger.log_operation("drop_table", result, success=False)
            return result
