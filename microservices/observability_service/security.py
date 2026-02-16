import jwt
from fastapi import Header, HTTPException

from microservices.observability_service.settings import get_settings


def verify_service_token(
    x_service_token: str | None = Header(None, alias="X-Service-Token"),
) -> dict:
    """
    التحقق من صحة الرمز المميز للخدمة (Service Token).
    يضمن هذا أن الطلب قادم من بوابة API Gateway الموثوقة.
    """
    settings = get_settings()

    if not x_service_token:
        # تجاوز في وضع التطوير المحلي فقط (إذا كان DEBUG=True)
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
