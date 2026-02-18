"""
Research Agent Client.
Provides a typed interface to the Research Agent Service.
"""

from __future__ import annotations

from typing import Final

import httpx

from microservices.orchestrator_service.src.core.http_client_factory import HTTPClientConfig, get_http_client
from microservices.orchestrator_service.src.core.logging import get_logger
from microservices.orchestrator_service.src.core.settings import get_settings

logger = get_logger("research-client")

DEFAULT_RESEARCH_AGENT_URL: Final[str] = "http://research-agent:8000"


class ResearchClient:
    """
    Client for interacting with the Research Agent microservice.
    Uses the "Contract-First" approach (Three-Plane Architecture).
    """

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        resolved_url = base_url or settings.RESEARCH_AGENT_URL or DEFAULT_RESEARCH_AGENT_URL
        self.base_url = resolved_url.rstrip("/")
        self.config = HTTPClientConfig(
            name="research-agent-client",
            timeout=60.0,  # Research can be heavy
            max_connections=50,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        return get_http_client(self.config)

    async def deep_research(self, query: str) -> str:
        """
        Execute deep research using the agent's execute endpoint.
        """
        url = f"{self.base_url}/execute"
        payload = {
            "caller_id": "orchestrator-backend",
            "action": "deep_research",
            "payload": {"query": query},
        }

        client = await self._get_client()
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                raise ValueError(f"Research agent error: {data.get('error')}")

            results = data.get("data", {}).get("results", [])
            if not results:
                return "No research results found."

            # Return the content of the first result (usually the report)
            return results[0].get("content", "")

        except Exception as e:
            logger.error(f"Deep research failed: {e}", exc_info=True)
            raise

    async def get_curriculum_structure(self, level: str | None = None) -> dict[str, object]:
        """Fetch curriculum structure."""
        url = f"{self.base_url}/content/curriculum"
        params = {"level": level} if level else {}

        client = await self._get_client()
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get curriculum: {e}", exc_info=True)
            return {}

    async def get_content_raw(
        self, content_id: str, include_solution: bool = False
    ) -> dict[str, str] | None:
        """Fetch raw content."""
        url = f"{self.base_url}/content/{content_id}"
        params = {"include_solution": str(include_solution).lower()}

        client = await self._get_client()
        try:
            response = await client.get(url, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get content raw: {e}", exc_info=True)
            return None

    async def semantic_search(
        self, query: str, top_k: int = 5, filters: dict[str, object] | None = None
    ) -> list[dict[str, object]]:
        """
        Execute semantic search via the agent's execute endpoint.
        """
        url = f"{self.base_url}/execute"
        payload = {
            "caller_id": "orchestrator-backend",
            "action": "search",
            "payload": {
                "query": query,
                "limit": top_k,
                "filters": filters or {},
            },
        }

        client = await self._get_client()
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                raise ValueError(f"Research agent error: {data.get('error')}")

            # Extract 'results' list from the data object
            return data.get("data", {}).get("results", [])

        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            raise

    async def refine_query(self, query: str, api_key: str | None = None) -> dict[str, object]:
        """
        Refine a query using the agent's logic.
        """
        url = f"{self.base_url}/execute"
        payload = {
            "caller_id": "orchestrator-backend",
            "action": "refine",
            "payload": {"query": query, "api_key": api_key},
        }

        client = await self._get_client()
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                raise ValueError(f"Refinement error: {data.get('error')}")

            return data.get("data", {})

        except Exception as e:
            logger.error(f"Query refinement failed: {e}", exc_info=True)
            raise

    async def rerank_results(
        self, query: str, documents: list[str] | list[dict], top_n: int = 5
    ) -> list[object]:
        """
        Rerank documents using the agent's reranker.
        """
        url = f"{self.base_url}/execute"
        payload = {
            "caller_id": "orchestrator-backend",
            "action": "rerank",
            "payload": {
                "query": query,
                "documents": documents,
                "top_n": top_n,
            },
        }

        client = await self._get_client()
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                raise ValueError(f"Reranking error: {data.get('error')}")

            return data.get("data", [])

        except Exception as e:
            logger.error(f"Reranking failed: {e}", exc_info=True)
            raise

    async def check_health(self) -> bool:
        """Check if the service is healthy."""
        url = f"{self.base_url}/health"
        client = await self._get_client()
        try:
            response = await client.get(url)
            return response.status_code == 200
        except Exception:
            return False


# Singleton
research_client = ResearchClient()
