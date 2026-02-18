"""
مدير البيانات (Data Manager).

مسؤول عن إدارة البيانات: إدخال، استعلام، تعديل، حذف.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.database_tools.operations_logger import (
    OperationsLogger,
)
from microservices.orchestrator_service.src.services.overmind.database_tools.validators import (
    ensure_columns_exist,
    ensure_table_exists,
    quote_identifier,
    validate_identifier,
)

logger = get_logger(__name__)


class DataManager:
    """مدير البيانات في قاعدة البيانات."""

    def __init__(
        self,
        session: AsyncSession,
        operations_logger: OperationsLogger,
    ) -> None:
        """
        تهيئة مدير البيانات.

        Args:
            session: جلسة قاعدة البيانات
            operations_logger: مسجل العمليات
        """
        self._session = session
        self._logger = operations_logger

    async def insert_data(
        self,
        table_name: str,
        data: dict[str, object],
    ) -> dict[str, object]:
        """
        إدخال بيانات جديدة في جدول.

        Args:
            table_name: اسم الجدول
            data: البيانات المراد إدخالها {عمود: قيمة}

        Returns:
            dict: نتيجة الإدخال
        """
        try:
            validate_identifier(table_name)
            if not data:
                raise ValueError("لا يمكن إدخال سجل فارغ.")
            await ensure_columns_exist(self._session, table_name, set(data.keys()))
            columns = ", ".join([quote_identifier(col) for col in data])
            placeholders = ", ".join([f":{col}" for col in data])

            insert_sql = (
                f"INSERT INTO {quote_identifier(table_name)} ({columns}) VALUES ({placeholders})"
            )

            await self._session.execute(text(insert_sql), data)
            await self._session.commit()

            result = {
                "success": True,
                "table_name": table_name,
                "data": data,
            }

            self._logger.log_operation("insert_data", result)
            return result

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Error inserting data: {e}")

            result = {
                "success": False,
                "table_name": table_name,
                "error": str(e),
            }
            self._logger.log_operation("insert_data", result, success=False)
            return result

    async def query_table(
        self,
        table_name: str,
        where: dict[str, object] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        """
        استعلام بيانات من جدول.

        Args:
            table_name: اسم الجدول
            where: شروط الاستعلام (اختياري)
            limit: حد أقصى للنتائج
            offset: البداية

        Returns:
            dict: نتيجة الاستعلام
        """
        try:
            validate_identifier(table_name)
            await ensure_table_exists(self._session, table_name)
            query = f"SELECT * FROM {quote_identifier(table_name)}"
            params: dict[str, object] = {}

            if where:
                await ensure_columns_exist(self._session, table_name, set(where.keys()))
                where_clauses = [f"{quote_identifier(col)} = :{col}" for col in where]
                query += " WHERE " + " AND ".join(where_clauses)
                params.update(where)

            if limit is not None:
                if limit < 0:
                    raise ValueError("limit يجب أن يكون صفراً أو قيمة موجبة.")
                query += " LIMIT :limit"
                params["limit"] = limit

            if offset is not None:
                if offset < 0:
                    raise ValueError("offset يجب أن يكون صفراً أو قيمة موجبة.")
                query += " OFFSET :offset"
                params["offset"] = offset

            result = await self._session.execute(text(query), params)
            rows = []
            for row in result:
                rows.append(dict(row._mapping))

            result_data = {
                "success": True,
                "table_name": table_name,
                "rows": rows,
                "count": len(rows),
            }

            self._logger.log_operation("query_table", {"table": table_name, "count": len(rows)})
            return result_data

        except Exception as e:
            logger.error(f"Error querying table: {e}")

            result_data = {
                "success": False,
                "table_name": table_name,
                "error": str(e),
            }
            self._logger.log_operation("query_table", result_data, success=False)
            return result_data

    async def update_data(
        self,
        table_name: str,
        data: dict[str, object],
        where: dict[str, object],
    ) -> dict[str, object]:
        """
        تعديل بيانات في جدول.

        Args:
            table_name: اسم الجدول
            data: البيانات الجديدة {عمود: قيمة}
            where: شروط التعديل {عمود: قيمة}

        Returns:
            dict: نتيجة التعديل
        """
        try:
            validate_identifier(table_name)
            if not data:
                raise ValueError("لا يمكن تحديث جدول بدون بيانات.")
            if not where:
                raise ValueError("شروط التعديل مطلوبة لمنع التحديث الشامل.")
            await ensure_columns_exist(
                self._session, table_name, set(data.keys()).union(where.keys())
            )
            set_clauses = [f"{quote_identifier(col)} = :set_{col}" for col in data]
            where_clauses = [f"{quote_identifier(col)} = :where_{col}" for col in where]

            update_sql = (
                f"UPDATE {quote_identifier(table_name)} "
                f"SET {', '.join(set_clauses)} "
                f"WHERE {' AND '.join(where_clauses)}"
            )

            params = {f"set_{k}": v for k, v in data.items()}
            params.update({f"where_{k}": v for k, v in where.items()})

            result = await self._session.execute(text(update_sql), params)
            await self._session.commit()

            result_data = {
                "success": True,
                "table_name": table_name,
                "affected_rows": result.rowcount,
            }

            self._logger.log_operation("update_data", result_data)
            return result_data

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Error updating data: {e}")

            result_data = {
                "success": False,
                "table_name": table_name,
                "error": str(e),
            }
            self._logger.log_operation("update_data", result_data, success=False)
            return result_data

    async def delete_data(
        self,
        table_name: str,
        where: dict[str, object],
    ) -> dict[str, object]:
        """
        حذف بيانات من جدول.

        Args:
            table_name: اسم الجدول
            where: شروط الحذف {عمود: قيمة}

        Returns:
            dict: نتيجة الحذف

        تحذير:
            ⚠️ البيانات ستُحذف نهائياً - احذر!
        """
        try:
            validate_identifier(table_name)
            if not where:
                raise ValueError("شروط الحذف مطلوبة لمنع الحذف الشامل.")
            await ensure_columns_exist(self._session, table_name, set(where.keys()))
            where_clauses = [f"{quote_identifier(col)} = :{col}" for col in where]

            delete_sql = (
                f"DELETE FROM {quote_identifier(table_name)} WHERE {' AND '.join(where_clauses)}"
            )

            result = await self._session.execute(text(delete_sql), where)
            await self._session.commit()

            result_data = {
                "success": True,
                "table_name": table_name,
                "affected_rows": result.rowcount,
            }

            self._logger.log_operation("delete_data", result_data)
            return result_data

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Error deleting data: {e}")

            result_data = {
                "success": False,
                "table_name": table_name,
                "error": str(e),
            }
            self._logger.log_operation("delete_data", result_data, success=False)
            return result_data
