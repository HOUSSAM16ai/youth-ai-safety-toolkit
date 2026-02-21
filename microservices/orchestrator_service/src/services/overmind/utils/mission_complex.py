"""
Mission Complex Handler (Microservice).
Handles the 'MISSION_COMPLEX' intent by starting a mission and streaming events.
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from microservices.orchestrator_service.src.core.database import async_session_factory
from microservices.orchestrator_service.src.core.event_bus import get_event_bus
from microservices.orchestrator_service.src.models.mission import (
    MissionEventType,
    MissionStatus,
)
from microservices.orchestrator_service.src.services.overmind.entrypoint import start_mission

logger = logging.getLogger(__name__)


async def handle_mission_complex_stream(
    question: str,
    context: dict,
    user_id: int,
) -> AsyncGenerator[str, None]:
    """
    Handles the MISSION_COMPLEX intent.
    Starts a mission and streams structured events as NDJSON strings.
    """
    # Initial status
    yield _json_event(
        {
            "type": "assistant_delta",
            "payload": {"content": "🚀 **بدء المهمة الخارقة (Super Agent)**...\n"},
        }
    )

    # Detect Force Research Intent
    force_research = False
    q_lower = question.lower()
    if any(
        k in q_lower
        for k in ["بحث", "internet", "db", "مصادر", "search", "database", "قاعدة بيانات"]
    ):
        force_research = True

    mission_id = 0

    try:
        # Start Mission
        async with async_session_factory() as session:
            mission = await start_mission(
                session=session,
                objective=question,
                initiator_id=user_id or 1,
                context={"chat_context": True, **context},
                force_research=force_research,
            )
            mission_id = mission.id

        yield _json_event(
            {
                "type": "assistant_delta",
                "payload": {"content": f"🆔 رقم المهمة: `{mission_id}`\n⏳ البدء..."},
            }
        )

        # Emit RUN_STARTED
        sequence_id = 0
        current_iteration = 0
        sequence_id += 1
        run0_id = f"{mission_id}:{current_iteration}"
        now = datetime.now(timezone.utc).isoformat()

        yield _json_event({
            "type": "RUN_STARTED",
            "payload": {
                "run_id": run0_id,
                "seq": sequence_id,
                "timestamp": now,
                "iteration": current_iteration,
                "mode": "standard",
            },
        })

        # Subscribe to Events
        event_bus = get_event_bus()
        subscription = event_bus.subscribe(f"mission:{mission_id}")

        processed_final = False

        async for event in subscription:
            # Event comes as a dict from Redis/EventBus
            # Structure: {"event_type": ..., "payload_json": ..., ...}
            # Or if it's a raw dict from log_event

            evt_data = event
            if not isinstance(evt_data, dict):
                logger.warning(f"Received non-dict event: {evt_data}")
                continue

            # Update Iteration context
            payload = evt_data.get("payload_json", {}) or evt_data.get("data", {})
            if payload.get("brain_event") == "loop_start":
                data = payload.get("data", {})
                current_iteration = data.get("iteration", current_iteration)

            # Output Protocol (User Message)
            message = _format_event_to_message(evt_data)
            if message:
                if message.get("type") == "assistant_final":
                    processed_final = True
                yield _json_event(message)

            # Canonical Events (UI State)
            sequence_id += 1
            structured = _create_structured_event(evt_data, sequence_id, current_iteration)
            if structured:
                yield _json_event(structured)

            # Check terminal state
            evt_type = evt_data.get("event_type")
            if evt_type == "mission_completed":
                if not processed_final:
                     # Check result summary
                    result = payload.get("result", {})
                    # If format_event_to_message didn't handle it (e.g. strict type match failed), force final
                    if not message or message.get("type") != "assistant_final":
                        # Attempt to get text result
                         result_text = _extract_result_text(result)
                         yield _json_event({
                            "type": "assistant_final",
                            "payload": {"content": result_text or "✅ تمت المهمة بنجاح."},
                        })
                break # Stop subscription

            elif evt_type == "mission_failed":
                if not processed_final:
                     yield _json_event({
                        "type": "assistant_error",
                        "payload": {
                            "content": f"❌ فشلت المهمة: {payload.get('error') or 'Unknown error'}"
                        },
                    })
                break

    except Exception as e:
        logger.error(f"Error in mission complex handler: {e}", exc_info=True)
        yield _json_event(
            {
                "type": "assistant_error",
                "payload": {
                    "content": "\n🛑 **حدث خطأ حرج أثناء تنفيذ المهمة.**\n"
                },
            }
        )


def _json_event(data: dict) -> str:
    """Helper to dump JSON line."""
    return json.dumps(data) + "\n"


def _extract_result_text(result: dict | str) -> str:
    if isinstance(result, dict):
        return result.get("output") or result.get("answer") or result.get("summary") or ""
    return str(result)

def _create_structured_event(
    event_data: dict, sequence_id: int, current_iteration: int
) -> dict | None:
    """
    Create Canonical Event (Production-Grade Contract) for UI FSM.
    """
    try:
        payload = event_data.get("payload_json", {}) or event_data.get("data", {})
        mission_id = event_data.get("mission_id")
        timestamp = event_data.get("created_at") or datetime.now(timezone.utc).isoformat()
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()

        event_type = event_data.get("event_type")

        run_id = f"{mission_id}:{current_iteration}"

        if event_type in (MissionEventType.STATUS_CHANGE, "status_change"):
            brain_evt = str(payload.get("brain_event", ""))
            data = payload.get("data", {})

            if brain_evt == "loop_start":
                iteration = data.get("iteration", current_iteration)
                new_run_id = f"{mission_id}:{iteration}"
                return {
                    "type": "RUN_STARTED",
                    "payload": {
                        "run_id": new_run_id,
                        "seq": sequence_id,
                        "timestamp": timestamp,
                        "iteration": iteration,
                        "mode": data.get("graph_mode", "standard"),
                    },
                }

            if brain_evt == "phase_start":
                return {
                    "type": "PHASE_STARTED",
                    "payload": {
                        "run_id": run_id,
                        "seq": sequence_id,
                        "phase": data.get("phase"),
                        "agent": data.get("agent"),
                        "timestamp": timestamp,
                    },
                }

            if brain_evt == "phase_completed":
                return {
                    "type": "PHASE_COMPLETED",
                    "payload": {
                        "run_id": run_id,
                        "seq": sequence_id,
                        "phase": data.get("phase"),
                        "agent": data.get("agent"),
                        "timestamp": timestamp,
                    },
                }
        return None
    except Exception as e:
        logger.warning(f"Failed to create structured event: {e}")
        return None


def _format_event_to_message(event_data: dict) -> dict | None:
    """
    Format mission event into a Strict Output Contract Message.
    """
    try:
        payload = event_data.get("payload_json", {}) or event_data.get("data", {})
        event_type = event_data.get("event_type")

        # 1. Handle Final Completion
        if event_type in (MissionEventType.MISSION_COMPLETED, "mission_completed"):
            result = payload.get("result", {})
            result_text = ""

            if isinstance(result, dict):
                if result.get("output") or result.get("answer") or result.get("summary"):
                    result_text = result.get("output") or result.get("answer") or result.get("summary")
                elif "results" in result and isinstance(result["results"], list):
                     return {
                        "type": "tool_result_summary",
                        "payload": {
                            "summary": "تم تنفيذ المهام بنجاح.",
                            "items": result["results"],
                        },
                    }
                else:
                    result_text = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                result_text = str(result)

            return {"type": "assistant_final", "payload": {"content": result_text}}

        # 2. Handle Failure
        if event_type in (MissionEventType.MISSION_FAILED, "mission_failed"):
            return {
                "type": "assistant_error",
                "payload": {"content": f"💀 **فشل:** {payload.get('error')}"},
            }

        # 3. Handle Status/Progress (Assistant Delta)
        if event_type in (MissionEventType.STATUS_CHANGE, "status_change"):
            brain_evt = payload.get("brain_event")
            if brain_evt:
                text = _format_brain_event(str(brain_evt), payload.get("data", {}))
                if text:
                    return {"type": "assistant_delta", "payload": {"content": text}}

            status_note = payload.get("note")
            if status_note:
                return {
                    "type": "assistant_delta",
                    "payload": {"content": f"🔄 {status_note}\n"},
                }

        return None
    except Exception:
        return None


def _format_brain_event(event_name: str, data: dict) -> str | None:
    if not isinstance(data, dict):
        data = {}
    normalized = event_name.lower()

    if normalized.endswith("_completed") or normalized in {"phase_start", "loop_start"}:
        return None

    if normalized == "plan_rejected":
        return "🧩 إعادة ضبط الخطة.\n"

    if normalized == "plan_approved":
        return "✅ تم اعتماد الخطة.\n"

    if normalized.endswith("_timeout"):
        return "⏳ تأخير... إعادة المزامنة.\n"

    if normalized == "mission_critique_failed":
        critique = data.get("critique", {})
        feedback = critique.get("feedback", "N/A") if isinstance(critique, dict) else str(critique)
        return f"🔔 **تدقيق:** {feedback} (جاري التعديل...)\n"

    if normalized in {"mission_success", "phase_error"}:
        return f"🔔 {event_name}\n"

    return None
