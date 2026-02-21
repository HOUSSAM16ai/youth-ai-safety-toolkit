"""
اختبارات التكامل بين الخدمات المصغرة (Microservices Integration Tests).

يختبر هذا الملف التكامل الكامل بين:
- Planning Agent
- Memory Agent
- User Service
- API Gateway
- Event Bus
"""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.event_bus_impl import Event, EventBus


def get_auth_headers() -> dict[str, str]:
    """توليد ترويسة مصادقة صالحة للخدمات."""
    # Fetch SECRET_KEY dynamically to ensure it picks up the value set by conftest.py
    secret_key = os.environ.get("SECRET_KEY", "super_secret_key_change_in_production")
    payload = {
        "sub": "api-gateway",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return {"X-Service-Token": token}


@pytest.fixture
def event_bus() -> EventBus:
    """ينشئ مثيل ناقل أحداث للاختبار."""
    return EventBus()


@pytest.fixture
def planning_app() -> FastAPI:
    """ينشئ تطبيق Planning Agent للاختبار."""
    from microservices.planning_agent.main import create_app as create_planning_app

    return create_planning_app()


@pytest.fixture
def memory_app() -> FastAPI:
    """ينشئ تطبيق Memory Agent للاختبار."""
    from microservices.memory_agent.main import create_app as create_memory_app

    return create_memory_app()


@pytest.fixture
def user_app() -> FastAPI:
    """ينشئ تطبيق User Service للاختبار."""
    from microservices.user_service.main import create_app as create_user_app

    return create_user_app()


def _build_client(app: FastAPI) -> AsyncClient:
    """يبني عميل HTTP مربوطاً بتطبيق ASGI للاختبارات."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestMicroservicesHealth:
    """اختبارات صحة الخدمات المصغرة."""

    @pytest.mark.asyncio
    async def test_planning_agent_health(self, planning_app: FastAPI) -> None:
        """يختبر صحة Planning Agent."""
        async with _build_client(planning_app) as client:
            response = await client.get("/health", headers=get_auth_headers())
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "planning-agent"
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_memory_agent_health(self, memory_app: FastAPI) -> None:
        """يختبر صحة Memory Agent."""
        async with _build_client(memory_app) as client:
            response = await client.get("/health", headers=get_auth_headers())
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "memory-agent"
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_user_service_health(self, user_app: FastAPI) -> None:
        """يختبر صحة User Service."""
        async with _build_client(user_app) as client:
            response = await client.get("/health", headers=get_auth_headers())
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "user-service"
            assert data["status"] == "ok"


class TestPlanningAgentAPI:
    """اختبارات API لـ Planning Agent."""

    @pytest.mark.asyncio
    async def test_create_plan(self, planning_app: FastAPI) -> None:
        """يختبر إنشاء خطة."""
        async with _build_client(planning_app) as client:
            response = await client.post(
                "/plans",
                json={
                    "goal": "تعلم البرمجة",
                    "context": ["مبتدئ", "Python"],
                },
                headers=get_auth_headers(),
            )
            assert response.status_code == 200
            data = response.json()
            assert "plan_id" in data
            assert data["goal"] == "تعلم البرمجة"
            assert len(data["steps"]) > 0

    @pytest.mark.asyncio
    async def test_list_plans(self, planning_app: FastAPI) -> None:
        """يختبر عرض الخطط."""
        async with _build_client(planning_app) as client:
            headers = get_auth_headers()
            # إنشاء خطة أولاً
            await client.post(
                "/plans",
                json={"goal": "تعلم Python", "context": []},
                headers=headers,
            )

            # عرض الخطط
            response = await client.get("/plans", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0


class TestMemoryAgentAPI:
    """اختبارات API لـ Memory Agent."""

    @pytest.mark.asyncio
    async def test_create_memory(self, memory_app: FastAPI) -> None:
        """يختبر إنشاء ذاكرة."""
        async with _build_client(memory_app) as client:
            response = await client.post(
                "/memories",
                json={
                    "content": "تعلمت اليوم عن FastAPI",
                    "tags": ["learning", "fastapi"],
                },
                headers=get_auth_headers(),
            )
            assert response.status_code == 200
            data = response.json()
            assert "entry_id" in data
            assert data["content"] == "تعلمت اليوم عن FastAPI"
            assert "learning" in data["tags"]

    @pytest.mark.asyncio
    async def test_search_memories(self, memory_app: FastAPI) -> None:
        """يختبر البحث في الذاكرة."""
        async with _build_client(memory_app) as client:
            headers = get_auth_headers()
            # إنشاء ذاكرة أولاً
            await client.post(
                "/memories",
                json={
                    "content": "FastAPI is awesome",
                    "tags": ["fastapi"],
                },
                headers=headers,
            )

            # البحث
            response = await client.get("/memories/search?query=fastapi", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0


class TestUserServiceAPI:
    """اختبارات API لـ User Service."""

    @pytest.mark.asyncio
    async def test_create_user(self, user_app: FastAPI) -> None:
        """يختبر إنشاء مستخدم."""
        async with _build_client(user_app) as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "أحمد محمد",
                    "email": "ahmed@example.com",
                    "password": "StrongPassword123!",
                },
                headers=get_auth_headers(),
            )
            assert response.status_code == 200
            data = response.json()
            assert "user" in data
            assert data["user"]["name"] == "أحمد محمد"
            assert data["user"]["email"] == "ahmed@example.com"

    @pytest.mark.asyncio
    async def test_login_and_me(self, user_app: FastAPI) -> None:
        """يختبر تسجيل الدخول وعرض الملف الشخصي."""
        async with _build_client(user_app) as client:
            headers = get_auth_headers()
            # إنشاء مستخدم أولاً
            await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "فاطمة علي",
                    "email": "fatima@example.com",
                    "password": "StrongPassword123!",
                },
                headers=headers,
            )

            # تسجيل الدخول
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "fatima@example.com",
                    "password": "StrongPassword123!",
                },
                headers=headers,
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # عرض الملف الشخصي
            # نحتاج لإضافة Bearer Token بالإضافة لـ Service Token (لأن الراوتر محمي بـ Service Token)
            # لكن الراوتر get_me يحتاج user context من Bearer
            auth_headers = headers.copy()
            auth_headers["Authorization"] = f"Bearer {token}"

            response = await client.get("/api/v1/auth/user/me", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "fatima@example.com"


class TestEventBusIntegration:
    """اختبارات تكامل ناقل الأحداث."""

    @pytest.mark.asyncio
    async def test_event_flow_between_services(self, event_bus: EventBus) -> None:
        """يختبر تدفق الأحداث بين الخدمات."""
        received_events = []

        # محاكاة اشتراك خدمة المستخدمين
        @event_bus.subscribe("user.created")
        async def on_user_created(event: Event) -> None:
            received_events.append(("user-service", event))

        # محاكاة اشتراك خدمة الذاكرة
        @event_bus.subscribe("user.created")
        async def on_user_created_memory(event: Event) -> None:
            received_events.append(("memory-agent", event))

        # نشر حدث
        await event_bus.publish(
            event_type="user.created",
            payload={"user_id": "123", "email": "test@example.com"},
            source="user-service",
        )

        # التحقق من استلام الحدث
        assert len(received_events) == 2
        assert received_events[0][0] == "user-service"
        assert received_events[1][0] == "memory-agent"

    @pytest.mark.asyncio
    async def test_plan_created_event(self, event_bus: EventBus) -> None:
        """يختبر حدث إنشاء خطة."""
        plan_events = []

        @event_bus.subscribe("plan.created")
        async def on_plan_created(event: Event) -> None:
            plan_events.append(event)

        await event_bus.publish(
            event_type="plan.created",
            payload={"plan_id": "456", "goal": "تعلم Python"},
            source="planning-agent",
        )

        assert len(plan_events) == 1
        assert plan_events[0].payload["goal"] == "تعلم Python"


class TestEndToEndScenarios:
    """اختبارات السيناريوهات الشاملة."""

    @pytest.mark.asyncio
    async def test_complete_learning_flow(
        self,
        user_app: FastAPI,
        planning_app: FastAPI,
        memory_app: FastAPI,
        event_bus: EventBus,
    ) -> None:
        """
        يختبر سيناريو تعليمي كامل:
        1. إنشاء مستخدم
        2. إنشاء خطة تعليمية
        3. حفظ التقدم في الذاكرة
        """
        # 1. إنشاء مستخدم
        async with _build_client(user_app) as client:
            user_response = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "محمد أحمد",
                    "email": "mohamed@example.com",
                    "password": "StrongPassword123!",
                },
                headers=get_auth_headers(),
            )
            assert user_response.status_code == 200
            user_data = user_response.json()
            user_id = user_data["user"]["id"]

        # 2. إنشاء خطة تعليمية
        async with _build_client(planning_app) as client:
            plan_response = await client.post(
                "/plans",
                json={
                    "goal": "إتقان FastAPI",
                    "context": ["متوسط", "Python"],
                },
                headers=get_auth_headers(),
            )
            assert plan_response.status_code == 200
            plan_data = plan_response.json()
            plan_id = plan_data["plan_id"]

        # 3. حفظ التقدم في الذاكرة
        async with _build_client(memory_app) as client:
            memory_response = await client.post(
                "/memories",
                json={
                    "content": f"المستخدم {user_id} بدأ الخطة {plan_id}",
                    "tags": ["progress", "learning"],
                },
                headers=get_auth_headers(),
            )
            assert memory_response.status_code == 200

        # 4. نشر حدث التقدم
        await event_bus.publish(
            event_type="learning.progress",
            payload={
                "user_id": str(user_id),
                "plan_id": str(plan_id),
                "status": "started",
            },
            source="orchestrator",
        )

        # التحقق من السجل
        history = event_bus.get_history(event_type="learning.progress")
        assert len(history) > 0
