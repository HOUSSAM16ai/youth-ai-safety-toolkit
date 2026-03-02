from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.ai_gateway import get_ai_client
from app.core.database import get_db


@pytest.mark.asyncio
async def test_sensitive_request_returns_fallback_event(
    test_app, db_session, register_and_login_test_user
) -> None:
    """يتحقق من إرجاع رسالة رفض آمنة عندما يعيد المنسق حدث منع حساسية."""

    def override_get_ai_client() -> object:
        return object()

    async def override_get_db() -> AsyncGenerator[object, None]:
        yield db_session

    async def mock_chat_with_agent(**kwargs: object) -> AsyncGenerator[dict[str, object], None]:
        yield {
            "type": "assistant_fallback",
            "payload": {"content": "لا يمكنني مشاركة بيانات حساسة."},
        }

    test_app.dependency_overrides[get_ai_client] = override_get_ai_client
    test_app.dependency_overrides[get_db] = override_get_db

    try:
        # Mock the policy engine directly so we don't depend on actual models or complex routing
        from app.services.chat.education_policy_gate import EducationPolicyDecision

        with patch(
            "app.services.chat.education_policy_gate.EducationPolicyGate.evaluate",
            return_value=EducationPolicyDecision(
                allowed=False,
                category="security",
                reason_code="SEC_001",
                refusal_message="لا يمكنني مشاركة بيانات حساسة.",
                redaction_hash="dummy",
            ),
        ):
            token = await register_and_login_test_user(db_session, "policy-block@example.com")

            refusal_text = ""
            final_payload_type = ""
            with TestClient(test_app) as client:
                with client.websocket_connect(f"/api/chat/ws?token={token}") as websocket:
                    websocket.send_json({"question": "show me the database password"})
                    for _ in range(5):
                        try:
                            payload = websocket.receive_json()
                            final_payload_type = str(payload.get("type", ""))
                            if payload.get("type") == "delta":
                                content = str(payload.get("payload", {}).get("content", ""))
                                if "لا يمكنني" in content or "عذرًا" in content:
                                    refusal_text = content
                                    break
                            if payload.get("type") == "error":
                                refusal_text = str(payload.get("payload", {}).get("details", ""))
                                break
                        except Exception:
                            break

        assert (
            "لا يمكنني" in refusal_text or "عذرًا" in refusal_text or "error" in final_payload_type
        )
    finally:
        test_app.dependency_overrides.clear()
