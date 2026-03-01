"""
إدارة حالة النواة (Kernel State Management).

يبني حالة التطبيق كبيانات واضحة ويطبقها على كائن FastAPI
وفق مبدأ: Functional Core, Imperative Shell.
"""

from dataclasses import dataclass

from fastapi import FastAPI

from app.core.event_bus_impl import get_event_bus
from app.core.protocols import EventBusProtocol
from app.services.overmind.langgraph.service import LangGraphAgentService, create_langgraph_service
from app.services.overmind.plan_registry import AgentPlanRegistry

__all__ = [
    "AppStateServices",
    "apply_app_state",
    "build_app_state",
]


@dataclass(frozen=True, slots=True)
class AppStateServices:
    """حاوية حالة التطبيق المنسقة كبيانات صريحة."""

    agent_plan_registry: AgentPlanRegistry

    langgraph_service: LangGraphAgentService
    event_bus: EventBusProtocol


def build_app_state() -> AppStateServices:
    """
    يبني حالة التطبيق كبيانات صريحة بدون تأثيرات جانبية.

    Returns:
        AppStateServices: الحاوية الكاملة لحالة النظام.
    """
    return AppStateServices(
        agent_plan_registry=AgentPlanRegistry(),
        langgraph_service=create_langgraph_service(),
        event_bus=get_event_bus(),
    )


def apply_app_state(app: FastAPI, state: AppStateServices) -> None:
    """
    يطبق حالة التطبيق على كائن FastAPI بشكل صريح.

    Args:
        app: كائن FastAPI الأساسي.
        state: حاوية حالة التطبيق.
    """
    app.state.agent_plan_registry = state.agent_plan_registry

    app.state.langgraph_service = state.langgraph_service
    app.state.event_bus = state.event_bus
