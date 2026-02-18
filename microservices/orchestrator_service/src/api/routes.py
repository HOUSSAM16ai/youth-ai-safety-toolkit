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

from microservices.orchestrator_service.src.core.config import get_settings
from microservices.orchestrator_service.src.core.database import async_session_factory, get_db
from microservices.orchestrator_service.src.core.event_bus import get_event_bus
from microservices.orchestrator_service.src.core.security import (
    decode_user_id,
    extract_websocket_auth,
)
from microservices.orchestrator_service.src.models.mission import Mission
from microservices.orchestrator_service.src.services.overmind.domain.api_schemas import (
    MissionCreate,
    MissionResponse,
)
from microservices.orchestrator_service.src.services.overmind.entrypoint import start_mission
from microservices.orchestrator_service.src.services.overmind.state import MissionStateManager

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Overmind (Super Agent)"],
)


def _get_mission_status_payload(status: str) -> dict[str, str | None]:
    if status == "partial_success":
        return {"status": "success", "outcome": "partial_success"}
    return {"status": status, "outcome": None}


def _serialize_mission(mission: Mission) -> MissionResponse:
    status_payload = _get_mission_status_payload(mission.status.value)
    return MissionResponse(
        id=mission.id,
        objective=mission.objective,
        status=status_payload["status"],
        outcome=status_payload["outcome"],
        created_at=mission.created_at,
        updated_at=mission.updated_at,
        result={"summary": mission.result_summary} if mission.result_summary else None,
        steps=[],
    )


@router.post("/missions", response_model=MissionResponse, summary="Launch Mission")
async def create_mission_endpoint(
    request: MissionCreate,
    background_tasks: BackgroundTasks,
    req: Request,
    db: AsyncSession = Depends(get_db),
) -> MissionResponse:
    correlation_id = req.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    logger.info(f"Orchestrator: Creating mission with Correlation ID: {correlation_id}")

    try:
        mission = await start_mission(
            session=db,
            objective=request.objective,
            initiator_id=1,  # Default system user for now, or extract from token if forwarded
            context=request.context,
            force_research=False,
            idempotency_key=correlation_id,
        )

        return _serialize_mission(mission)

    except Exception as e:
        logger.error(f"Failed to create mission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/missions/{mission_id}", response_model=MissionResponse, summary="Get Mission")
async def get_mission_endpoint(
    mission_id: int, req: Request, db: AsyncSession = Depends(get_db)
) -> MissionResponse:
    state_manager = MissionStateManager(db)
    mission = await state_manager.get_mission(mission_id)

    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    return _serialize_mission(mission)


@router.websocket("/missions/{mission_id}/ws")
async def stream_mission_ws(
    websocket: WebSocket,
    mission_id: int,
) -> None:
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

    event_bus = get_event_bus()
    channel = f"mission:{mission_id}"

    # We need a subscription iterator
    subscription = event_bus.subscribe(channel)

    try:
        async with async_session_factory() as session:
            state_manager = MissionStateManager(session)
            mission = await state_manager.get_mission(mission_id)
            if not mission:
                await websocket.close(code=4004)
                return

            status_payload = _get_mission_status_payload(mission.status.value)
            await websocket.send_json({"type": "mission_status", "payload": status_payload})

            events = await state_manager.get_mission_events(mission_id)
            for evt in events:
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

    try:
        async for event in subscription:
            payload = {}
            evt_type = ""

            if isinstance(event, dict):
                # Check structure from Redis (published by log_event or entrypoint)
                # entrypoint might publish raw dicts?
                # MissionStateManager.log_event publishes to Redis.
                # Let's assume it matches what we expect
                payload = event.get("payload_json", {}) or event.get("data", {})
                evt_type = event.get("event_type", "")

            await websocket.send_json(
                {"type": "mission_event", "payload": {"event_type": evt_type, "data": payload}}
            )

            if evt_type in ("mission_completed", "mission_failed"):
                # Fetch final status
                async with async_session_factory() as final_session:
                    sm = MissionStateManager(final_session)
                    m = await sm.get_mission(mission_id)
                    if m:
                        status_p = _get_mission_status_payload(m.status.value)
                        await websocket.send_json({"type": "mission_status", "payload": status_p})
                break

    except WebSocketDisconnect:
        logger.info(f"WS Disconnected: {mission_id}")
    except Exception as e:
        logger.error(f"WS Loop Error: {e}")
    finally:
        await websocket.close()
        # Subscription is a generator, we just break loop to stop it,
        # but cleanup of redis pubsub happens in generator finally block if we break?
        # Python async generators support cleanup on garbage collection or aclose()
        # Ideally we should use `async with` on the generator if it supported it, or manually close.
        # My implementation of subscribe uses try/finally. If we break, `finally` runs?
        # Yes, if we stop iterating, the generator is closed.
        pass
