"""
مساعدات مصادقة WebSocket.

توفر هذه الوحدة أدوات خفيفة وآمنة لاستخراج رمز الوصول من
رؤوس بروتوكولات WebSocket أو من معاملات الاستعلام كحل تراثي.
"""

from fastapi import WebSocket

from app.core.settings.base import get_settings


def _parse_protocol_header(protocol_header: str | None) -> list[str]:
    """
    تحليل ترويسة بروتوكولات WebSocket إلى قائمة مرتبة ونظيفة.

    Args:
        protocol_header: قيمة ترويسة `sec-websocket-protocol`.

    Returns:
        قائمة بالبروتوكولات بعد التنقية.
    """

    if not protocol_header:
        return []
    return [protocol.strip() for protocol in protocol_header.split(",") if protocol.strip()]


def _extract_token_from_protocols(protocols: list[str]) -> str | None:
    """
    استخراج رمز الوصول من قائمة البروتوكولات المتفاوض عليها.

    الاتفاق الحالي يتوقع أن يرسل العميل البروتوكولين:
    ["jwt", "<token>"] ضمن ترويسة `sec-websocket-protocol`.

    Args:
        protocols: قائمة البروتوكولات المرسلة من العميل.

    Returns:
        رمز الوصول إذا توفر وفق الاتفاق، وإلا `None`.
    """

    if "jwt" not in protocols:
        return None

    try:
        jwt_index = protocols.index("jwt")
    except ValueError:
        return None

    # Ensure there is a token following the 'jwt' protocol specifier
    if jwt_index + 1 >= len(protocols):
        return None

    return protocols[jwt_index + 1]


def extract_websocket_auth(websocket: WebSocket) -> tuple[str | None, str | None]:
    """
    استخراج رمز الدخول والبروتوكول المختار من طلب WebSocket.

    نحاول أولاً قراءة الرمز من ترويسة البروتوكول (أكثر أماناً من الـ query).
    وعند الفشل نستخدم معامل الاستعلام `token` لأجل التوافق،
    لكن هذا المسار يُعطّل تلقائياً في بيئات الإنتاج والتهيئة المرحلية.

    Args:
        websocket: كائن WebSocket الوارد من FastAPI.

    Returns:
        زوج (token, selected_protocol) حيث يمكن أن تكون القيم `None`.
    """

    protocols = _parse_protocol_header(websocket.headers.get("sec-websocket-protocol"))
    token = _extract_token_from_protocols(protocols)
    if token:
        selected_protocol = "jwt" if "jwt" in protocols else None
        return token, selected_protocol

    fallback_token = websocket.query_params.get("token")
    if not fallback_token:
        return None, None

    settings = get_settings()
    if settings.ENVIRONMENT in ("production", "staging"):
        return None, None

    return fallback_token, None
