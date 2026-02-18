from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.logging import get_logger
from microservices.orchestrator_service.src.services.overmind.langgraph.context_contracts import (
    RefineResult,
    Snippet,
)
from microservices.orchestrator_service.src.services.overmind.langgraph.research_agent_client import (
    ResearchAgentClient,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class NoopObjectiveRefiner:
    """
    منقح هدف افتراضي يعيد الهدف كما هو.
    """

    async def refine(self, objective: str) -> RefineResult:
        """
        يعيد الهدف كما ورد دون تعديل.
        """
        return RefineResult(refined_objective=objective, metadata={})


@dataclass(frozen=True, slots=True)
class NullSnippetRetriever:
    """
    مسترجع مقتطفات فارغ يستخدم عند غياب التكاملات الخارجية.
    """

    async def retrieve(
        self,
        query: str,
        *,
        context: dict[str, object],
        metadata: dict[str, object],
        max_snippets: int,
    ) -> list[Snippet]:
        """
        يعيد قائمة فارغة لتجنب آثار جانبية غير لازمة.
        """
        return []


@dataclass(frozen=True, slots=True)
class ResearchAgentSnippetRetriever:
    """
    مسترجع مقتطفات عبر خدمة Research Agent الخارجية.
    """

    client: ResearchAgentClient

    async def retrieve(
        self,
        query: str,
        *,
        context: dict[str, object],
        metadata: dict[str, object],
        max_snippets: int,
    ) -> list[Snippet]:
        """
        يستدعي خدمة Research Agent ويحوّل النتائج إلى مقتطفات موحّدة.
        """
        filters = _extract_metadata_filters(context, metadata)
        # Check context for deep_dive signal
        deep_dive = bool(context.get("deep_dive", False))
        # If no results found in regular search, we might want to auto-trigger deep dive?
        # For now, let's respect the flag.
        return await self.client.search(
            query=query, filters=filters, limit=max_snippets, deep_dive=deep_dive
        )


@dataclass(frozen=True, slots=True)
class ResearchAgentObjectiveRefiner:
    """
    منقح هدف يعتمد على خدمة Research Agent.
    """

    client: ResearchAgentClient
    api_key: str

    async def refine(self, objective: str) -> RefineResult:
        """
        يرسل الهدف إلى خدمة Research Agent لإعادة صياغته.
        """
        result = await self.client.refine(query=objective, api_key=self.api_key)
        return RefineResult(
            refined_objective=result.refined_query,
            metadata=result.metadata,
        )


def build_default_retriever() -> NullSnippetRetriever | ResearchAgentSnippetRetriever:
    """
    بناء المسترجع الافتراضي وفق متغيرات البيئة.
    """
    base_url = os.environ.get("RESEARCH_AGENT_URL")
    if not base_url:
        logger.info("Research Agent URL غير متوفر، سيتم تعطيل الاسترجاع الخارجي.")
        return NullSnippetRetriever()
    return ResearchAgentSnippetRetriever(
        client=ResearchAgentClient(base_url=base_url),
    )


def build_default_refiner() -> NoopObjectiveRefiner | ResearchAgentObjectiveRefiner:
    """
    بناء المنقح الافتراضي وفق متغيرات البيئة.
    """
    base_url = os.environ.get("RESEARCH_AGENT_URL")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not base_url or not api_key:
        logger.info("تعذر تفعيل تنقيح الهدف عبر Research Agent.")
        return NoopObjectiveRefiner()
    return ResearchAgentObjectiveRefiner(
        client=ResearchAgentClient(base_url=base_url),
        api_key=api_key,
    )


def _extract_metadata_filters(
    context: dict[str, object], metadata: dict[str, object]
) -> dict[str, object]:
    """
    استخراج مرشحات البحث من السياق المشترك إن وجدت.
    """
    candidate = context.get("metadata_filters")
    if isinstance(candidate, dict):
        return candidate
    return metadata
