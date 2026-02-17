from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from microservices.api_gateway.config import settings

security = HTTPBearer(auto_error=False)


async def verify_gateway_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> dict | None:
    """
    Verifies the user's JWT token for the Gateway.
    Skips verification for OPTIONS requests (CORS preflight).
    """
    if request.method == "OPTIONS":
        return None

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")

    try:
        return jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


def create_service_token() -> str:
    """
    Generates a short-lived JWT for service-to-service communication.
    The 'sub' claim identifies the caller as the API Gateway.
    """
    payload = {
        "sub": "api-gateway",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
