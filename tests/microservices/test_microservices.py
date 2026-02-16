"""
اختبارات مواصفات الخدمات المصغرة.

تتحقق من أن كل خدمة مستقلة تقدم واجهاتها الأساسية
وفق مبدأ "خدمة واحدة، وظيفة واحدة".
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from microservices.memory_agent.main import create_app as create_memory_app
from microservices.planning_agent.main import create_app as create_planning_app
from microservices.user_service.main import create_app as create_user_app

# نستخدم نفس المفتاح الافتراضي المحدد في الإعدادات للاختبار
TEST_SECRET_KEY = "super_secret_key_change_in_production"


def get_auth_headers() -> dict[str, str]:
    """توليد ترويسة مصادقة صالحة للخدمات."""
    payload = {
        "sub": "api-gateway",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")
    return {"X-Service-Token": token}


def test_planning_agent_generates_plan_with_context() -> None:
    """يتحقق من أن وكيل التخطيط يولد خطوات تشمل السياق عند توفره."""

    client = TestClient(create_planning_app())
    response = client.post(
        "/plans",
        json={
            "goal": "بناء خطة تعلم الذكاء الاصطناعي",
            "context": ["مستوى مبتدئ", "مدة 4 أسابيع"],
        },
        headers=get_auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["goal"] == "بناء خطة تعلم الذكاء الاصطناعي"
    assert any("تضمين السياق" in step for step in payload["steps"])


def test_memory_agent_stores_and_searches_entries() -> None:
    """يضمن أن وكيل الذاكرة يحفظ العناصر ويعيدها عبر البحث."""

    client = TestClient(create_memory_app())
    headers = get_auth_headers()

    create_response = client.post(
        "/memories",
        json={"content": "معلومة مهمة عن الحوسبة", "tags": ["حاسوب", "نواة"]},
        headers=headers,
    )

    assert create_response.status_code == 200
    entry_id = create_response.json()["entry_id"]

    search_response = client.get("/memories/search", params={"query": "نواة"}, headers=headers)
    assert search_response.status_code == 200
    results = search_response.json()

    assert any(entry["entry_id"] == entry_id for entry in results)


def test_user_service_creates_and_lists_users() -> None:
    """يتأكد من أن خدمة المستخدمين تنشئ المستخدمين وتعرضهم."""

    client = TestClient(create_user_app())
    headers = get_auth_headers()

    create_response = client.post(
        "/users",
        json={"name": "Amina", "email": "amina@example.com"},
        headers=headers,
    )

    assert create_response.status_code == 200

    list_response = client.get("/users", headers=headers)
    assert list_response.status_code == 200
    payload = list_response.json()

    assert any(user["email"] == "amina@example.com" for user in payload)


def test_user_service_rejects_invalid_email() -> None:
    """يتأكد من أن خدمة المستخدمين ترفض البريد الإلكتروني غير الصالح."""

    client = TestClient(create_user_app())
    headers = get_auth_headers()

    response = client.post(
        "/users",
        json={"name": "Noura", "email": "invalid-email"},
        headers=headers,
    )

    assert response.status_code == 422
