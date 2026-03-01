import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings.base import get_settings


async def _create_user_and_token(db_session: AsyncSession, email: str) -> str:
    """ينشئ مستخدم اختبار مباشرةً ويعيد رمز JWT صالحًا دون الاعتماد على خدمات خارجية."""

    insert_statement = text(
        """
        INSERT INTO users (
            external_id,
            full_name,
            email,
            password_hash,
            is_admin,
            is_active,
            status
        )
        VALUES (:external_id, :full_name, :email, :password_hash, :is_admin, :is_active, :status)
        """
    )
    result = await db_session.execute(
        insert_statement,
        {
            "external_id": f"test-{email}",
            "full_name": "Student User",
            "email": email,
            "password_hash": "not-used-in-this-test",
            "is_admin": False,
            "is_active": True,
            "status": "active",
        },
    )
    await db_session.commit()

    user_id = int(result.lastrowid)
    return jwt.encode({"sub": str(user_id)}, get_settings().SECRET_KEY, algorithm="HS256")


def _consume_stream_until_terminal(websocket: object) -> list[dict[str, object]]:
    """يجمع أحداث البث حتى ظهور حدث نهائي أو رسالة خطأ."""

    messages: list[dict[str, object]] = []
    for _ in range(8):
        payload = websocket.receive_json()
        messages.append(payload)
        event_type = str(payload.get("type", ""))
        if event_type in {"assistant_final", "assistant_error", "assistant_fallback", "error"}:
            break
    return messages
