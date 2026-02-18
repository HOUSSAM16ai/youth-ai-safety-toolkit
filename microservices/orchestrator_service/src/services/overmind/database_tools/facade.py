"""
واجهة الأدوات الخارقة لقواعد البيانات (Super Database Tools Facade).

هذه الواجهة توحد جميع مديري قاعدة البيانات في واجهة بسيطة واحدة،
مع الحفاظ على التوافق الكامل مع الواجهة القديمة.

المبدأ: Facade Pattern
يوفر واجهة بسيطة لنظام معقد من المكونات المتخصصة.
"""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_logger
from microservices.orchestrator_service.src.core.config import get_settings
from microservices.orchestrator_service.src.core.database import get_db
from microservices.orchestrator_service.src.services.overmind.database_tools.column_manager import (
    ColumnManager,
)
from microservices.orchestrator_service.src.services.overmind.database_tools.data_manager import (
    DataManager,
)
from microservices.orchestrator_service.src.services.overmind.database_tools.index_manager import (
    IndexManager,
)
from microservices.orchestrator_service.src.services.overmind.database_tools.operations_logger import (
    OperationsLogger,
)
from microservices.orchestrator_service.src.services.overmind.database_tools.query_executor import (
    QueryExecutor,
)
from microservices.orchestrator_service.src.services.overmind.database_tools.table_manager import (
    TableManager,
)

logger = get_logger(__name__)


class SuperDatabaseTools:
    """
    الأدوات الخارقة لقواعد البيانات (Super Database Tools).

    توفر تحكماً كاملاً 100% في كل تفصيلة من تفاصيل قاعدة البيانات:
    - الجداول: إنشاء، تعديل، حذف، قائمة
    - الأعمدة: إضافة، تعديل، حذف
    - البيانات: إدخال، تعديل، حذف، استعلام
    - الفهارس: إنشاء، حذف، تحليل
    - العلاقات: إنشاء FK، حذف
    - التحليل: إحصائيات، أداء، صحة
    - النسخ الاحتياطي: حفظ، استعادة

    التصميم الجديد:
        تم تقسيم الوظائف إلى مديرين متخصصين:
        - TableManager: إدارة الجداول
        - ColumnManager: إدارة الأعمدة
        - DataManager: إدارة البيانات
        - IndexManager: إدارة الفهارس
        - QueryExecutor: تنفيذ استعلامات SQL
        - OperationsLogger: تسجيل العمليات

    الاستخدام:
        >>> async with SuperDatabaseTools() as db_tools:
        >>>     # إنشاء جدول جديد
        >>>     await db_tools.create_table("products", {
        >>>         "id": "INTEGER PRIMARY KEY",
        >>>         "name": "VARCHAR(255) NOT NULL",
        >>>         "price": "DECIMAL(10,2)"
        >>>     })
        >>>
        >>>     # إضافة بيانات
        >>>     await db_tools.insert_data("products", {
        >>>         "name": "Product 1",
        >>>         "price": 99.99
        >>>     })
        >>>
        >>>     # استعلام
        >>>     results = await db_tools.query_table("products")
    """

    def __init__(self) -> None:
        """تهيئة أدوات قاعدة البيانات."""
        self.settings = get_settings()
        self._session: AsyncSession | None = None
        self.metadata = MetaData()

        # تهيئة المديرين (سيتم بعد فتح الجلسة)
        self._operations_logger: OperationsLogger | None = None
        self._table_manager: TableManager | None = None
        self._column_manager: ColumnManager | None = None
        self._data_manager: DataManager | None = None
        self._index_manager: IndexManager | None = None
        self._query_executor: QueryExecutor | None = None

        logger.info("SuperDatabaseTools initialized")

    async def __aenter__(self):
        """فتح الجلسة (Context Manager)."""
        async for session in get_db():
            self._session = session
            break

        # تهيئة المديرين بعد فتح الجلسة
        self._operations_logger = OperationsLogger()
        self._table_manager = TableManager(self._session, self.metadata, self._operations_logger)
        self._column_manager = ColumnManager(self._session, self._operations_logger)
        self._data_manager = DataManager(self._session, self._operations_logger)
        self._index_manager = IndexManager(self._session, self._operations_logger)
        self._query_executor = QueryExecutor(self._session, self._operations_logger)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """إغلاق الجلسة."""
        if self._session:
            await self._session.close()

    # =========================================================================
    # الجداول: الإنشاء، القائمة، التفاصيل، الحذف
    # =========================================================================

    async def list_all_tables(self) -> list[str]:
        """
        عرض جميع الجداول في قاعدة البيانات.

        Returns:
            list[str]: أسماء جميع الجداول
        """
        if not self._table_manager:
            return []
        return await self._table_manager.list_all_tables()

    async def get_table_details(self, table_name: str) -> dict[str, object]:
        """
        الحصول على تفاصيل كاملة عن جدول.

        Args:
            table_name: اسم الجدول

        Returns:
            dict: تفاصيل شاملة
        """
        if not self._table_manager:
            return {}
        return await self._table_manager.get_table_details(table_name)

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

        Returns:
            dict: نتيجة الإنشاء
        """
        if not self._table_manager:
            return {"success": False, "error": "No session"}
        return await self._table_manager.create_table(table_name, columns)

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
        """
        if not self._table_manager:
            return {"success": False, "error": "No session"}
        return await self._table_manager.drop_table(table_name, cascade)

    # =========================================================================
    # الأعمدة: الإضافة، الحذف
    # =========================================================================

    async def add_column(
        self,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> dict[str, object]:
        """
        إضافة عمود جديد إلى جدول موجود.

        Args:
            table_name: اسم الجدول
            column_name: اسم العمود الجديد
            column_type: نوع العمود

        Returns:
            dict: نتيجة الإضافة
        """
        if not self._column_manager:
            return {"success": False, "error": "No session"}
        return await self._column_manager.add_column(table_name, column_name, column_type)

    async def drop_column(
        self,
        table_name: str,
        column_name: str,
    ) -> dict[str, object]:
        """
        حذف عمود من جدول.

        Args:
            table_name: اسم الجدول
            column_name: اسم العمود

        Returns:
            dict: نتيجة الحذف
        """
        if not self._column_manager:
            return {"success": False, "error": "No session"}
        return await self._column_manager.drop_column(table_name, column_name)

    # =========================================================================
    # البيانات: الإدخال، الاستعلام، التعديل، الحذف
    # =========================================================================

    async def insert_data(
        self,
        table_name: str,
        data: dict[str, object],
    ) -> dict[str, object]:
        """
        إدخال بيانات جديدة في جدول.

        Args:
            table_name: اسم الجدول
            data: البيانات المراد إدخالها

        Returns:
            dict: نتيجة الإدخال
        """
        if not self._data_manager:
            return {"success": False, "error": "No session"}
        return await self._data_manager.insert_data(table_name, data)

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
            where: شروط الاستعلام
            limit: حد أقصى للنتائج
            offset: البداية

        Returns:
            dict: نتيجة الاستعلام
        """
        if not self._data_manager:
            return {"success": False, "error": "No session"}
        return await self._data_manager.query_table(table_name, where, limit, offset)

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
            data: البيانات الجديدة
            where: شروط التعديل

        Returns:
            dict: نتيجة التعديل
        """
        if not self._data_manager:
            return {"success": False, "error": "No session"}
        return await self._data_manager.update_data(table_name, data, where)

    async def delete_data(
        self,
        table_name: str,
        where: dict[str, object],
    ) -> dict[str, object]:
        """
        حذف بيانات من جدول.

        Args:
            table_name: اسم الجدول
            where: شروط الحذف

        Returns:
            dict: نتيجة الحذف
        """
        if not self._data_manager:
            return {"success": False, "error": "No session"}
        return await self._data_manager.delete_data(table_name, where)

    # =========================================================================
    # الفهارس: الإنشاء، الحذف
    # =========================================================================

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
            unique: هل الفهرس فريد

        Returns:
            dict: نتيجة الإنشاء
        """
        if not self._index_manager:
            return {"success": False, "error": "No session"}
        return await self._index_manager.create_index(index_name, table_name, columns, unique)

    async def drop_index(self, index_name: str) -> dict[str, object]:
        """
        حذف فهرس.

        Args:
            index_name: اسم الفهرس

        Returns:
            dict: نتيجة الحذف
        """
        if not self._index_manager:
            return {"success": False, "error": "No session"}
        return await self._index_manager.drop_index(index_name)

    # =========================================================================
    # تنفيذ SQL مخصص
    # =========================================================================

    async def execute_sql(
        self,
        sql: str,
        params: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """
        تنفيذ استعلام SQL مخصص.

        Args:
            sql: استعلام SQL
            params: المعاملات

        Returns:
            dict: نتيجة التنفيذ
        """
        if not self._query_executor:
            return {"success": False, "error": "No session"}
        return await self._query_executor.execute_sql(sql, params)

    # =========================================================================
    # سجل العمليات
    # =========================================================================

    def get_operations_log(self) -> list[dict[str, object]]:
        """
        الحصول على سجل العمليات.

        Returns:
            list[dict]: جميع العمليات المُنفذة
        """
        if not self._operations_logger:
            return []
        return self._operations_logger.get_operations_log()

    def clear_operations_log(self) -> None:
        """مسح سجل العمليات."""
        if self._operations_logger:
            self._operations_logger.clear_operations_log()
