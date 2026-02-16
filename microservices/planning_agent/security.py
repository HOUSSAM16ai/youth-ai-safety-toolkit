import jwt
from fastapi import Header, HTTPException

from microservices.planning_agent.settings import get_settings


def verify_service_token(
    x_service_token: str | None = Header(None, alias="X-Service-Token"),
) -> dict:
    """
    التحقق من صحة الرمز المميز للخدمة (Service Token).
    يضمن هذا أن الطلب قادم من بوابة API Gateway الموثوقة.
    """
    settings = get_settings()

    if not x_service_token:
        # إذا كنا في بيئة اختبار أو تطوير محلي، قد نسمح بالتجاوز،
        # ولكن "الجودة الفائقة" تتطلب الصرامة.
        # ومع ذلك، لتسهيل التطوير المحلي بدون Gateway، يمكننا التحقق من DEBUG.
        if settings.DEBUG:
            return {"sub": "debug-mode"}
        raise HTTPException(status_code=401, detail="Missing X-Service-Token header")

    try:
        payload = jwt.decode(x_service_token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("sub") != "api-gateway":
            raise HTTPException(status_code=403, detail="Invalid token subject")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Service token has expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid service token") from None
