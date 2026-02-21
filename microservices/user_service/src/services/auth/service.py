"""
Auth Service Facade for User Service.
"""

from __future__ import annotations

from typing import TypedDict

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.user_service.models import RefreshToken, User, UserStatus
from microservices.user_service.src.core.security import pwd_context
from microservices.user_service.src.services.audit import AuditService
from microservices.user_service.src.services.auth.crypto import AuthCrypto
from microservices.user_service.src.services.auth.password_manager import PasswordManager
from microservices.user_service.src.services.auth.registration import RegistrationManager
from microservices.user_service.src.services.auth.token_manager import TokenManager
from microservices.user_service.src.services.rbac import ADMIN_ROLE, RBACService


class TokenBundle(TypedDict):
    access_token: str
    refresh_token: str
    token_type: str


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rbac = RBACService(session)
        self.audit = AuditService(session)

        # Initialize Sub-components
        self.crypto = AuthCrypto()  # Settings loaded internally
        self.token_manager = TokenManager(session)
        self.password_manager = PasswordManager(session)
        self.registration_manager = RegistrationManager(session, self.rbac)

    async def register_user(
        self,
        *,
        full_name: str,
        email: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        try:
            user = await self.registration_manager.register_user(
                full_name=full_name, email=email, password=password
            )
            await self.audit.record(
                actor_user_id=user.id,
                action="USER_REGISTERED",
                target_type="user",
                target_id=str(user.id),
                metadata={"email_hash": self.crypto.hash_identifier(email.lower().strip())},
                ip=ip,
                user_agent=user_agent,
            )
            return user
        except Exception:
            raise

    async def authenticate(
        self,
        *,
        email: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        await self.rbac.ensure_seed()
        normalized_email = email.lower().strip()
        result = await self.session.execute(select(User).where(User.email == normalized_email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash or not user.check_password(password):
            await self.audit.record(
                actor_user_id=None,
                action="AUTH_FAILED",
                target_type="user",
                target_id=None,
                metadata={"email_hash": self.crypto.hash_identifier(normalized_email)},
                ip=ip,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        if not user.is_active or user.status in {UserStatus.SUSPENDED, UserStatus.DISABLED}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

        await self.audit.record(
            actor_user_id=user.id,
            action="AUTH_SUCCEEDED",
            target_type="user",
            target_id=str(user.id),
            metadata={"status": user.status.value},
            ip=ip,
            user_agent=user_agent,
        )
        return user

    async def issue_tokens(
        self,
        user: User,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenBundle:
        roles = await self.rbac.user_roles(user.id)
        permissions = await self.rbac.user_permissions(user.id)
        access_token = self.crypto.encode_access_token(user, roles, permissions)
        refresh_value = await self.token_manager.create_refresh_token(
            user, ip=ip, user_agent=user_agent, family_id=None
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_value,
            "token_type": "Bearer",
        }

    def _split_refresh_token(self, refresh_token: str) -> tuple[str, str]:
        return self.crypto.split_refresh_token(refresh_token)

    async def _get_refresh_record(self, token_id: str) -> RefreshToken | None:
        return await self.token_manager.get_refresh_record(token_id)

    async def update_profile(
        self,
        *,
        user: User,
        full_name: str | None,
        email: str | None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        await self.rbac.ensure_seed()
        changed_fields: list[str] = []

        if full_name and full_name.strip() and full_name != user.full_name:
            user.full_name = full_name.strip()
            changed_fields.append("full_name")

        if email:
            normalized_email = email.lower().strip()
            if normalized_email != user.email:
                conflict = await self.session.execute(
                    select(User).where(User.email == normalized_email, User.id != user.id)
                )
                if conflict.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
                    )
                user.email = normalized_email
                changed_fields.append("email")

        if not changed_fields:
            return user

        await self.session.commit()
        await self.session.refresh(user)
        await self.audit.record(
            actor_user_id=user.id,
            action="PROFILE_UPDATED",
            target_type="user",
            target_id=str(user.id),
            metadata={"fields": changed_fields},
            ip=ip,
            user_agent=user_agent,
        )
        return user

    async def issue_reauth_proof(
        self,
        *,
        user: User,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, int]:
        if not user.check_password(password):
            await self.audit.record(
                actor_user_id=user.id,
                action="REAUTH_REJECTED",
                target_type="user",
                target_id=str(user.id),
                metadata={"reason": "bad_password"},
                ip=ip,
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Re-authentication required"
            )

        token, expires_in = self.crypto.encode_reauth_token(user)
        await self.audit.record(
            actor_user_id=user.id,
            action="REAUTH_SUCCEEDED",
            target_type="user",
            target_id=str(user.id),
            metadata={"expires_in": expires_in},
            ip=ip,
            user_agent=user_agent,
        )
        return token, expires_in

    async def verify_reauth_proof(
        self,
        token: str,
        *,
        user: User,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        try:
            payload = self.crypto.verify_jwt(token)
        except HTTPException as exc:
            raise exc

        if payload.get("purpose") != "reauth" or payload.get("sub") != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Re-authentication required"
            )

    async def refresh_session(
        self,
        *,
        refresh_token: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenBundle:
        token_id, secret = self.crypto.split_refresh_token(refresh_token)
        record = await self.token_manager.get_refresh_record(token_id)

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        if record.revoked_at is not None or record.replaced_by_token_id is not None:
            await self.token_manager.revoke_family(record.family_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        if not record.is_active():
            await self.token_manager.revoke_record(record)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        if not pwd_context.verify(secret, record.hashed_token):
            await self.token_manager.revoke_record(record)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        user = await self.session.get(User, record.user_id)
        if user is None or not user.is_active:
            await self.token_manager.revoke_record(record)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

        new_refresh_value = await self.token_manager.create_refresh_token(
            user,
            family_id=record.family_id,
            ip=ip,
            user_agent=user_agent,
        )
        new_token_id, _ = self.crypto.split_refresh_token(new_refresh_value)
        await self.token_manager.revoke_record(record, replaced_by=new_token_id)

        roles = await self.rbac.user_roles(user.id)
        permissions = await self.rbac.user_permissions(user.id)
        access_token = self.crypto.encode_access_token(user, roles, permissions)

        refreshed: TokenBundle = {
            "access_token": access_token,
            "refresh_token": new_refresh_value,
            "token_type": "Bearer",
        }
        await self.audit.record(
            actor_user_id=user.id,
            action="REFRESH_ROTATED",
            target_type="refresh_token",
            target_id=token_id,
            metadata={"status": user.status.value, "family_id": record.family_id},
            ip=ip,
            user_agent=user_agent,
        )
        return refreshed

    async def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if not user.check_password(current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
            )

        user.set_password(new_password)
        await self.session.commit()
        revoked = await self.token_manager.revoke_user_tokens(user)
        await self.audit.record(
            actor_user_id=user.id,
            action="PASSWORD_CHANGED",
            target_type="user",
            target_id=str(user.id),
            metadata={"revoked_refresh_tokens": revoked},
            ip=ip,
            user_agent=user_agent,
        )

    async def request_password_reset(
        self,
        *,
        email: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str | None, int | None]:
        normalized_email = email.lower().strip()
        result = await self.session.execute(select(User).where(User.email == normalized_email))
        user = result.scalar_one_or_none()

        if not user:
            return None, None

        token_value, expires_in, record = await self.password_manager.create_reset_token(
            user, ip, user_agent
        )

        await self.audit.record(
            actor_user_id=user.id,
            action="PASSWORD_RESET_REQUESTED",
            target_type="user",
            target_id=str(user.id),
            metadata={"token_id": record.token_id, "expires_at": record.expires_at.isoformat()},
            ip=ip,
            user_agent=user_agent,
        )
        return token_value, expires_in

    async def reset_password(
        self,
        *,
        token: str,
        new_password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        try:
            user = await self.password_manager.verify_and_redeem_token(token)
        except HTTPException as exc:
            raise exc

        user.set_password(new_password)
        await self.session.commit()
        revoked = await self.token_manager.revoke_user_tokens(user)

        await self.audit.record(
            actor_user_id=user.id,
            action="PASSWORD_RESET_COMPLETED",
            target_type="user",
            target_id=str(user.id),
            metadata={"revoked_refresh_tokens": revoked},
            ip=ip,
            user_agent=user_agent,
        )

    async def logout(
        self, *, refresh_token: str, ip: str | None = None, user_agent: str | None = None
    ) -> None:
        try:
            token_id, _ = self.crypto.split_refresh_token(refresh_token)
            record = await self.token_manager.get_refresh_record(token_id)
            if record:
                await self.token_manager.revoke_family(record.family_id)
                await self.audit.record(
                    actor_user_id=record.user_id,
                    action="LOGOUT",
                    target_type="refresh_token",
                    target_id=token_id,
                    metadata={"status": "family_revoked", "family_id": record.family_id},
                    ip=ip,
                    user_agent=user_agent,
                )
        except HTTPException:
            pass

    async def promote_to_admin(self, *, user: User) -> None:
        await self.rbac.ensure_seed()
        await self.rbac.assign_role(user, ADMIN_ROLE)
        if not user.is_admin:
            user.is_admin = True
            await self.session.commit()

    def verify_access_token(self, token: str) -> dict[str, object]:
        return self.crypto.verify_jwt(token)
