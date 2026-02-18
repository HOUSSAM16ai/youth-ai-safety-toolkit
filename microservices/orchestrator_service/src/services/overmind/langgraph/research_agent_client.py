from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.logging import get_logger
from microservices.orchestrator_service.src.services.overmind.langgraph.context_contracts import (
    RefineResult,
    Snippet,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ResearchAgentClient:
    """
    عميل HTTP للتواصل مع خدمة Research Agent.
    """

    base_url: str
    timeout: float = 10.0

    async def search(
        self,
        *,
        query: str,
        filters: dict[str, object],
        limit: int,
        deep_dive: bool = False,
    ) -> list[Snippet]:
        """
        تنفيذ عملية بحث عبر واجهة Research Agent الموحدة.
        """
        payload = {
            "caller_id": "overmind",
            "target_service": "research_agent",
            "action": "deep_research" if deep_dive else "search",
            "payload": {"query": query, "filters": filters, "limit": limit, "deep_dive": deep_dive},
            "security_token": None,
        }
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                response = await client.post("/execute", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("فشل الاتصال بـ Research Agent: %s", exc)
            return []

        data = response.json()
        if data.get("status") != "success":
            logger.warning("Research Agent أعاد حالة غير ناجحة: %s", data.get("error"))
            return []

        raw_results = data.get("data", {}).get("results", [])
        if not isinstance(raw_results, list):
            return []

        snippets: list[Snippet] = []
        for item in raw_results[:limit]:
            if not isinstance(item, dict):
                continue
            text = _extract_text(item)
            if not text:
                continue
            metadata = _extract_metadata(item)
            snippets.append(Snippet(text=text, metadata=metadata))
        return snippets

    async def refine(self, *, query: str, api_key: str) -> RefineResult:
        """
        إرسال طلب تنقيح إلى خدمة Research Agent.
        """
        payload = {
            "caller_id": "overmind",
            "target_service": "research_agent",
            "action": "refine",
            "payload": {"query": query, "api_key": api_key},
            "security_token": None,
        }
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                response = await client.post("/execute", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("فشل تنقيح الهدف عبر Research Agent: %s", exc)
            return RefineResult(refined_objective=query, metadata={})

        data = response.json()
        if data.get("status") != "success":
            logger.warning("Research Agent لم ينجح في التنقيح: %s", data.get("error"))
            return RefineResult(refined_objective=query, metadata={})

        payload_data = data.get("data", {})
        if not isinstance(payload_data, dict):
            return RefineResult(refined_objective=query, metadata={})

        refined_query = payload_data.get("refined_query")
        refined_value = refined_query if isinstance(refined_query, str) else query
        metadata = _extract_refine_metadata(payload_data)
        return RefineResult(refined_objective=refined_value, metadata=metadata)


def _extract_text(item: dict[str, object]) -> str | None:
    """
    استخراج النص من نتيجة بحث خارجية.
    """
    snippet = item.get("snippet")
    if isinstance(snippet, str) and snippet.strip():
        return snippet
    title = item.get("title")
    if isinstance(title, str) and title.strip():
        return title
    return None


def _extract_metadata(item: dict[str, object]) -> dict[str, object]:
    """
    بناء بيانات وصفية نظيفة من نتيجة البحث.
    """
    metadata: dict[str, object] = {}
    score = item.get("score")
    if isinstance(score, (int, float)):
        metadata["score"] = score
    source = item.get("source")
    if isinstance(source, str):
        metadata["source"] = source
    title = item.get("title")
    if isinstance(title, str):
        metadata["title"] = title
    return metadata


def _extract_refine_metadata(payload: dict[str, object]) -> dict[str, object]:
    """
    استخراج بيانات وصفية من استجابة التنقيح.
    """
    metadata: dict[str, object] = {}
    for key in ("year", "subject", "branch"):
        value = payload.get(key)
        if value is not None:
            metadata[key] = value
    return metadata
