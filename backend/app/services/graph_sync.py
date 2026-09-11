"""Postgres -> Neo4j projection via the transactional outbox.

Neo4j is NEVER written directly by a request handler. A worker replays
outbox_events idempotently, keyed on aggregate_id + aggregate_version, so a
retry or an out-of-order delivery can never duplicate an edge.
"""
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Entity, OutboxEvent, Relationship

log = logging.getLogger("trinetra.graph_sync")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_lifetime=180,
        )
    return _driver


def ping_neo4j() -> bool:
    """Also keeps AuraDB Free awake - it auto-pauses after 72h idle."""
    with get_driver().session() as session:
        session.run("RETURN 1").consume()
    return True


MERGE_NODE = """
MERGE (n:Entity {entity_id: $entity_id})
SET n.name = $name, n.type = $type, n.case_id = $case_id,
    n.aliases = $aliases, n.graph_version = $graph_version
RETURN n.entity_id AS id
"""

MERGE_REL = """
MATCH (a:Entity {entity_id: $source_id})
MATCH (b:Entity {entity_id: $target_id})
MERGE (a)-[r:REL {relationship_id: $relationship_id}]->(b)
SET r.type = $type,
    r.status = $status,
    r.confidence = $confidence,
    r.confidence_type = 'relationship',
    r.provenance_id = $provenance_id,
    r.evidence_id = $evidence_id,
    r.occurred_at = $occurred_at,
    r.occurred_from = $occurred_from,
    r.occurred_to = $occurred_to,
    r.observed_at = $observed_at,
    r.graph_version = $graph_version,
    r.case_id = $case_id
RETURN r.relationship_id AS id
"""


def _iso(value):
    return value.isoformat() if value else None


def sync_entity(entity: Entity, graph_version: int) -> None:
    with get_driver().session() as session:
        session.run(MERGE_NODE, entity_id=str(entity.id), name=entity.name,
                    type=entity.type, case_id=str(entity.case_id),
                    aliases=list(entity.aliases or []),
                    graph_version=graph_version).consume()


def sync_relationship(rel: Relationship, graph_version: int) -> None:
    """The projection carries full provenance - not just confidence+evidence_id
    - so any edge traces straight back to its authoritative Postgres record."""
    with get_driver().session() as session:
        session.run(
            MERGE_REL,
            relationship_id=str(rel.id),
            source_id=str(rel.source_id), target_id=str(rel.target_id),
            type=rel.type, status=rel.status,
            confidence=rel.relationship_confidence,
            provenance_id=str(rel.provenance_id) if rel.provenance_id else None,
            evidence_id=str(rel.evidence_id) if rel.evidence_id else None,
            occurred_at=_iso(rel.occurred_at),
            occurred_from=_iso(rel.occurred_from),
            occurred_to=_iso(rel.occurred_to),
            observed_at=_iso(rel.observed_at),
            graph_version=graph_version, case_id=str(rel.case_id),
        ).consume()


def drain_outbox(db: Session, limit: int = 200) -> dict:
    """Poll pending events, apply to Neo4j, mark processed only on success."""
    if not (settings.NEO4J_ENABLED and settings.NEO4J_URI):
        return {"skipped": "neo4j disabled", "processed": 0}

    events = (db.query(OutboxEvent)
                .filter(OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at.asc())
                .limit(limit).all())

    processed = failed = 0
    for event in events:
        try:
            if event.aggregate_type == "entity":
                entity = db.query(Entity).filter(
                    Entity.id == event.aggregate_id).first()
                if entity:
                    sync_entity(entity, event.aggregate_version)
            elif event.aggregate_type == "relationship":
                rel = db.query(Relationship).filter(
                    Relationship.id == event.aggregate_id).first()
                if rel:
                    # ensure both endpoints exist first
                    for eid in (rel.source_id, rel.target_id):
                        ent = db.query(Entity).filter(Entity.id == eid).first()
                        if ent:
                            sync_entity(ent, event.aggregate_version)
                    sync_relationship(rel, event.aggregate_version)

            event.status = "processed"
            from datetime import datetime, timezone
            event.processed_at = datetime.now(timezone.utc)
            processed += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("Outbox event %s failed: %s", event.id, exc)
            event.retry_count += 1
            event.last_error = str(exc)[:500]
            if event.retry_count >= 5:
                event.status = "failed"
            failed += 1
        db.commit()

    return {"processed": processed, "failed": failed, "scanned": len(events)}


def backfill_case(db: Session, case_id: str) -> dict:
    """Push an entire case into Neo4j - useful after a fresh deploy."""
    from app.models import CaseGraphState
    state = db.query(CaseGraphState).filter(
        CaseGraphState.case_id == case_id).first()
    version = state.graph_version if state else 1

    entities = db.query(Entity).filter(Entity.case_id == case_id).all()
    rels = db.query(Relationship).filter(
        Relationship.case_id == case_id,
        Relationship.status.in_(["source_observed", "human_confirmed", "inferred"]),
    ).all()

    for entity in entities:
        sync_entity(entity, version)
    for rel in rels:
        sync_relationship(rel, version)

    return {"entities": len(entities), "relationships": len(rels),
            "graph_version": version}
