"""
Crypto Logic for User Service.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Final

import jwt
from fastapi import HTTPException, status

from microservices.user_service.models import User
from microservices.user_service.settings import get_settings

ACCESS_EXPIRE_MINUTES: Final[int] = 30
REAUTH_EXPIRE_MINUTES: Final[int] = 10


class AuthCrypto:
    def __init__(self) -> None:
        self.settings = get_settings()

    def hash_identifier(self, value: str) -> str:
        digest = sha256(value.encode()).hexdigest()
        return digest[:16]

    def encode_access_token(self, user: User, roles: list[str], permissions: set[str]) -> str:
        # Assuming settings has SECRET_KEY.
        # Note: User Service settings might not have ACCESS_TOKEN_EXPIRE_MINUTES defined yet.
        # I'll default to 30 if missing or use logic similar to monolith.
        expire_min = getattr(self.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", ACCESS_EXPIRE_MINUTES)
        expires_delta = timedelta(minutes=min(expire_min, ACCESS_EXPIRE_MINUTES))

        payload = {
            "sub": str(user.id),
            "roles": roles,
            "permissions": sorted(permissions),
            "jti": secrets.token_urlsafe(8),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + expires_delta,
        }
        return jwt.encode(payload, self.settings.SECRET_KEY, algorithm="HS256")

    def encode_reauth_token(self, user: User) -> tuple[str, int]:
        expire_min = getattr(self.settings, "REAUTH_TOKEN_EXPIRE_MINUTES", REAUTH_EXPIRE_MINUTES)
        expires_delta = timedelta(minutes=min(expire_min, REAUTH_EXPIRE_MINUTES))

        payload = {
            "sub": str(user.id),
            "purpose": "reauth",
            "jti": secrets.token_urlsafe(8),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + expires_delta,
        }
        token = jwt.encode(payload, self.settings.SECRET_KEY, algorithm="HS256")
        return token, int(expires_delta.total_seconds())

    def split_refresh_token(self, token: str) -> tuple[str, str]:
        try:
            token_id_part, secret_part = token.split(":", maxsplit=1)
            return token_id_part, secret_part
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token format"
            ) from exc

    def verify_jwt(self, token: str) -> dict[str, object]:
        try:
            return jwt.decode(token, self.settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from exc
