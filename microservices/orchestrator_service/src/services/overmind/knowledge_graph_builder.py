from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text

from app.core.logging import get_logger
from microservices.orchestrator_service.src.core.database import async_session_factory

logger = get_logger(__name__)

RELATION_BIDS_ON = "bids_on"
RELATION_AWARDED_TO = "awarded_to"
RELATION_OWNED_BY = "owned_by"
RELATION_PARTNER_OF = "partner_of"


@dataclass(frozen=True, slots=True)
class ProcurementEntity:
    """
    تمثيل كيان مشتريات لبناء الرسم البياني المعرفي.
    """

    entity_type: str
    entity_id: str
    name: str
    metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class ProcurementRelation:
    """
    تمثيل علاقة مشتريات بين كيانين.
    """

    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relation: str
    properties: dict[str, object]


@dataclass(frozen=True, slots=True)
class GraphNode:
    """
    عقدة معرفة جاهزة للحفظ داخل مخزن المعرفة.
    """

    node_id: uuid.UUID
    label: str
    name: str
    content: str | None
    metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """
    ضلع علاقة بين عقدتين داخل الرسم البياني.
    """

    edge_id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    relation: str
    properties: dict[str, object]


@dataclass(frozen=True, slots=True)
class GraphBuildResult:
    """
    نتيجة بناء الرسم البياني للمعرفة في سياق المشتريات.
    """

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    node_index: dict[tuple[str, str], uuid.UUID]


@dataclass(frozen=True, slots=True)
class FraudSignal:
    """
    مؤشر احتيال مشتق من تحليل الرسم البياني.
    """

    signal: str
    vendor_id: str
    company_id: str
    tender_id: str
    reason: str
    severity: float


def build_procurement_graph(
    *,
    entities: list[ProcurementEntity],
    relations: list[ProcurementRelation],
    namespace: uuid.UUID = uuid.NAMESPACE_URL,
) -> GraphBuildResult:
    """
    بناء عقد وأضلاع المعرفة لعلاقات المشتريات.
    """
    node_index: dict[tuple[str, str], uuid.UUID] = {}
    nodes: list[GraphNode] = []

    for entity in entities:
        key = (entity.entity_type, entity.entity_id)
        if key in node_index:
            continue
        node_id = _stable_node_id(namespace, entity.entity_type, entity.entity_id)
        node_index[key] = node_id
        nodes.append(
            GraphNode(
                node_id=node_id,
                label=entity.entity_type,
                name=entity.name,
                content=None,
                metadata=entity.metadata,
            )
        )

    edges: list[GraphEdge] = []
    for relation in relations:
        source_key = (relation.source_type, relation.source_id)
        target_key = (relation.target_type, relation.target_id)
        source_id = node_index.get(source_key)
        target_id = node_index.get(target_key)
        if source_id is None or target_id is None:
            continue
        edge_id = _stable_edge_id(
            namespace,
            relation.relation,
            relation.source_type,
            relation.source_id,
            relation.target_type,
            relation.target_id,
        )
        edges.append(
            GraphEdge(
                edge_id=edge_id,
                source_id=source_id,
                target_id=target_id,
                relation=relation.relation,
                properties=relation.properties,
            )
        )

    return GraphBuildResult(nodes=nodes, edges=edges, node_index=node_index)


def detect_triangular_fraud_signals(
    relations: list[ProcurementRelation],
) -> list[FraudSignal]:
    """
    اكتشاف مؤشرات احتيال مثل ارتباط المورد بشركة فائزة على نفس المناقصة.
    """
    vendor_to_tenders: dict[str, set[str]] = {}
    company_to_tenders: dict[str, set[str]] = {}
    vendor_to_companies: dict[str, set[str]] = {}

    for relation in relations:
        if relation.relation == RELATION_BIDS_ON:
            vendor_to_tenders.setdefault(relation.source_id, set()).add(relation.target_id)
        elif relation.relation == RELATION_AWARDED_TO:
            company_to_tenders.setdefault(relation.target_id, set()).add(relation.source_id)
        elif relation.relation in {RELATION_OWNED_BY, RELATION_PARTNER_OF}:
            vendor_to_companies.setdefault(relation.source_id, set()).add(relation.target_id)

    signals: list[FraudSignal] = []
    for vendor_id, companies in vendor_to_companies.items():
        tenders = vendor_to_tenders.get(vendor_id, set())
        if not tenders:
            continue
        for company_id in companies:
            awarded = company_to_tenders.get(company_id, set())
            for tender_id in tenders.intersection(awarded):
                signals.append(
                    FraudSignal(
                        signal="vendor_company_award_overlap",
                        vendor_id=vendor_id,
                        company_id=company_id,
                        tender_id=tender_id,
                        reason="المورد مرتبط بشركة فائزة على نفس المناقصة.",
                        severity=0.82,
                    )
                )
    return signals


async def persist_graph(result: GraphBuildResult) -> None:
    """
    حفظ الرسم البياني داخل قاعدة المعرفة باستخدام عمليات إدراج آمنة.
    """
    if not result.nodes and not result.edges:
        return

    async with async_session_factory() as session:
        async with session.begin():
            for node in result.nodes:
                await session.execute(
                    text(
                        """
                        INSERT INTO knowledge_nodes (id, label, name, content, metadata)
                        VALUES (:id, :label, :name, :content, :metadata)
                        ON CONFLICT (id)
                        DO UPDATE SET
                            label = EXCLUDED.label,
                            name = EXCLUDED.name,
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata
                        """
                    ),
                    {
                        "id": str(node.node_id),
                        "label": node.label,
                        "name": node.name,
                        "content": node.content,
                        "metadata": node.metadata,
                    },
                )

            for edge in result.edges:
                await session.execute(
                    text(
                        """
                        INSERT INTO knowledge_edges (id, source_id, target_id, relation, properties)
                        VALUES (:id, :source_id, :target_id, :relation, :properties)
                        ON CONFLICT (id)
                        DO UPDATE SET
                            source_id = EXCLUDED.source_id,
                            target_id = EXCLUDED.target_id,
                            relation = EXCLUDED.relation,
                            properties = EXCLUDED.properties
                        """
                    ),
                    {
                        "id": str(edge.edge_id),
                        "source_id": str(edge.source_id),
                        "target_id": str(edge.target_id),
                        "relation": edge.relation,
                        "properties": edge.properties,
                    },
                )

    logger.info(
        "Knowledge graph persisted with %s nodes and %s edges.",
        len(result.nodes),
        len(result.edges),
    )


def _stable_node_id(namespace: uuid.UUID, entity_type: str, entity_id: str) -> uuid.UUID:
    """
    بناء معرف ثابت لعقدة المشتريات.
    """
    return uuid.uuid5(namespace, f"{entity_type}:{entity_id}")


def _stable_edge_id(
    namespace: uuid.UUID,
    relation: str,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
) -> uuid.UUID:
    """
    بناء معرف ثابت للضلع داخل الرسم البياني.
    """
    key = f"{relation}:{source_type}:{source_id}->{target_type}:{target_id}"
    return uuid.uuid5(namespace, key)
