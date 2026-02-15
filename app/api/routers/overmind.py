# app/api/routers/overmind.py
"""
Overmind Router (Gateway / BFF).
Delegates all logic to the Unified Control Plane (Internal Overmind Service).
Refactored to remove Split-Brain Orchestration.
"""

import logging
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.ws_auth import extract_websocket_auth
from app.core.config import get_settings
from app.core.database import get_db
from app.core.domain.mission import Mission
from app.core.event_bus import get_event_bus
from app.services.auth.token_decoder import decode_user_id
from app.services.overmind.domain.api_schemas import (
    MissionCreate,
    MissionResponse,
)
from app.services.overmind.entrypoint import start_mission
from app.services.overmind.state import MissionStateManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/overmind",
    tags=["Overmind (Super Agent)"],
)


def _get_mission_status_payload(status: str) -> dict[str, str | None]:
    """
    Helper to map internal domain status to API status/outcome.
    Handles 'partial_success' by returning success status with partial_success outcome.
    """
    if status == "partial_success":
        return {"status": "success", "outcome": "partial_success"}
    return {"status": status, "outcome": None}


def _serialize_mission(mission: Mission) -> MissionResponse:
    """
    Helper to serialize Mission domain model to MissionResponse API schema.
    Applies the status mapping logic.
    """
    status_payload = _get_mission_status_payload(mission.status.value)

    # Safely get result summary or json result if available
    # Assuming result_summary is the main result field for now

    return MissionResponse(
        id=mission.id,
        objective=mission.objective,
        status=status_payload["status"],
        outcome=status_payload["outcome"],
        created_at=mission.created_at,
        updated_at=mission.updated_at,
        result={"summary": mission.result_summary} if mission.result_summary else None,
        steps=[],  # Assuming tasks are mapped separately or not needed for basic response
    )


@router.post("/missions", response_model=MissionResponse, summary="Launch Mission")
async def create_mission_endpoint(
    request: MissionCreate,
    background_tasks: BackgroundTasks,
    req: Request,
    db: AsyncSession = Depends(get_db),
) -> MissionResponse:
    """
    Launch a mission using the Unified Control Plane.
    """
    correlation_id = req.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    logger.info(f"Gateway: Creating mission with Correlation ID: {correlation_id}")

    try:
        # Use Unified Entrypoint
        # Use correlation_id as idempotency_key for API requests if not provided in body (assuming body doesn't have it yet)
        # Ideally request.idempotency_key if exists, else correlation_id

        mission = await start_mission(
            session=db,
            objective=request.objective,
            initiator_id=1,  # System/Admin default
            context=request.context,
            force_research=False,  # API default
            idempotency_key=correlation_id,
        )

        # Map domain model to API response using helper
        return _serialize_mission(mission)

    except Exception as e:
        logger.error(f"Failed to create mission: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/missions/{mission_id}", response_model=MissionResponse, summary="Get Mission")
async def get_mission_endpoint(
    mission_id: int, req: Request, db: AsyncSession = Depends(get_db)
) -> MissionResponse:
    """
    Retrieve mission state from the Single Source of Truth.
    """
    state_manager = MissionStateManager(db)
    mission = await state_manager.get_mission(mission_id)

    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    # Use helper
    return _serialize_mission(mission)


@router.websocket("/missions/{mission_id}/ws")
async def stream_mission_ws(
    websocket: WebSocket,
    mission_id: int,
) -> None:
    """
    WebSocket Streaming BFF.
    Subscribes to internal EventBus (Unified Path).
    """
    # 1. Auth & Handshake
    token, selected_protocol = extract_websocket_auth(websocket)
    if not token:
        await websocket.close(code=4401)
        return

    try:
        decode_user_id(token, get_settings().SECRET_KEY)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept(subprotocol=selected_protocol)

    # 2. Subscribe to Event Bus (Gap-Free)
    # Since we are now in the SAME process as the execution (Control Plane),
    # the internal EventBus receives events directly from StateManager.
    # No need for Redis Bridge necessarily, but Redis Bridge might still pump events if scaled.
    event_bus = get_event_bus()
    channel = f"mission:{mission_id}"
    event_queue = event_bus.subscribe_queue(channel)

    # We need a session to fetch initial state
    from app.core.database import async_session_factory

    try:
        async with async_session_factory() as session:
            state_manager = MissionStateManager(session)

            # 3. Initial State (Snapshot)
            mission = await state_manager.get_mission(mission_id)
            if not mission:
                await websocket.close(code=4004)  # Not Found
                return

            status_payload = _get_mission_status_payload(mission.status.value)
            await websocket.send_json({"type": "mission_status", "payload": status_payload})

            # Fetch Historical Events (Gap-Free Catchup)
            events = await state_manager.get_mission_events(mission_id)
            for evt in events:
                # Format payload
                evt_type = (
                    evt.event_type.value
                    if hasattr(evt.event_type, "value")
                    else str(evt.event_type)
                )
                payload = evt.payload_json or {}

                await websocket.send_json(
                    {"type": "mission_event", "payload": {"event_type": evt_type, "data": payload}}
                )

    except Exception as e:
        logger.error(f"WS Init Error: {e}")
        await websocket.close(code=1011)
        return

    # 4. Event Loop (Standard)
    try:
        while True:
            # Wait for event
            event = await event_queue.get()

            # Format and Send
            # The internal bus sends `MissionEvent` objects (SQLModel) usually.
            # But Redis Bridge sends Dicts.
            # We need to handle both.

            payload = {}
            evt_type = ""

            if hasattr(event, "payload_json"):
                # It's an Object
                payload = event.payload_json
                evt_type = (
                    event.event_type.value
                    if hasattr(event.event_type, "value")
                    else str(event.event_type)
                )
            elif isinstance(event, dict):
                # It's a Dict (from Redis Bridge)
                payload = event.get("payload_json", {}) or event.get("data", {})
                evt_type = event.get("event_type", "")

            await websocket.send_json(
                {"type": "mission_event", "payload": {"event_type": evt_type, "data": payload}}
            )

            # Check terminal
            if evt_type in ("mission_completed", "mission_failed"):
                # Fetch final status
                async with async_session_factory() as final_session:
                    sm = MissionStateManager(final_session)
                    m = await sm.get_mission(mission_id)
                    if m:
                        status_p = _get_mission_status_payload(m.status.value)
                        await websocket.send_json({"type": "mission_status", "payload": status_p})
                await websocket.close()
                return

    except WebSocketDisconnect:
        logger.info(f"WS Disconnected: {mission_id}")
    except Exception as e:
        logger.error(f"WS Loop Error: {e}")
    finally:
        event_bus.unsubscribe_queue(channel, event_queue)
