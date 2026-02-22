"""
Tests for Auth Boundary Service Migration (Shadow Mode).
Verifies that the service correctly delegates to User Service and falls back to Local Persistence.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.services.boundaries.auth_boundary_service import AuthBoundaryService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def service(mock_db):
    return AuthBoundaryService(mock_db)


@pytest.mark.asyncio
async def test_register_user_success_remote(service):
    """
    Test successful registration via User Service.
    Should return remote user data and NOT call local persistence.
    """
    # Mock User Service Client
    with patch("app.services.boundaries.auth_boundary_service.user_service_client") as mock_client:
        mock_client.register_user = AsyncMock(
            return_value={
                "user": {
                    "id": 100,
                    "full_name": "Remote User",
                    "email": "remote@test.com",
                    "is_admin": False,
                },
                "message": "Remote success",
            }
        )

        # Mock Local Persistence (should NOT be called)
        service.persistence.user_exists = AsyncMock()
        service.persistence.create_user = AsyncMock()

        result = await service.register_user("Remote User", "remote@test.com", "password")

        assert result["status"] == "success"
        assert result["user"]["email"] == "remote@test.com"
        assert result["user"]["id"] == 100

        # Verify calls
        mock_client.register_user.assert_called_once_with(
            "Remote User", "remote@test.com", "password"
        )
        service.persistence.user_exists.assert_not_called()
        service.persistence.create_user.assert_not_called()


@pytest.mark.asyncio
async def test_register_user_failure_network_fallback(service):
    """
    Test network failure during registration.
    Should catch exception and FALLBACK to local persistence.
    """
    with patch("app.services.boundaries.auth_boundary_service.user_service_client") as mock_client:
        # Simulate Network Error
        mock_client.register_user.side_effect = httpx.RequestError("Connection failed")

        # Mock Local Persistence (SHOULD be called)
        service.persistence.user_exists = AsyncMock(return_value=False)
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.full_name = "Local User"
        mock_user.email = "local@test.com"
        mock_user.is_admin = False
        service.persistence.create_user = AsyncMock(return_value=mock_user)

        # Mock RBAC
        with patch("app.services.boundaries.auth_boundary_service.RBACService") as mock_rbac_class:
            mock_rbac = mock_rbac_class.return_value
            mock_rbac.ensure_seed = AsyncMock()
            mock_rbac.assign_role = AsyncMock()

            result = await service.register_user("Local User", "local@test.com", "password")

            assert result["status"] == "success"
            assert result["user"]["email"] == "local@test.com"
            assert result["user"]["id"] == 1  # Local ID

            # Verify calls
            mock_client.register_user.assert_called_once()
            service.persistence.user_exists.assert_called_once_with("local@test.com")
            service.persistence.create_user.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_failure_logical_400(service):
    """
    Test logical failure (400 Bad Request) from User Service.
    Should RAISE exception and NOT fallback.
    """
    with patch("app.services.boundaries.auth_boundary_service.user_service_client") as mock_client:
        # Simulate 400 Error (e.g. Email exists remote)
        response = httpx.Response(400, json={"detail": "Email already registered"})
        mock_client.register_user.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=None, response=response
        )

        # Mock Local Persistence (should NOT be called)
        service.persistence.user_exists = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await service.register_user("User", "exists@test.com", "password")

        assert exc.value.status_code == 400
        service.persistence.user_exists.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_user_success_remote(service):
    """
    Test successful login via User Service.
    """
    with patch("app.services.boundaries.auth_boundary_service.user_service_client") as mock_client:
        mock_client.login_user = AsyncMock(
            return_value={
                "access_token": "remote_token",
                "token_type": "Bearer",
                "user": {
                    "id": 200,
                    "full_name": "Remote Login",
                    "email": "login@test.com",
                    "is_admin": False,
                },
                "status": "success",
            }
        )

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "TestAgent"

        service.persistence.get_user_by_email = AsyncMock()

        result = await service.authenticate_user("login@test.com", "password", mock_request)

        assert result["access_token"] == "remote_token"
        assert result["user"]["id"] == 200

        mock_client.login_user.assert_called_once()
        service.persistence.get_user_by_email.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_user_fallback_on_401(service):
    """
    Test fallback behavior when User Service returns 401 (or connection error).
    Ideally, we try local just in case user is not migrated.
    """
    with patch("app.services.boundaries.auth_boundary_service.user_service_client") as mock_client:
        # Simulate 401 from Remote (e.g. User not found remote)
        response = httpx.Response(401, json={"detail": "Invalid credentials"})
        mock_client.login_user.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=None, response=response
        )

        # Mock Local Persistence (SHOULD be called for fallback)
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.email = "local_only@test.com"
        mock_user.is_admin = False
        mock_user.verify_password.return_value = True

        service.persistence.get_user_by_email = AsyncMock(return_value=mock_user)

        # Mock ChronoShield
        with patch("app.services.boundaries.auth_boundary_service.chrono_shield") as mock_shield:
            mock_shield.check_allowance = AsyncMock()
            mock_shield.reset_target = MagicMock()

            # Mock JWT
            with patch("app.services.boundaries.auth_boundary_service.jwt") as mock_jwt:
                mock_jwt.encode.return_value = "local_token"

                # Mock Settings
                service.settings = MagicMock()
                service.settings.SECRET_KEY = "secret"

                mock_request = MagicMock()

                result = await service.authenticate_user(
                    "local_only@test.com", "password", mock_request
                )

                assert result["access_token"] == "local_token"
                assert result["user"]["id"] == 2

                mock_client.login_user.assert_called_once()
                service.persistence.get_user_by_email.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_user_success_remote(service):
    """
    Test successful get_current_user via User Service.
    """
    with patch("app.services.boundaries.auth_boundary_service.user_service_client") as mock_client:
        mock_client.get_me = AsyncMock(
            return_value={
                "id": 300,
                "full_name": "Remote Me",
                "email": "me@test.com",
                "is_admin": True,
            }
        )

        service.persistence.get_user_by_id = AsyncMock()

        result = await service.get_current_user("valid_remote_token")

        assert result["email"] == "me@test.com"
        assert result["id"] == 300

        mock_client.get_me.assert_called_once_with("valid_remote_token")
        service.persistence.get_user_by_id.assert_not_called()
