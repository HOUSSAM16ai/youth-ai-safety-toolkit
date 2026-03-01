"""
Orchestrator Client.
Provides a typed interface to the Orchestrator Service.
Decouples the Monolith from the Overmind Orchestration Logic.
"""

from __future__ import annotations

import json
import logging
import socket
from collections.abc import AsyncGenerator
from typing import Any, Final
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from app.core.http_client_factory import HTTPClientConfig, get_http_client
from app.core.settings.base import get_settings

logger = logging.getLogger("orchestrator-client")

DEFAULT_ORCHESTRATOR_URL: Final[str] = "http://orchestrator-service:8006"
LOCAL_ORCHESTRATOR_URL: Final[str] = "http://localhost:8006"
DOCKER_ORCHESTRATOR_HOSTS: Final[set[str]] = {"orchestrator-service", "orchestrator_service"}


def _is_host_resolvable(host: str | None) -> bool:
    """يتحقق من قابلية حل اسم المضيف ضمن بيئة التشغيل الحالية."""

    if host is None:
        return False

    try:
        socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False

    return True


def _resolve_runtime_orchestrator_url(configured_url: str) -> str:
    """يختار عنوان orchestrator القابل للوصول وفق نمط التشغيل الحالي."""

    parsed = urlparse(configured_url)
    host = parsed.hostname

    if host not in DOCKER_ORCHESTRATOR_HOSTS:
        return configured_url

    if _is_host_resolvable(host):
        return configured_url

    logger.error(
        "Runtime DNS mismatch: host '%s' is not resolvable; falling back to %s",
        host,
        LOCAL_ORCHESTRATOR_URL,
    )
    return LOCAL_ORCHESTRATOR_URL


class MissionResponse(BaseModel):
    id: int
    objective: str
    status: str
    outcome: str | None = None
    created_at: Any = None
    updated_at: Any = None
    result: dict | None = None
    steps: list = []


class OrchestratorClient:
    """
    Client for interacting with the Orchestrator Service.
    """

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        # Ensure we use the configuration from settings if available
        # Note: In docker-compose, ORCHESTRATOR_SERVICE_URL is passed to API Gateway.
        # The Monolith (Core Kernel) might not have it set in its env if not updated.
        # But we assume it should be reachable.
        env_url = getattr(settings, "ORCHESTRATOR_SERVICE_URL", None)
        configured_url = base_url or env_url or DEFAULT_ORCHESTRATOR_URL
        runtime_url = _resolve_runtime_orchestrator_url(configured_url)
        self.base_url = runtime_url.rstrip("/")
        self.config = HTTPClientConfig(
            name="orchestrator-client",
            timeout=60.0,
            max_connections=50,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        return get_http_client(self.config)

    async def create_mission(
        self,
        objective: str,
        context: dict[str, Any] | None = None,
        priority: int = 1,
        idempotency_key: str | None = None,
    ) -> MissionResponse:
        """
        Create and start a mission via the Orchestrator Service.
        """
        url = f"{self.base_url}/missions"
        payload = {
            "objective": objective,
            "context": context or {},
            "priority": priority,
        }
        headers = {}
        if idempotency_key:
            headers["X-Correlation-ID"] = idempotency_key

        client = await self._get_client()
        try:
            logger.info(f"Dispatching mission to Orchestrator: {objective[:50]}...")
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return MissionResponse(**data)
        except Exception as e:
            logger.error(f"Failed to create mission: {e}", exc_info=True)
            raise

    async def get_mission(self, mission_id: int) -> MissionResponse | None:
        """
        Get mission details.
        """
        url = f"{self.base_url}/missions/{mission_id}"
        client = await self._get_client()
        try:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return MissionResponse(**data)
        except Exception as e:
            logger.error(f"Failed to get mission {mission_id}: {e}")
            raise

    async def get_mission_events(self, mission_id: int) -> list[dict]:
        """
        Get mission events from the Orchestrator Service.
        """
        url = f"{self.base_url}/missions/{mission_id}/events"
        client = await self._get_client()
        try:
            response = await client.get(url)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get mission events {mission_id}: {e}")
            return []

    async def chat_with_agent(
        self,
        question: str,
        user_id: int,
        conversation_id: int | None = None,
        history_messages: list[dict[str, str]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict | str, None]:
        """
        Chat with the Orchestrator Agent (Microservice).
        Expects NDJSON stream from the service.
        Yields either structured event dictionaries or fallback strings.
        """
        url = f"{self.base_url}/agent/chat"
        payload = {
            "question": question,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "history_messages": history_messages or [],
            "context": context or {},
        }

        client = await self._get_client()
        try:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON line from agent: {line[:50]}...")
                        # Fallback for raw text if Microservice isn't fully migrated
                        yield {"type": "assistant_delta", "payload": {"content": line}}
        except Exception as e:
            logger.error(f"Failed to chat with agent: {e}", exc_info=True)
            yield {
                "type": "assistant_error",
                "payload": {"content": f"Error connecting to agent: {e}"},
            }


# Singleton
orchestrator_client = OrchestratorClient()
