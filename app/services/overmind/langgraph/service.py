from __future__ import annotations

from app.infrastructure.clients.orchestrator_client import orchestrator_client
from app.services.overmind.domain.api_schemas import (
    LangGraphRunData,
    LangGraphRunRequest,
)


class LangGraphAgentService:
    """
    خدمة تشغيل LangGraph للوكلاء المتعددين.
    Proxy implementation using Orchestrator Client.
    """

    def __init__(self, engine=None) -> None:
        """
        Engine arg kept for compatibility but ignored.
        """
        pass

    async def run(self, payload: LangGraphRunRequest) -> LangGraphRunData:
        """
        تشغيل LangGraph وإرجاع بيانات التشغيل.
        """
        # Delegate to Orchestrator Service
        # We assume Orchestrator Service has an endpoint for LangGraph runs
        # create_mission in Orchestrator Client uses POST /missions
        # We might need to map LangGraphRunRequest to MissionCreate or use a specific endpoint.

        # For now, map to create_mission
        context = payload.context or {}
        # Pass graph_mode if supported by orchestrator
        context["graph_mode"] = "langgraph"
        context["constraints"] = payload.constraints
        context["priority"] = payload.priority

        mission_response = await orchestrator_client.create_mission(
            objective=payload.objective,
            context=context,
            priority=1,  # mapping logic needed
        )

        # Convert MissionResponse to LangGraphRunData
        # This is lossy because MissionResponse is generic
        return LangGraphRunData(
            run_id=str(mission_response.id),
            objective=mission_response.objective,
            plan=None,
            design=None,
            execution=None,
            audit=None,
            timeline=[],
        )


def create_langgraph_service(db=None) -> LangGraphAgentService:
    """
    Factory function for LangGraphAgentService.
    Now returns a proxy service.
    """
    return LangGraphAgentService()
