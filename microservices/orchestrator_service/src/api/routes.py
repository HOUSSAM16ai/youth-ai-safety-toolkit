import logging
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
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
    LangGraphRunRequest,
    MissionCreate,
    MissionEventResponse,
    MissionResponse,
)
from microservices.orchestrator_service.src.services.overmind.entrypoint import start_mission
from microservices.orchestrator_service.src.services.overmind.factory import (
    create_langgraph_service,
)
from microservices.orchestrator_service.src.services.overmind.state import MissionStateManager
from microservices.orchestrator_service.src.services.overmind.utils.mission_complex import (
    handle_mission_complex_stream,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Overmind (Super Agent)"],
)


def _normalize_intent_hint(raw_intent: object) -> str | None:
    """يطبّع تلميح النية القادمة من العميل إلى صيغة موحدة."""

    if not isinstance(raw_intent, str):
        return None
    normalized = raw_intent.strip()
    if not normalized:
        return None
    alias_map = {
        "mission_complex": "MISSION_COMPLEX",
        "deep_analysis": "DEEP_ANALYSIS",
        "code_search": "CODE_SEARCH",
        "chat": "DEFAULT",
    }
    return alias_map.get(normalized.lower(), normalized.upper())


def _is_mission_complex_context(context: dict[str, object]) -> bool:
    """يتحقق من وجوب تفعيل مسار المهمة الخارقة من سياق الطلب."""

    intent_hint = _normalize_intent_hint(context.get("intent"))
    return intent_hint == "MISSION_COMPLEX"


def _json_line(payload: dict[str, object]) -> str:
    """يحوّل الحمولة إلى سطر NDJSON متوافق مع عميل الدردشة."""

    import json

    return json.dumps(payload) + "\n"


class ChatRequest(BaseModel):
    question: str
    user_id: int
    conversation_id: int | None = None
    history_messages: list[dict[str, str]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


def _sanitize_langgraph_context(
    payload: dict[str, object],
) -> dict[str, str | int | float | bool | None]:
    """ينظف السياق قبل تمريره إلى StateGraph لضمان قابلية التسلسل."""

    context: dict[str, str | int | float | bool | None] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str | int | float | bool) or value is None:
            context[key] = value
    return context


def _extract_ws_context(incoming: dict[str, object]) -> dict[str, str | int | float | bool | None]:
    """يستخلص سياق WebSocket ويطبّعه لضمان اتساق التنفيذ الحي."""

    context_payload = incoming.get("context")
    context: dict[str, str | int | float | bool | None] = {}
    if isinstance(context_payload, dict):
        context = _sanitize_langgraph_context(context_payload)

    normalized_intent = _normalize_intent_hint(incoming.get("mission_type"))
    if normalized_intent is None:
        metadata = incoming.get("metadata")
        if isinstance(metadata, dict):
            normalized_intent = _normalize_intent_hint(metadata.get("mission_type"))

    if normalized_intent is not None:
        context["intent"] = normalized_intent

    return context


def _extract_chat_objective(payload: dict[str, object]) -> str | None:
    """يستخلص الهدف النصي للدردشة من حمولة عامة بشكل صريح وآمن."""
    question = payload.get("question")
    if isinstance(question, str) and question.strip():
        return question.strip()
    objective = payload.get("objective")
    if isinstance(objective, str) and objective.strip():
        return objective.strip()
    return None


async def _run_chat_langgraph(
    objective: str,
    context: dict[str, str | int | float | bool | None],
) -> dict[str, object]:
    """يشغّل LangGraph كعمود فقري لرحلة chat ويعيد حمولة موحدة قابلة للبث."""
    service = create_langgraph_service()
    request = LangGraphRunRequest(objective=objective, context=context)
    run_data = await service.run(request)
    execution_summary = run_data.execution or {}
    response_text = str(execution_summary.get("summary") or objective)
    return {
        "status": "ok",
        "response": response_text,
        "run_id": run_data.run_id,
        "timeline": [event.model_dump(mode="json") for event in run_data.timeline],
        "graph_mode": "stategraph",
    }


@router.get("/api/chat/messages", summary="Chat Health Endpoint")
async def chat_messages_health_endpoint() -> dict[str, str]:
    """يوفر نقطة صحة توافقية لمسار chat ضمن سلطة orchestrator الموحدة."""
    return {
        "status": "ok",
        "service": "orchestrator-service",
        "control_plane": "stategraph",
    }


@router.post("/api/chat/messages", summary="StateGraph Chat Endpoint")
async def chat_messages_endpoint(payload: dict[str, object]) -> dict[str, object]:
    """ينفّذ رسالة chat عبر خدمة LangGraph ويعيد نتيجة تشغيل موحدة."""
    objective = _extract_chat_objective(payload)
    if objective is None:
        raise HTTPException(status_code=422, detail="question/objective is required")

    context_payload = payload.get("context")
    context: dict[str, str | int | float | bool | None] = {}
    if isinstance(context_payload, dict):
        context = _sanitize_langgraph_context(context_payload)

    return await _run_chat_langgraph(objective, context)


@router.websocket("/api/chat/ws")
async def chat_ws_stategraph(websocket: WebSocket) -> None:
    """يشغّل WebSocket chat فوق LangGraph لضمان توحيد مسار التنفيذ مع mission."""
    token, selected_protocol = extract_websocket_auth(websocket)
    if not token:
        await websocket.close(code=4401)
        return

    try:
        user_id = decode_user_id(token, get_settings().SECRET_KEY)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept(subprotocol=selected_protocol)
    try:
        while True:
            incoming = await websocket.receive_json()
            if not isinstance(incoming, dict):
                await websocket.send_json({"status": "error", "message": "invalid payload"})
                continue
            objective = _extract_chat_objective(incoming)
            if objective is None:
                await websocket.send_json(
                    {"status": "error", "message": "question/objective required"}
                )
                continue

            ws_context = _extract_ws_context(incoming)
            if _is_mission_complex_context({"intent": ws_context.get("intent")}):
                async for chunk in handle_mission_complex_stream(
                    objective,
                    ws_context,
                    user_id=user_id,
                ):
                    await websocket.send_text(chunk)
                continue

            result = await _run_chat_langgraph(objective, ws_context)
            result["route_id"] = "chat_ws_customer"
            await websocket.send_json(result)
    except WebSocketDisconnect:
        logger.info("Customer chat websocket disconnected")


@router.websocket("/admin/api/chat/ws")
async def admin_chat_ws_stategraph(websocket: WebSocket) -> None:
    """يشغّل WebSocket الإداري عبر LangGraph بنفس السلطة الموحدة للـ control-plane."""
    token, selected_protocol = extract_websocket_auth(websocket)
    if not token:
        await websocket.close(code=4401)
        return

    try:
        user_id = decode_user_id(token, get_settings().SECRET_KEY)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await websocket.accept(subprotocol=selected_protocol)
    try:
        while True:
            incoming = await websocket.receive_json()
            if not isinstance(incoming, dict):
                await websocket.send_json({"status": "error", "message": "invalid payload"})
                continue
            objective = _extract_chat_objective(incoming)
            if objective is None:
                await websocket.send_json(
                    {"status": "error", "message": "question/objective required"}
                )
                continue

            ws_context = _extract_ws_context(incoming)
            if _is_mission_complex_context({"intent": ws_context.get("intent")}):
                async for chunk in handle_mission_complex_stream(
                    objective,
                    ws_context,
                    user_id=user_id,
                ):
                    await websocket.send_text(chunk)
                continue

            result = await _run_chat_langgraph(objective, ws_context)
            result["route_id"] = "chat_ws_admin"
            await websocket.send_json(result)
    except WebSocketDisconnect:
        logger.info("Admin chat websocket disconnected")


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


@router.post("/agent/chat", summary="Chat with Orchestrator Agent")
async def chat_with_agent_endpoint(
    request: ChatRequest,
) -> StreamingResponse:
    """
    Direct chat endpoint for the Orchestrator Agent (Microservice).
    Streams the response chunk by chunk.
    """
    logger.info(f"Agent Chat Request: {request.question[:50]}... User: {request.user_id}")

    # Prepare context
    context = request.context.copy()
    context.update(
        {
            "user_id": request.user_id,
            "conversation_id": request.conversation_id,
            "history_messages": request.history_messages,
        }
    )

    async def _stream_generator():
        try:
            sanitized_context = _sanitize_langgraph_context(context)
            normalized_intent = _normalize_intent_hint(context.get("intent"))
            if normalized_intent is not None:
                sanitized_context["intent"] = normalized_intent

            if _is_mission_complex_context(context):
                async for chunk in handle_mission_complex_stream(
                    request.question,
                    context=sanitized_context,
                    user_id=request.user_id,
                ):
                    yield chunk
                return

            run_payload = await _run_chat_langgraph(request.question, sanitized_context)
            response_text = str(run_payload.get("response", ""))
            yield _json_line({"type": "assistant_delta", "payload": {"content": response_text}})
            yield _json_line(
                {
                    "type": "assistant_final",
                    "payload": {
                        "content": response_text,
                        "graph_mode": run_payload.get("graph_mode"),
                        "run_id": run_payload.get("run_id"),
                        "timeline": run_payload.get("timeline", []),
                    },
                }
            )
        except Exception as e:
            logger.error(f"Agent Chat Error: {e}", exc_info=True)
            yield _json_line(
                {
                    "type": "assistant_error",
                    "payload": {"content": f"Error: {e}"},
                }
            )

    return StreamingResponse(_stream_generator(), media_type="text/plain")


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


@router.get(
    "/missions/{mission_id}/events",
    response_model=list[MissionEventResponse],
    summary="Get Mission Events",
)
async def get_mission_events_endpoint(
    mission_id: int, req: Request, db: AsyncSession = Depends(get_db)
) -> list[MissionEventResponse]:
    """
    Retrieve historical events for a mission.
    """
    state_manager = MissionStateManager(db)
    events = await state_manager.get_mission_events(mission_id)

    return [
        MissionEventResponse(
            event_type=(
                evt.event_type.value if hasattr(evt.event_type, "value") else str(evt.event_type)
            ),
            mission_id=evt.mission_id,
            timestamp=evt.created_at,
            payload=evt.payload_json or {},
        )
        for evt in events
    ]


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
