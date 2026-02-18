"""
Tool Registry.
"""

from collections.abc import Callable

from microservices.orchestrator_service.src.core.logging import get_logger

logger = get_logger("tool-registry")

# Global registry of tool functions
_TOOL_REGISTRY: dict[str, Callable] = {}


def get_registry() -> dict[str, Callable]:
    """Returns the tool registry."""
    return _TOOL_REGISTRY


def register_tool(name: str, func: Callable) -> None:
    """Registers a tool."""
    _TOOL_REGISTRY[name] = func
    logger.info(f"Registered tool: {name}")
