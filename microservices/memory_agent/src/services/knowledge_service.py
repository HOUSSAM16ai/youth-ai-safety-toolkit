"""
خدمة المعرفة (Knowledge Service).
================================

تدير العمليات المتعلقة بالرسم البياني للمفاهيم.
"""

from microservices.memory_agent.src.domain.concept_graph import (
    Concept,
    ConceptGraph,
    get_concept_graph,
)


class KnowledgeService:
    """خدمة المعرفة."""

    def __init__(self) -> None:
        self.graph: ConceptGraph = get_concept_graph()

    async def get_concept(self, concept_id: str) -> Concept | None:
        """يحصل على مفهوم بواسطة معرفه."""
        return self.graph.concepts.get(concept_id)

    async def get_prerequisites(self, concept_id: str) -> list[Concept]:
        """يحصل على المتطلبات السابقة."""
        return self.graph.get_prerequisites(concept_id)

    async def get_related_concepts(self, concept_id: str) -> list[Concept]:
        """يحصل على المفاهيم المرتبطة."""
        return self.graph.get_related_concepts(concept_id)

    async def get_next_concepts(self, concept_id: str) -> list[Concept]:
        """يحصل على المفاهيم التالية."""
        return self.graph.get_next_concepts(concept_id)

    async def find_concept_by_topic(self, topic: str) -> Concept | None:
        """يبحث عن مفهوم."""
        return self.graph.find_concept_by_topic(topic)

    async def get_learning_path(self, from_concept: str, to_concept: str) -> list[Concept]:
        """يجد مسار تعلم."""
        return self.graph.get_learning_path(from_concept, to_concept)

    async def visualize(self) -> str:
        """يولّد تمثيلاً نصياً للرسم البياني."""
        return self.graph.visualize()
