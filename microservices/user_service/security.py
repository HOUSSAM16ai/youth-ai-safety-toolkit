import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.user_service.database import get_session
from microservices.user_service.models import User
from microservices.user_service.settings import get_settings
from microservices.user_service.src.services.auth.service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_service_token(
    x_service_token: str | None = Header(None, alias="X-Service-Token"),
) -> dict:
    """
    Verify the service token (Service-to-Service auth).
    Ensures the request comes from the API Gateway.
    """
    settings = get_settings()

    if not x_service_token:
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


async def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """
    Verify the Bearer token and return the current user.
    """
    try:
        payload = service.verify_access_token(token)
        user_id = int(payload["sub"])
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except HTTPException as e:
        raise e

    user = await service.session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def require_role(role_name: str):
    async def _require_role(
        user: User = Depends(get_current_user),
        service: AuthService = Depends(get_auth_service),
    ) -> User:
        roles = await service.rbac.user_roles(user.id)
        if role_name not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role_name}",
            )
        return user

    return _require_role
