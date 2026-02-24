"""
خدمة حدود المصادقة (Auth Boundary Service).

تمثل هذه الخدمة الواجهة الموحدة (Facade) لعمليات المصادقة، حيث تقوم بتنسيق منطق الأعمال
بين طبقة العرض (Router) وطبقة البيانات (Persistence).

المعايير المطبقة (Standards Applied):
- CS50 2025: توثيق عربي احترافي، صرامة في الأنواع.
- SOLID: فصل المسؤوليات (Separation of Concerns).
- Security First: تكامل مع درع الدفاع الزمني (Chrono-Kinetic Defense Shield).
- Microservices First: استخدام خدمة المستخدمين (User Service) مع خطة طوارئ (Fallback).
"""

from __future__ import annotations

import datetime
import logging

import httpx
import jwt
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.clients.user_client import user_service_client
from app.security.chrono_shield import chrono_shield
from app.services.rbac import STANDARD_ROLE, RBACService
from app.services.security.auth_persistence import AuthPersistence

logger = logging.getLogger(__name__)

__all__ = ["AuthBoundaryService"]


class AuthBoundaryService:
    """
    خدمة حدود المصادقة (Auth Boundary Service).

    المسؤوليات:
    - تنسيق عمليات تسجيل الدخول والتسجيل.
    - إدارة الرموز المميزة (JWT Management).
    - حماية النظام باستخدام درع كرونو (Chrono Shield Integration).
    - الوكيل (Proxy) لخدمة المستخدمين المصغرة (User Service).
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        تهيئة خدمة المصادقة.

        Args:
            db (AsyncSession): جلسة قاعدة البيانات غير المتزامنة.
        """
        self.db = db
        self.persistence = AuthPersistence(db)
        self.settings = get_settings()

    async def register_user(self, full_name: str, email: str, password: str) -> dict[str, object]:
        """
        تسجيل مستخدم جديد في النظام.

        يحاول استخدام خدمة المستخدمين (User Service) أولاً.
        في حال فشل الاتصال، يعود لاستخدام النظام المحلي (Monolith).

        Args:
            full_name (str): الاسم الكامل.
            email (str): البريد الإلكتروني.
            password (str): كلمة المرور.

        Returns:
            dict[str, object]: تفاصيل العملية والمستخدم المسجل.

        Raises:
            HTTPException: في حال وجود البريد الإلكتروني مسبقاً (400).
        """
        # محاولة التسجيل عبر الخدمة المصغرة (Microservice)
        try:
            response = await user_service_client.register_user(full_name, email, password)
            # تحويل استجابة الخدمة إلى التنسيق المتوقع محلياً
            # response format: {"user": {...}, "message": "..."}
            user_data = response.get("user", {})
            return {
                "status": "success",
                "message": response.get("message", "User registered successfully"),
                "user": {
                    "id": user_data.get("id"),
                    "full_name": user_data.get("full_name"),
                    "email": user_data.get("email"),
                    "is_admin": user_data.get("is_admin", False),
                },
            }
        except httpx.HTTPStatusError as e:
            # إذا رفضت الخدمة الطلب (مثلاً البريد موجود)، نرفع الخطأ كما هو
            # باستثناء الحالات التي تدل غالباً على عدم جاهزية الخدمة أو رفض على مستوى البوابة
            # (مثل 401/403/5xx) حيث ننتقل إلى الخطة المحلية البديلة.
            logger.warning(f"User Service rejected registration: {e}")
            if e.response.status_code == 400:
                raise HTTPException(status_code=400, detail="Email already registered") from e
            if e.response.status_code not in {401, 403, 404, 429} and e.response.status_code < 500:
                raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
            logger.error(
                "User Service registration endpoint unavailable (%s), using local fallback.",
                e.response.status_code,
            )
        except (httpx.RequestError, httpx.TimeoutException, Exception) as e:
            # في حال فشل الاتصال، نستخدم الخطة البديلة (Local Fallback)
            logger.error(f"User Service unreachable for registration ({e}), using local fallback.")

        # ==============================================================================
        # Local Fallback (Monolith Logic)
        # ==============================================================================
        if await self.persistence.user_exists(email):
            raise HTTPException(status_code=400, detail="Email already registered")

        new_user = await self.persistence.create_user(
            full_name=full_name,
            email=email,
            password=password,
            is_admin=False,
        )
        rbac_service = RBACService(self.db)
        await rbac_service.ensure_seed()
        await rbac_service.assign_role(new_user, STANDARD_ROLE)

        return {
            "status": "success",
            "message": "User registered successfully",
            "user": {
                "id": new_user.id,
                "full_name": new_user.full_name,
                "email": new_user.email,
                "is_admin": new_user.is_admin,
            },
        }

    async def authenticate_user(
        self, email: str, password: str, request: Request
    ) -> dict[str, object]:
        """
        المصادقة على المستخدم وإصدار رمز الدخول (JWT).

        محاولة المصادقة عبر User Service أولاً، ثم العودة للنظام المحلي.

        Args:
            email (str): البريد الإلكتروني.
            password (str): كلمة المرور.
            request (Request): كائن الطلب الحالي.

        Returns:
            dict[str, object]: رمز الدخول (Access Token) وتفاصيل المستخدم.
        """
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

        # محاولة المصادقة عبر الخدمة المصغرة
        try:
            response = await user_service_client.login_user(
                email=email, password=password, ip=ip, user_agent=user_agent
            )
            # response format: {"access_token": "...", "user": {...}, "status": "..."}
            user_data = response.get("user", {})
            is_admin = user_data.get("is_admin", False)
            landing_path = "/admin" if is_admin else "/app/chat"

            return {
                "access_token": response.get("access_token"),
                "refresh_token": response.get("refresh_token"),
                "token_type": "Bearer",
                "user": {
                    "id": user_data.get("id"),
                    "name": user_data.get("full_name"),
                    "email": user_data.get("email"),
                    "is_admin": is_admin,
                },
                "status": "success",
                "landing_path": landing_path,
            }
        except httpx.HTTPStatusError as e:
            # إذا رفضت الخدمة (كلمة مرور خطأ)، نرفع الخطأ
            # لكن مهلاً! ماذا لو كان المستخدم موجوداً محلياً فقط (لم يتم ترحيله)؟
            # إذا قالت الخدمة 401، قد يكون المستخدم غير موجود هناك أصلاً.
            # لذا يجب أن نتحقق محلياً أيضاً إذا قالت الخدمة "Invalid credentials" أو "User not found".
            logger.warning(f"User Service rejected login: {e}")
            pass  # ننتقل للخطة البديلة للتأكد
        except (httpx.RequestError, httpx.TimeoutException, Exception) as e:
            logger.error(f"User Service unreachable for login ({e}), using local fallback.")

        # ==============================================================================
        # Local Fallback (Monolith Logic with ChronoShield)
        # ==============================================================================
        # 0. تفعيل درع الدفاع الزمني
        await chrono_shield.check_allowance(request, email)

        # 1. جلب بيانات المستخدم
        user = await self.persistence.get_user_by_email(email)

        # 2. التحقق من كلمة المرور
        is_valid = False
        if user:
            try:
                is_valid = user.verify_password(password)
            except Exception as e:
                logger.error(f"Password verification error for user {user.id}: {e}")
                is_valid = False
        else:
            chrono_shield.phantom_verify(password)
            is_valid = False

        if not is_valid:
            chrono_shield.record_failure(request, email)
            logger.warning(f"Failed login attempt for {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        chrono_shield.reset_target(email)

        # 3. توليد رمز JWT
        role = "admin" if user.is_admin else "user"
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": role,
            "is_admin": user.is_admin,
            "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24),
        }

        token = jwt.encode(payload, self.settings.SECRET_KEY, algorithm="HS256")

        landing_path = "/admin" if user.is_admin else "/app/chat"
        return {
            "access_token": token,
            "token_type": "Bearer",
            "user": {
                "id": user.id,
                "name": user.full_name,
                "email": user.email,
                "is_admin": user.is_admin,
            },
            "status": "success",
            "landing_path": landing_path,
        }

    async def get_current_user(self, token: str) -> dict[str, object]:
        """
        جلب بيانات المستخدم الحالي من رمز JWT.

        يحاول التحقق عبر User Service أولاً.

        Args:
            token (str): رمز JWT الخام.

        Returns:
            dict[str, object]: تفاصيل المستخدم.
        """
        # محاولة التحقق عبر الخدمة المصغرة
        try:
            user_data = await user_service_client.get_me(token)
            return {
                "id": user_data.get("id"),
                "name": user_data.get("full_name"),
                "email": user_data.get("email"),
                "is_admin": user_data.get("is_admin", False),
            }
        except httpx.HTTPStatusError:
            # الرمز غير صالح بالنسبة للخدمة، أو المستخدم غير موجود هناك
            pass
        except (httpx.RequestError, httpx.TimeoutException, Exception) as e:
            logger.error(f"User Service unreachable for get_me ({e}), using local fallback.")

        # ==============================================================================
        # Local Fallback
        # ==============================================================================
        try:
            payload = jwt.decode(token, self.settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")
        except jwt.PyJWTError as e:
            logger.warning(f"Token decoding failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid token") from e

        user = await self.persistence.get_user_by_id(int(user_id))

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "is_admin": user.is_admin,
        }

    @staticmethod
    def extract_token_from_request(request: Request) -> str:
        """
        استخراج رمز JWT من ترويسة التفويض.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid Authorization header format")
        return parts[1]

    async def update_profile(
        self, token: str, full_name: str | None = None, email: str | None = None
    ) -> dict[str, object]:
        """Update profile via User Service."""
        try:
            return await user_service_client.update_profile(token, full_name, email)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
        except Exception as e:
            logger.error(f"Failed to update profile via service: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable") from e

    async def change_password(
        self, token: str, current_password: str, new_password: str
    ) -> dict[str, object]:
        """Change password via User Service."""
        try:
            return await user_service_client.change_password(token, current_password, new_password)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
        except Exception as e:
            logger.error(f"Failed to change password via service: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable") from e

    async def forgot_password(self, email: str) -> dict[str, object]:
        """Request password reset via User Service."""
        try:
            return await user_service_client.forgot_password(email)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
        except Exception as e:
            logger.error(f"Failed to request password reset via service: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable") from e

    async def reset_password(self, token: str, new_password: str) -> dict[str, object]:
        """Reset password via User Service."""
        try:
            return await user_service_client.reset_password(token, new_password)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
        except Exception as e:
            logger.error(f"Failed to reset password via service: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable") from e

    async def create_user_admin(
        self, token: str, full_name: str, email: str, password: str, is_admin: bool = False
    ) -> dict[str, object]:
        """Admin create user via User Service."""
        try:
            return await user_service_client.create_user_admin(
                token, full_name, email, password, is_admin
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
        except Exception as e:
            logger.error(f"Failed to create user (admin) via service: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable") from e

    async def update_user_status(self, token: str, user_id: int, status: str) -> dict[str, object]:
        """Admin update status via User Service."""
        try:
            return await user_service_client.update_user_status(token, user_id, status)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
        except Exception as e:
            logger.error(f"Failed to update status via service: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable") from e

    async def assign_role(self, token: str, user_id: int, role_name: str) -> dict[str, object]:
        """Admin assign role via User Service."""
        try:
            return await user_service_client.assign_role(token, user_id, role_name)
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text) from e
        except Exception as e:
            logger.error(f"Failed to assign role via service: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable") from e

    async def list_users(self) -> list[dict[str, object]]:
        """List all users via User Service (Admin)."""
        try:
            return await user_service_client.get_users()
        except Exception as e:
            logger.error(f"Failed to list users via service: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable") from e

    async def issue_reauth_proof(
        self, user_id: int, password: str, ip: str | None = None, user_agent: str | None = None
    ) -> tuple[str, int]:
        """Issue re-auth proof locally (Fallback)."""
        # We use local persistence to verify password for re-auth
        # This assumes shared DB.
        user = await self.persistence.get_user_by_id(user_id)
        if not user or not user.verify_password(password):
            raise HTTPException(status_code=401, detail="Re-authentication required")

        payload = {
            "sub": str(user.id),
            "purpose": "reauth",
            "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=5),
        }
        token = jwt.encode(payload, self.settings.SECRET_KEY, algorithm="HS256")
        return token, 300

    def verify_reauth_proof(self, token: str, user_id: int) -> None:
        """Verify re-auth proof locally."""
        try:
            payload = jwt.decode(token, self.settings.SECRET_KEY, algorithms=["HS256"])
            if payload.get("purpose") != "reauth" or payload.get("sub") != str(user_id):
                raise HTTPException(status_code=401, detail="Re-authentication required")
        except jwt.PyJWTError as e:
            raise HTTPException(status_code=401, detail="Re-authentication required") from e

    async def refresh_session(
        self, refresh_token: str, ip: str | None = None, user_agent: str | None = None
    ) -> dict[str, str]:
        """Refresh session locally (Fallback)."""
        # Since Microservice doesn't expose refresh endpoint yet, we use local logic.
        # This works if they share DB and Secret.
        try:
            from app.services.auth.service import AuthService

            # Create a temporary AuthService to handle complex token logic
            # This is a bit hacky but preserves logic without duplicating 100 lines of token code
            local_service = AuthService(self.db, self.settings)
            return await local_service.refresh_session(
                refresh_token=refresh_token, ip=ip, user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Local refresh failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid refresh token") from e

    async def logout(
        self, refresh_token: str, ip: str | None = None, user_agent: str | None = None
    ) -> None:
        """Logout locally."""
        try:
            from app.services.auth.service import AuthService

            local_service = AuthService(self.db, self.settings)
            await local_service.logout(refresh_token=refresh_token, ip=ip, user_agent=user_agent)
        except Exception:
            pass
