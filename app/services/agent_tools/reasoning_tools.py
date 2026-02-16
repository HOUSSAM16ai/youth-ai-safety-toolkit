"""
Reasoning Tools
=====================
Bridge to the Reasoning Agent Microservice.
"""

import logging

from app.infrastructure.clients.reasoning_client import reasoning_client

from .core import tool
from .definitions import ToolResult

logger = logging.getLogger("agent_tools")


@tool(
    name="reason_deeply",
    description="Perform deep, multi-step reasoning using Tree of Thought strategy. Use for complex problems.",
    category="cognitive",
    capabilities=["reasoning"],
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The complex problem or question to analyze.",
            },
        },
        "required": ["query"],
    },
)
async def reason_deeply(query: str) -> ToolResult:
    """
    Executes a deep reasoning workflow via the Reasoning Agent Microservice.
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return ToolResult(ok=False, error="EMPTY_QUERY")

    try:
        result = await reasoning_client.reason_deeply(clean_query)

        if "error" in result:
            return ToolResult(ok=False, error=result["error"])

        return ToolResult(
            ok=True,
            data={
                "answer": result.get("answer", "Analysis completed."),
                "logic_trace": result.get("logic_trace", []),
            },
        )

    except Exception as e:
        logger.error(f"reason_deeply tool failed: {e}")
        return ToolResult(ok=False, error=str(e))
