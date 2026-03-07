"""
Admin Agent (Simplified for Microservice).
"""

from collections.abc import AsyncGenerator

from microservices.orchestrator_service.src.core.logging import get_logger
from microservices.orchestrator_service.src.services.llm.client import AIClient
from microservices.orchestrator_service.src.services.overmind.agents.data_access import (
    DataAccessAgent,
)
from microservices.orchestrator_service.src.services.overmind.agents.refactor import (
    RefactorAgent,
)
from microservices.orchestrator_service.src.services.overmind.utils.tools import ToolRegistry

logger = get_logger("admin-agent")


class AdminAgent:
    """
    Admin Agent Proxy.
    """

    def __init__(
        self,
        tools: ToolRegistry,
        ai_client: AIClient | None = None,
    ) -> None:
        self.tools = tools
        self.ai_client = ai_client
        self.data_agent = DataAccessAgent()
        self.refactor_agent = RefactorAgent()

    async def run(
        self,
        question: str,
        context: dict[str, object] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Handle admin queries intelligently.
        Binds required tools and prevents hallucinated responses.
        """
        if not self.ai_client:
            yield "⚠️ AI client is not available."
            return

        system_prompt = (
            "You are a strict Admin Agent."
            "You MUST use the provided tools to answer the user's question, especially for counting databases or files."
            "Do NOT hallucinate or guess the answer. Use the available tools."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        # Define the tools we want to make available to the LLM
        # For example, counting users or checking tables
        agent_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_user_count",
                    "description": "Get the total number of users in the system.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_all_tables",
                    "description": "List all database tables.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_table_count",
                    "description": "Get the number of rows in a specific table.",
                    "parameters": {
                        "type": "object",
                        "properties": {"table_name": {"type": "string"}},
                        "required": ["table_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "count_python_files",
                    "description": "Get the total number of Python (.py) files in the project workspace.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "count_db_tables",
                    "description": "Get the exact count of all database tables.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_microservices",
                    "description": "List all running microservices.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_stats",
                    "description": "Calculate and get complete project statistics.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

        try:
            # Force tool execution
            response = await self.ai_client.generate(
                messages=messages, tools=agent_tools, tool_choice="required"
            )

            # Inspect the response
            message = response.choices[0].message
            if not hasattr(message, "tool_calls") or not message.tool_calls:
                response = await self.ai_client.generate(
                    messages=messages, tools=agent_tools, tool_choice="required"
                )
                message = response.choices[0].message

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        import json

                        tool_args = json.loads(tool_call.function.arguments)
                    except Exception:
                        tool_args = {}

                    logger.info(f"AdminAgent invoking tool: {tool_name} with {tool_args}")

                    # Instead of self.tools, use the registry or a facade if available,
                    # or handle directly if needed.
                    # If this service doesn't have these tools registered in its own ToolRegistry,
                    # we need to fallback or properly implement them in the microservice registry.
                    result = await self.tools.execute(tool_name, tool_args)

                    if result is not None:
                        yield f"✅ نتيجة أداة {tool_name}:\n{result}"
                    # Attempt direct execution if they are DB tools
                    elif tool_name == "get_user_count":
                        from microservices.orchestrator_service.src.infrastructure.clients.user_client import (
                            user_client,
                        )

                        try:
                            count = await user_client.get_user_count()
                            yield f"✅ عدد المستخدمين: {count}"
                        except Exception as e:
                            yield f"❌ فشل جلب عدد المستخدمين: {e}"
                    elif tool_name in ["list_all_tables", "get_table_count"]:
                        from microservices.orchestrator_service.src.services.overmind.database_tools.facade import (
                            SuperDatabaseTools,
                        )

                        try:
                            async with SuperDatabaseTools() as db_tools:
                                if tool_name == "list_all_tables":
                                    tables = await db_tools.list_all_tables()
                                    yield f"✅ الجداول المتاحة: {', '.join(tables)}"
                                elif tool_name == "get_table_count":
                                    # Not perfectly matching facade, maybe use knowledge
                                    from microservices.orchestrator_service.src.services.overmind.knowledge import (
                                        DatabaseKnowledge,
                                    )

                                    async with DatabaseKnowledge() as db_knowledge:
                                        count = await db_knowledge.get_table_count(
                                            tool_args.get("table_name", "")
                                        )
                                    yield f"✅ عدد الصفوف في {tool_args.get('table_name')}: {count}"
                        except Exception as e:
                            yield f"❌ فشل تنفيذ أداة قواعد البيانات: {e}"
                    elif tool_name == "count_python_files":
                        try:
                            import asyncio

                            proc = await asyncio.create_subprocess_shell(
                                "find . -name '*.py' | wc -l",
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                            )
                            stdout, _ = await proc.communicate()
                            count = stdout.decode().strip()
                            yield f"✅ عدد ملفات بايثون في المشروع: {count} ملف."
                        except Exception as e:
                            yield f"❌ فشل حساب ملفات بايثون: {e}"
                    elif tool_name == "count_db_tables":
                        from microservices.orchestrator_service.src.services.overmind.database_tools.facade import (
                            SuperDatabaseTools,
                        )

                        try:
                            async with SuperDatabaseTools() as db_tools:
                                tables = await db_tools.list_all_tables()
                                yield f"✅ عدد الجداول في قاعدة البيانات: {len(tables)}"
                        except Exception as e:
                            yield f"❌ فشل حساب عدد الجداول: {e}"
                    elif tool_name == "list_microservices":
                        try:
                            import asyncio

                            proc = await asyncio.create_subprocess_shell(
                                "docker ps --format '{{.Names}}' | grep service | wc -l",
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                            )
                            stdout, _ = await proc.communicate()
                            count = stdout.decode().strip()
                            yield f"✅ عدد الخدمات المصغرة الشغالة: {count}"
                        except Exception as e:
                            yield f"❌ فشل إحصاء الخدمات المصغرة: {e}"
                    elif tool_name == "calculate_stats":
                        from microservices.orchestrator_service.src.infrastructure.clients.user_client import (
                            user_client,
                        )
                        from microservices.orchestrator_service.src.services.overmind.database_tools.facade import (
                            SuperDatabaseTools,
                        )

                        try:
                            user_count = await user_client.get_user_count()

                            async with SuperDatabaseTools() as db_tools:
                                admin_convos = await db_tools.execute_sql(
                                    "SELECT count(*) as c FROM admin_conversations"
                                )
                                cust_convos = await db_tools.execute_sql(
                                    "SELECT count(*) as c FROM customer_conversations"
                                )

                                admin_c = (
                                    admin_convos.get("rows", [{"c": 0}])[0]["c"]
                                    if admin_convos.get("success")
                                    else 0
                                )
                                cust_c = (
                                    cust_convos.get("rows", [{"c": 0}])[0]["c"]
                                    if cust_convos.get("success")
                                    else 0
                                )

                                yield (
                                    "✅ إحصائيات النظام:\n"
                                    f"- المستخدمين النشطين: {user_count}\n"
                                    f"- محادثات العملاء: {cust_c}\n"
                                    f"- محادثات الأدمن: {admin_c}"
                                )
                        except Exception as e:
                            yield f"❌ خطأ في حساب الإحصائيات: {e}"
                    else:
                        yield f"⚠️ الأداة {tool_name} غير مدعومة حالياً في هذه النسخة المصغرة."

            else:
                yield "❌ خطأ: الوكيل الذكي لم يستخدم أي أداة لحساب النتيجة، وهذا غير مسموح."

        except Exception as e:
            logger.error(f"AdminAgent error: {e}")
            yield f"⚠️ حدث خطأ أثناء محاولة تنفيذ أمر الإدارة: {e}"
