"""
Auth Routes for User Service.
"""

from fastapi import APIRouter, Depends, Request

from microservices.user_service.security import get_auth_service, get_current_user
from microservices.user_service.src.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    ReauthRequest,
    ReauthResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenGenerateResponse,
    TokenVerifyRequest,
    TokenVerifyResponse,
    UserResponse,
)
from microservices.user_service.src.services.auth.service import AuthService

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=RegisterResponse)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    user = await service.register_user(
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
    )
    # Convert User model to UserResponse schema
    user_response = UserResponse.model_validate(user)
    return RegisterResponse(user=user_response, message="User registered successfully")


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user = await service.authenticate(
        email=payload.email,
        password=payload.password,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    tokens = await service.issue_tokens(
        user,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    user_response = UserResponse.model_validate(user)
    return AuthResponse(
        access_token=tokens["access_token"],
        user=user_response,
        status="success",
    )


@router.post("/refresh", response_model=TokenGenerateResponse)
async def refresh_token(
    payload: RefreshRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenGenerateResponse:
    tokens = await service.refresh_session(
        refresh_token=payload.refresh_token,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return TokenGenerateResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
    )


@router.post("/reauth", response_model=ReauthResponse)
async def reauth(
    payload: ReauthRequest,
    request: Request,
    user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> ReauthResponse:
    token, expires_in = await service.issue_reauth_proof(
        user=user,
        password=payload.password,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return ReauthResponse(reauth_token=token, expires_in=expires_in)


@router.post("/logout")
async def logout(
    payload: LogoutRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    await service.logout(
        refresh_token=payload.refresh_token,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return {"status": "logged_out"}


@router.get("/user/me", response_model=UserResponse)
async def get_me(
    user=Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/token/verify", response_model=TokenVerifyResponse)
async def verify_token(
    payload: TokenVerifyRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenVerifyResponse:
    if not payload.token:
        return TokenVerifyResponse(status="error", data={"valid": False, "error": "Missing token"})
    try:
        service.verify_access_token(payload.token)
        return TokenVerifyResponse(status="success", data={"valid": True})
    except Exception as e:
        return TokenVerifyResponse(status="error", data={"valid": False, "error": str(e)})
