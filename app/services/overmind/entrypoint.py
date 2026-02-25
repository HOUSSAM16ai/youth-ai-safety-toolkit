"""
Unified Entrypoint for Overmind Missions.
Implements the Command Pattern to standardize mission execution.
Ensures Single Control Plane and Source of Truth via Orchestrator Service.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.mission import Mission, MissionStatus
from app.infrastructure.clients.orchestrator_client import orchestrator_client
from app.services.overmind.domain.types import MissionContext

logger = logging.getLogger(__name__)


async def start_mission(
    session: AsyncSession | None,  # Kept for compatibility, but unused for local DB creation
    objective: str,
    initiator_id: int,
    context: MissionContext | None = None,
    force_research: bool = False,
    idempotency_key: str | None = None,
) -> Mission:
    """
    Unified Entrypoint to Start a Mission via Orchestrator Service.

    ARCHITECTURAL NOTE:
    -------------------
    This function is a STRICT PROXY to the Orchestrator Service.
    Local execution of missions within the Monolith (Core Kernel) is FORBIDDEN.
    The Single Source of Truth for Mission Command and State is the Orchestrator Service.

    Any attempt to bypass this delegation violates the 'Split-Brain' prevention policy.

    Args:
        session: The active database session (unused in decoupled mode).
        objective: The mission objective.
        initiator_id: The ID of the user initiating the mission.
        context: Optional context dictionary.
        force_research: Flag to force research mode.
        idempotency_key: Optional key to ensure idempotency.

    Returns:
        The created Mission object (Transient/Proxy).
    """
    logger.info(f"Delegating Mission Execution to Orchestrator Service: {objective[:50]}...")

    try:
        # Delegate to Orchestrator Service
        # We wrap the context to match API expected schema
        api_context = {}
        if context:
            # Flatten context if needed or pass as dict
            if hasattr(context, "dict"):
                api_context = context.dict()
            elif isinstance(context, dict):
                api_context = context

        if force_research:
            api_context["force_research"] = True

        response = await orchestrator_client.create_mission(
            objective=objective,
            context=api_context,
            priority=1,
            idempotency_key=idempotency_key,
        )

        # Convert Response to Domain Model (Transient)
        # This allows existing handlers to work with the Mission object structure
        return Mission(
            id=response.id,
            objective=response.objective,
            status=MissionStatus(response.status) if response.status else MissionStatus.PENDING,
            result_summary=response.result.get("summary") if response.result else None,
            created_at=response.created_at,
            updated_at=response.updated_at,
        )

    except Exception as e:
        logger.error(f"Failed to dispatch mission via Orchestrator Client: {e}")
        raise e
