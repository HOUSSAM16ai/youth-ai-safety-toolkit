"""
موجه واجهة نظام إدارة المستخدمين مع حراسة RBAC وبوابة السياسات.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.ums import (
    AdminCreateUserRequest,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    ProfileUpdateRequest,
    QuestionRequest,
    ReauthRequest,
    ReauthResponse,
    RefreshRequest,
    RegisterRequest,
    RoleAssignmentRequest,
    StatusUpdateRequest,
    TokenPair,
    UserOut,
)
from app.core.database import get_db
from app.core.domain.audit import AuditLog
from app.core.domain.user import UserStatus
from app.deps.auth import CurrentUser, get_current_user, require_permissions
from app.middleware.rate_limiter_middleware import rate_limit
from app.services.audit import AuditService
from app.services.boundaries.auth_boundary_service import AuthBoundaryService
from app.services.policy import PolicyService
from app.services.rbac import (
    ACCOUNT_SELF,
    ADMIN_ROLE,
    AI_CONFIG_READ,
    AI_CONFIG_WRITE,
    AUDIT_READ,
    QA_SUBMIT,
    ROLES_WRITE,
    USERS_READ,
    USERS_WRITE,
)

router = APIRouter(tags=["User Management"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthBoundaryService:
    return AuthBoundaryService(db)


def _audit_context(request: Request) -> tuple[str | None, str | None]:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    return client_ip, user_agent


async def _enforce_recent_auth(
    *,
    request: Request,
    auth_service: AuthBoundaryService,
    current: CurrentUser,
    provided_token: str | None,
    provided_password: str | None,
) -> None:
    """Check for recent authentication proof."""
    token = provided_token or request.headers.get("X-Reauth-Token")
    password = provided_password or request.headers.get("X-Reauth-Password")

    if token:
        auth_service.verify_reauth_proof(token, current.user.id)
        return

    if password and current.user.check_password(password):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Re-authentication required"
    )


@router.post("/auth/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=300, limiter_key="auth_register")
async def register_user(
    request: Request,
    payload: RegisterRequest,
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> TokenPair:
    _, _ = _audit_context(request)

    # 1. Register via Microservice
    await auth_service.register_user(
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
    )

    # 2. Login immediately via Microservice
    auth_result = await auth_service.authenticate_user(
        email=payload.email,
        password=payload.password,
        request=request,
    )

    return TokenPair(
        access_token=str(auth_result.get("access_token")),
        refresh_token=str(auth_result.get("refresh_token") or ""),
        token_type=str(auth_result.get("token_type", "Bearer")),
    )


@router.get("/users/me", response_model=UserOut)
async def get_me(
    request: Request,
    current: CurrentUser = Depends(require_permissions(ACCOUNT_SELF)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> UserOut:
    """Return current user profile using local context (synced via shared DB)."""
    # Since we share the DB, current.user is fresh enough for basic profile.
    # Roles are fetched via RBAC locally.
    # To use microservice fully, we would call auth_service.get_current_user(token).
    # But current.user is already injected.

    # Re-fetch roles locally to match schema
    # AuthBoundaryService doesn't expose rbac directly, but initialized AuthPersistence with session.
    # We can access auth_service.db
    from app.services.rbac import RBACService

    rbac = RBACService(auth_service.db)
    roles = await rbac.user_roles(current.user.id)

    return UserOut(
        id=current.user.id,
        email=current.user.email,
        full_name=current.user.full_name,
        is_active=current.user.is_active,
        status=current.user.status,
        roles=roles,
    )


@router.patch("/users/me", response_model=UserOut)
async def update_me(
    request: Request,
    payload: ProfileUpdateRequest,
    current: CurrentUser = Depends(require_permissions(ACCOUNT_SELF)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> UserOut:
    """Update profile via Microservice."""
    _, _ = _audit_context(request)
    token = AuthBoundaryService.extract_token_from_request(request)

    result = await auth_service.update_profile(
        token=token, full_name=payload.full_name, email=payload.email
    )

    # Construct UserOut from result dict
    # Microservice result has 'roles' in it.
    roles = result.get("roles", [])
    if not roles:
        # Fallback fetch if missing
        from app.services.rbac import RBACService

        rbac = RBACService(auth_service.db)
        roles = await rbac.user_roles(current.user.id)

    return UserOut(
        id=int(result["id"]),  # type: ignore
        email=str(result["email"]),
        full_name=str(result.get("full_name") or result.get("name")),
        is_active=bool(result.get("is_active", True)),
        status=UserStatus(result.get("status", "active")),
        roles=roles,
    )


@router.post("/users/me/change-password")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current: CurrentUser = Depends(require_permissions(ACCOUNT_SELF)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> dict[str, str]:
    """Change password via Microservice."""
    token = AuthBoundaryService.extract_token_from_request(request)
    await auth_service.change_password(
        token=token, current_password=payload.current_password, new_password=payload.new_password
    )
    return {"status": "password_changed"}


@router.post("/auth/login", response_model=TokenPair)
@rate_limit(max_requests=5, window_seconds=60, limiter_key="auth_login")
async def login(
    request: Request,
    payload: LoginRequest,
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> TokenPair:
    auth_result = await auth_service.authenticate_user(
        email=payload.email,
        password=payload.password,
        request=request,
    )
    return TokenPair(
        access_token=str(auth_result.get("access_token")),
        refresh_token=str(auth_result.get("refresh_token") or ""),
        token_type=str(auth_result.get("token_type", "Bearer")),
    )


@router.post("/auth/reauth", response_model=ReauthResponse)
async def reauth(
    request: Request,
    payload: ReauthRequest,
    current: CurrentUser = Depends(get_current_user),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> ReauthResponse:
    client_ip, user_agent = _audit_context(request)
    token, expires_in = await auth_service.issue_reauth_proof(
        user_id=current.user.id, password=payload.password, ip=client_ip, user_agent=user_agent
    )
    return ReauthResponse(reauth_token=token, expires_in=expires_in)


@router.post("/auth/refresh", response_model=TokenPair)
@rate_limit(max_requests=20, window_seconds=60, limiter_key="auth_refresh")
async def refresh_token(
    request: Request,
    payload: RefreshRequest,
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> TokenPair:
    client_ip, user_agent = _audit_context(request)
    result = await auth_service.refresh_session(
        refresh_token=payload.refresh_token,
        ip=client_ip,
        user_agent=user_agent,
    )
    return TokenPair(
        access_token=str(result["access_token"]),
        refresh_token=str(result["refresh_token"]),
        token_type=str(result["token_type"]),
    )


@router.post("/auth/logout")
async def logout(
    request: Request,
    payload: LogoutRequest,
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> dict[str, str]:
    client_ip, user_agent = _audit_context(request)
    await auth_service.logout(
        refresh_token=payload.refresh_token, ip=client_ip, user_agent=user_agent
    )
    return {"status": "logged_out"}


@router.post("/auth/password/forgot", response_model=PasswordResetResponse)
@rate_limit(max_requests=5, window_seconds=900, limiter_key="auth_password_forgot")
async def request_password_reset(
    request: Request,
    payload: PasswordResetRequest,
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> PasswordResetResponse:
    # Microservice response is dict
    result = await auth_service.forgot_password(email=payload.email)
    # result keys might be reset_token, expires_in
    return PasswordResetResponse(
        reset_token=str(result.get("reset_token")) if result.get("reset_token") else None,
        expires_in=int(result.get("expires_in")) if result.get("expires_in") else None,
    )


@router.post("/auth/password/reset")
@rate_limit(max_requests=10, window_seconds=300, limiter_key="auth_password_reset")
async def reset_password(
    request: Request,
    payload: PasswordResetConfirmRequest,
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> dict[str, str]:
    # Wait, password reset usually uses a specific reset token, not auth token.
    # Microservice 'reset_password' takes 'token' and 'new_password'.
    # This 'token' is the reset token from email.
    # The client/schema names it 'token'.
    # auth_service.reset_password(token, new_pw).
    await auth_service.reset_password(
        token=payload.token,
        new_password=payload.new_password,
    )
    return {"status": "password_reset"}


@router.get("/admin/users", response_model=list[UserOut])
async def list_users(
    _: CurrentUser = Depends(require_permissions(USERS_READ)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> list[UserOut]:
    # Use Microservice via Boundary
    users_data = await auth_service.list_users()

    output = []
    for u_dict in users_data:
        # Microservice returns UserOut structure with roles
        output.append(
            UserOut(
                id=int(u_dict["id"]),  # type: ignore
                email=str(u_dict["email"]),
                full_name=str(u_dict.get("full_name") or u_dict.get("name")),
                is_active=bool(u_dict.get("is_active", True)),
                status=UserStatus(u_dict.get("status", "active")),
                roles=u_dict.get("roles", []),  # type: ignore
            )
        )
    return output


@router.post("/admin/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    request: Request,
    payload: AdminCreateUserRequest,
    current: CurrentUser = Depends(require_permissions(USERS_WRITE, ROLES_WRITE)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> UserOut:
    token = AuthBoundaryService.extract_token_from_request(request)

    if payload.is_admin:
        await _enforce_recent_auth(
            request=request,
            auth_service=auth_service,
            current=current,
            provided_token=None,
            provided_password=None,
        )

    result = await auth_service.create_user_admin(
        token=token,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        is_admin=payload.is_admin,
    )

    return UserOut(
        id=int(result["id"]),  # type: ignore
        email=str(result["email"]),
        full_name=str(result.get("full_name") or result.get("name")),
        is_active=bool(result.get("is_active", True)),
        status=UserStatus(result.get("status", "active")),
        roles=result.get("roles", []),  # type: ignore
    )


@router.patch("/admin/users/{user_id}/status", response_model=UserOut)
async def update_user_status(
    request: Request,
    user_id: int,
    payload: StatusUpdateRequest,
    current: CurrentUser = Depends(require_permissions(USERS_WRITE)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> UserOut:
    token = AuthBoundaryService.extract_token_from_request(request)

    result = await auth_service.update_user_status(
        token=token, user_id=user_id, status=payload.status.value
    )

    return UserOut(
        id=int(result["id"]),  # type: ignore
        email=str(result["email"]),
        full_name=str(result.get("full_name") or result.get("name")),
        is_active=bool(result.get("is_active", True)),
        status=UserStatus(result.get("status", "active")),
        roles=result.get("roles", []),  # type: ignore
    )


@router.post("/admin/users/{user_id}/roles", response_model=UserOut)
async def assign_role(
    request: Request,
    user_id: int,
    payload: RoleAssignmentRequest,
    current: CurrentUser = Depends(require_permissions(USERS_WRITE, ROLES_WRITE)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> UserOut:
    token = AuthBoundaryService.extract_token_from_request(request)

    if payload.role_name == ADMIN_ROLE:
        await _enforce_recent_auth(
            request=request,
            auth_service=auth_service,
            current=current,
            provided_token=payload.reauth_token,
            provided_password=payload.reauth_password,
        )
        if not payload.justification or len(payload.justification.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Justification required for admin assignment",
            )

    result = await auth_service.assign_role(
        token=token, user_id=user_id, role_name=payload.role_name
    )

    return UserOut(
        id=int(result["id"]),  # type: ignore
        email=str(result["email"]),
        full_name=str(result.get("full_name") or result.get("name")),
        is_active=bool(result.get("is_active", True)),
        status=UserStatus(result.get("status", "active")),
        roles=result.get("roles", []),  # type: ignore
    )


@router.get("/admin/audit", response_model=list[dict])
async def list_audit(
    _: CurrentUser = Depends(require_permissions(AUDIT_READ)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    # Keeping local audit log read for now as Auditor Service client is not ready
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit out of range")
    if offset < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="offset out of range")

    result = await auth_service.db.execute(
        select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    )
    rows = result.scalars().all()
    return [row.model_dump() for row in rows]


@router.get("/admin/ai-config")
async def get_ai_config(
    _: CurrentUser = Depends(require_permissions(AI_CONFIG_READ)),
) -> dict[str, str]:
    return {"status": "ok", "message": "AI config readable"}


@router.put("/admin/ai-config")
async def update_ai_config(
    _: CurrentUser = Depends(require_permissions(AI_CONFIG_WRITE)),
) -> dict[str, str]:
    return {"status": "ok", "message": "AI config updated"}


@router.post("/qa/question")
async def ask_question(
    request: Request,
    payload: QuestionRequest,
    current: CurrentUser = Depends(require_permissions(QA_SUBMIT)),
    auth_service: AuthBoundaryService = Depends(get_auth_service),
) -> dict[str, str]:
    policy = PolicyService()
    primary_role = ADMIN_ROLE if ADMIN_ROLE in current.roles else "STANDARD_USER"
    decision = policy.enforce_policy(user_role=primary_role, question=payload.question)
    client_ip, user_agent = _audit_context(request)

    if not decision.allowed:
        audit = AuditService(auth_service.db)
        await audit.record(
            actor_user_id=current.user.id,
            action="POLICY_BLOCK",
            target_type="question",
            target_id=str(decision.redaction_hash),
            metadata={"reason": decision.reason, "classification": decision.classification},
            ip=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)

    return {
        "status": "accepted",
        "classification": decision.classification,
        "message": "question accepted",
    }
