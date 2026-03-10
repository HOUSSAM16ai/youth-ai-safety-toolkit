from app.core.settings.base import AppSettings


def test_default_service_url_resolution_codespaces() -> None:
    # Codespaces maps to localhost ports
    assert (
        AppSettings._resolve_service_url("USER_SERVICE_URL", is_codespaces=True)
        == "http://localhost:8003"
    )
    assert (
        AppSettings._resolve_service_url("PLANNING_AGENT_URL", is_codespaces=True)
        == "http://localhost:8001"
    )
    assert (
        AppSettings._resolve_service_url("RESEARCH_AGENT_URL", is_codespaces=True)
        == "http://localhost:8007"
    )
    assert (
        AppSettings._resolve_service_url("REASONING_AGENT_URL", is_codespaces=True)
        == "http://localhost:8008"
    )


def test_default_service_url_resolution_docker() -> None:
    # Docker maps to service names and internal port 8000
    assert (
        AppSettings._resolve_service_url("USER_SERVICE_URL", is_codespaces=False)
        == "http://user-service:8000"
    )
    assert (
        AppSettings._resolve_service_url("PLANNING_AGENT_URL", is_codespaces=False)
        == "http://planning-agent:8000"
    )
    assert (
        AppSettings._resolve_service_url("RESEARCH_AGENT_URL", is_codespaces=False)
        == "http://research-agent:8007"
    )
    assert (
        AppSettings._resolve_service_url("REASONING_AGENT_URL", is_codespaces=False)
        == "http://reasoning-agent:8008"
    )


def test_unknown_service_url_fallback() -> None:
    # Unknown services default to localhost:8000
    assert (
        AppSettings._resolve_service_url("UNKNOWN_URL", is_codespaces=True)
        == "http://localhost:8000"
    )
