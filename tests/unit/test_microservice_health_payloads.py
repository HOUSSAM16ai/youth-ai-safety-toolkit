"""اختبارات جاهزية الخدمات المصغرة عبر باني الاستجابة."""

from microservices.memory_agent.health import build_health_payload as memory_health
from microservices.memory_agent.settings import MemoryAgentSettings
from microservices.observability_service.health import build_health_payload as observability_health
from microservices.planning_agent.health import build_health_payload as planning_health
from microservices.planning_agent.settings import PlanningAgentSettings
from microservices.user_service.health import build_health_payload as user_health
from microservices.user_service.settings import UserServiceSettings


def test_planning_agent_health_payload() -> None:
    settings = PlanningAgentSettings()
    payload = planning_health(settings)

    assert payload.service == settings.SERVICE_NAME
    assert payload.status == "ok"
    assert payload.database == settings.DATABASE_URL


def test_memory_agent_health_payload() -> None:
    settings = MemoryAgentSettings()
    payload = memory_health(settings)

    assert payload.service == settings.SERVICE_NAME
    assert payload.status == "ok"
    assert payload.database == settings.DATABASE_URL


def test_user_service_health_payload() -> None:
    settings = UserServiceSettings()
    payload = user_health(settings)

    assert payload.service == settings.SERVICE_NAME
    assert payload.status == "ok"
    assert payload.environment == settings.ENVIRONMENT


def test_observability_health_payload() -> None:
    payload = observability_health(service_name="observability-service")

    assert payload.service == "observability-service"
    assert payload.status == "ok"
    assert payload.database is None
