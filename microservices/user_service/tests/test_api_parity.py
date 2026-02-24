import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.user_service.src.services.auth.service import AuthService


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, session: AsyncSession):
    # Setup
    service = AuthService(session)
    user = await service.register_user(
        full_name="Test User",
        email="test@example.com",
        password="password123",
    )
    # Ensure seed roles exist so issue_tokens works
    await service.rbac.ensure_seed()

    tokens = await service.issue_tokens(user)
    refresh_token = tokens["refresh_token"]

    # Act
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token  # New token issued


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, session: AsyncSession):
    # Setup
    service = AuthService(session)
    user = await service.register_user(
        full_name="Logout User",
        email="logout@example.com",
        password="password123",
    )
    await service.rbac.ensure_seed()

    tokens = await service.issue_tokens(user)
    refresh_token = tokens["refresh_token"]

    # Act
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "logged_out"

    # Verify token is invalid
    from fastapi import HTTPException

    try:
        await service.refresh_session(refresh_token=refresh_token)
        pytest.fail("Should raise Unauthorized")
    except HTTPException as e:
        assert e.status_code == 401


@pytest.mark.asyncio
async def test_reauth(client: AsyncClient, session: AsyncSession):
    # Setup
    service = AuthService(session)
    user = await service.register_user(
        full_name="Reauth User",
        email="reauth@example.com",
        password="password123",
    )
    await service.rbac.ensure_seed()

    tokens = await service.issue_tokens(user)
    access_token = tokens["access_token"]

    # Act
    response = await client.post(
        "/api/v1/auth/reauth",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"password": "password123"},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "reauth_token" in data
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_admin_audit(client: AsyncClient, session: AsyncSession, admin_token: str):
    # Setup - Create some audit logs
    service = AuthService(session)
    # Registering creates audit logs
    await service.register_user(
        full_name="Audit Subject",
        email="subject@example.com",
        password="password123",
    )

    # Act
    response = await client.get(
        "/api/v1/admin/audit?limit=10&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "action" in data[0]
