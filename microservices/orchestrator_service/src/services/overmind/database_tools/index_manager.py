"""
مدير الفهارس (Index Manager).

مسؤول عن إدارة الفهارس: إنشاء، حذف.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.database_tools.operations_logger import (
    OperationsLogger,
)
from microservices.orchestrator_service.src.services.overmind.database_tools.validators import (
    ensure_columns_exist,
    quote_identifier,
    validate_identifier,
)

logger = get_logger(__name__)


class IndexManager:
    """مدير الفهارس في قاعدة البيانات."""

    def __init__(
        self,
        session: AsyncSession,
        operations_logger: OperationsLogger,
    ) -> None:
        """
        تهيئة مدير الفهارس.

        Args:
            session: جلسة قاعدة البيانات
            operations_logger: مسجل العمليات
        """
        self._session = session
        self._logger = operations_logger

    async def create_index(
        self,
        index_name: str,
        table_name: str,
        columns: list[str],
        unique: bool = False,
    ) -> dict[str, object]:
        """
        إنشاء فهرس على جدول.

        Args:
            index_name: اسم الفهرس
            table_name: اسم الجدول
            columns: قائمة الأعمدة
            unique: هل الفهرس فريد (UNIQUE INDEX)

        Returns:
            dict: نتيجة الإنشاء
        """
        try:
            validate_identifier(index_name)
            validate_identifier(table_name)
            if not columns:
                raise ValueError("قائمة الأعمدة مطلوبة لإنشاء الفهرس.")
            await ensure_columns_exist(self._session, table_name, set(columns))
            unique_sql = "UNIQUE " if unique else ""
            columns_sql = ", ".join([quote_identifier(col) for col in columns])

            create_sql = (
                f"CREATE {unique_sql}INDEX {quote_identifier(index_name)} "
                f"ON {quote_identifier(table_name)} ({columns_sql})"
            )

            await self._session.execute(text(create_sql))
            await self._session.commit()

            result = {
                "success": True,
                "index_name": index_name,
                "table_name": table_name,
                "columns": columns,
                "unique": unique,
            }

            self._logger.log_operation("create_index", result)
            return result

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Error creating index: {e}")

            result = {
                "success": False,
                "index_name": index_name,
                "error": str(e),
            }
            self._logger.log_operation("create_index", result, success=False)
            return result

    async def drop_index(self, index_name: str) -> dict[str, object]:
        """
        حذف فهرس.

        Args:
            index_name: اسم الفهرس

        Returns:
            dict: نتيجة الحذف
        """
        try:
            validate_identifier(index_name)
            drop_sql = f"DROP INDEX IF EXISTS {quote_identifier(index_name)}"

            await self._session.execute(text(drop_sql))
            await self._session.commit()

            result = {
                "success": True,
                "index_name": index_name,
            }

            self._logger.log_operation("drop_index", result)
            return result

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Error dropping index: {e}")

            result = {
                "success": False,
                "index_name": index_name,
                "error": str(e),
            }
            self._logger.log_operation("drop_index", result, success=False)
            return result
