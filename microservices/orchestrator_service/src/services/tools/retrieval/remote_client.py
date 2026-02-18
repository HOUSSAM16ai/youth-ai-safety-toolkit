"""
Remote Memory Agent Client (Legacy/Unified Adapter).
Infrastructure Layer.
"""

import os

import httpx

from microservices.orchestrator_service.src.core.logging import get_logger

logger = get_logger("tool-retrieval-remote")


def _parse_tags_to_filters(tags: list[str]) -> dict[str, object]:
    """Convert legacy tags list to Research Agent filters dict."""
    filters = {}
    for tag in tags:
        if ":" in tag:
            key, val = tag.split(":", 1)
            val = val.strip()
            if not val:
                continue

            if key in {"year", "subject", "branch", "level", "type", "lang"}:
                if key == "year" and val.isdigit():
                    filters[key] = int(val)
                else:
                    filters[key] = val
            elif key == "exam_ref":
                filters["set_name"] = val
    return filters


async def fetch_from_memory_agent(query: str, tags: list[str]) -> list[dict[str, object]]:
    """
    Fetches content from the Research Agent microservice.
    Returns a list of result dictionaries or raises an exception/returns empty on failure.
    """
    # Use RESEARCH_AGENT_URL as primary, fallback to MEMORY_AGENT_URL for backward compat
    base_url = (
        os.getenv("RESEARCH_AGENT_URL")
        or os.getenv("MEMORY_AGENT_URL")
        or "http://research-agent:8000"
    )

    # Unified Protocol Endpoint
    url = f"{base_url}/execute"

    logger.info(f"Searching content with query='{query}' and tags={tags}")

    filters = _parse_tags_to_filters(tags)

    payload = {
        "caller_id": "overmind-tool-legacy-client",
        "target_service": "research_agent",
        "action": "search",
        "payload": {"query": query, "filters": filters, "limit": 5},
        "security_token": None,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "success":
                logger.warning(f"Research Agent returned error: {data.get('error')}")
                return []

            results = data.get("data", {}).get("results", [])
            if not isinstance(results, list):
                return []

            # Map back to expected format if needed
            # The tool expects "content" and metadata.
            # ResearchAgent results now include "content" (thanks to my previous fix).
            # And metadata is flatter.

            mapped_results = []
            for item in results:
                mapped_results.append(
                    {
                        "content": item.get("content", ""),
                        "metadata": item,  # Pass full item as metadata
                        "payload": item,  # Legacy field support
                    }
                )

            return mapped_results

    except Exception as e:
        logger.error(f"Failed to fetch from remote agent: {e}")
        # Return empty list to trigger local fallback in the caller
        return []
