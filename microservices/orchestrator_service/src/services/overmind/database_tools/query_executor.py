"""
منفذ الاستعلامات (Query Executor).

مسؤول عن تنفيذ استعلامات SQL مخصصة.
"""

import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.database_tools.operations_logger import (
    OperationsLogger,
)

logger = get_logger(__name__)

_READ_ONLY_PREFIXES = ("SELECT", "WITH")
_WRITE_PREFIXES = ("UPDATE", "INSERT", "DELETE")
_FORBIDDEN_SQL = re.compile(r";")


class QueryExecutor:
    """منفذ استعلامات SQL مخصصة."""

    def __init__(
        self,
        session: AsyncSession,
        operations_logger: OperationsLogger,
    ) -> None:
        """
        تهيئة منفذ الاستعلامات.

        Args:
            session: جلسة قاعدة البيانات
            operations_logger: مسجل العمليات
        """
        self._session = session
        self._logger = operations_logger

    async def execute_sql(
        self,
        sql: str,
        params: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """
        تنفيذ استعلام SQL مخصص.

        Args:
            sql: استعلام SQL
            params: المعاملات (اختياري)

        Returns:
            dict: نتيجة التنفيذ

        تحذير:
            ⚠️ هذه دالة قوية جداً - استخدمها بحذر!
            ⚠️ تأكد من صحة الاستعلام قبل التنفيذ!
        """
        try:
            normalized = " ".join(sql.strip().split())
            upper_sql = normalized.upper()
            if _FORBIDDEN_SQL.search(upper_sql):
                raise ValueError("يمنع تنفيذ أكثر من عبارة في طلب واحد.")
            if not upper_sql.startswith(_READ_ONLY_PREFIXES + _WRITE_PREFIXES):
                raise ValueError("نوع الاستعلام غير مدعوم ضمن المنفذ الحالي.")

            result = await self._session.execute(text(sql), params or {})

            # إذا كان استعلام تحديد (SELECT/CTE)، أرجع النتائج
            if upper_sql.startswith(_READ_ONLY_PREFIXES):
                rows = []
                for row in result:
                    rows.append(dict(row._mapping))

                return {
                    "success": True,
                    "rows": rows,
                    "row_count": len(rows),
                }
            await self._session.commit()
            return {
                "success": True,
                "affected_rows": result.rowcount,
            }

        except Exception as e:
            await self._session.rollback()
            logger.error(f"Error executing SQL: {e}")

            return {
                "success": False,
                "error": str(e),
            }
