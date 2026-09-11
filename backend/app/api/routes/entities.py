from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.crypto import redact
from app.core.security import CurrentUser, authorize_case
from app.db.session import get_db
from app.models import CriminalHistory, Entity, Observation, Relationship
from app.services.analytics import investigative_priority

router = APIRouter(prefix="/cases/{case_id}/entities", tags=["entities"])


def _serialize(entity: Entity, role: str) -> dict:
    """Redaction happens server-side BEFORE serialization. The frontend never
    receives data a role isn't cleared to see."""
    attrs = dict(entity.attributes or {})
    for field, key in (("aadhaar", "person.aadhaar"), ("phone", "person.phone"),
                       ("account", "bank.account"), ("address", "person.address")):
        if field in attrs:
            attrs[field] = redact(key, str(attrs[field]), role)
    return {"id": str(entity.id), "type": entity.type, "name": entity.name,
            "aliases": entity.aliases or [], "attributes": attrs,
            "created_at": entity.created_at}


@router.get("")
def list_entities(case_id: str, user: CurrentUser,
                  type: str | None = Query(None),
                  db: Session = Depends(get_db)):
    authorize_case(db, user, case_id)
    q = db.query(Entity).filter(Entity.case_id == case_id)
    if type:
        q = q.filter(Entity.type == type.upper())
    return [_serialize(e, user.role) for e in q.limit(500).all()]


@router.get("/{entity_id}")
def entity_detail(case_id: str, entity_id: str, request: Request,
                  user: CurrentUser, db: Session = Depends(get_db)):
    authorize_case(db, user, case_id)
    entity = db.query(Entity).filter(Entity.id == entity_id,
                                     Entity.case_id == case_id).first()
    if entity is None:
        raise HTTPException(404, "Entity not found")

    # Honeytoken check: accessing a canary is always a security event.
    from app.services.honeytokens import is_canary, trip
    if is_canary(entity):
        trip(db, entity=entity, actor=user.email, actor_role=user.role,
             ip=request.client.host if request.client else None)

    rels = db.query(Relationship).filter(
        Relationship.case_id == case_id,
        (Relationship.source_id == entity_id) | (Relationship.target_id == entity_id),
    ).all()

    names = {str(e.id): e.name for e in
             db.query(Entity).filter(Entity.case_id == case_id).all()}

    observations = db.query(Observation).filter(
        Observation.case_id == case_id,
        Observation.id.in_(entity.source_observation_ids or []),
    ).all() if entity.source_observation_ids else []

    history = db.query(CriminalHistory).filter(
        CriminalHistory.entity_id == entity_id).all()

    return {
        **_serialize(entity, user.role),
        "priority": investigative_priority(db, case_id, entity_id),
        "relationships": [
            {"id": str(r.id), "type": r.type, "status": r.status,
             "confidence": r.relationship_confidence,
             "direction": "out" if str(r.source_id) == entity_id else "in",
             "other": names.get(str(r.target_id if str(r.source_id) == entity_id
                                     else r.source_id), "?"),
             "other_id": str(r.target_id if str(r.source_id) == entity_id
                             else r.source_id),
             "occurred_at": r.occurred_at, "evidence_id": str(r.evidence_id or ""),
             "attributes": r.attributes or {}}
            for r in rels[:200]
        ],
        "observations": [
            {"id": str(o.id), "raw_text": o.raw_text, "method": o.extraction_method,
             "confidence": o.extraction_confidence, "page": o.page_number,
             "document_id": str(o.source_document_id or "")}
            for o in observations
        ],
        "criminal_history": [
            {"case_ref": h.case_ref, "offense_type": h.offense_type,
             "date": h.date} for h in history
        ],
    }


@router.get("/{entity_id}/lineage")
def lineage(case_id: str, entity_id: str, user: CurrentUser,
            db: Session = Depends(get_db)):
    """End-to-end intelligence lineage: walk any finding backwards to the
    exact page of the exact document it came from."""
    authorize_case(db, user, case_id)
    from app.models import Evidence, Provenance

    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if entity is None:
        raise HTTPException(404, "Entity not found")

    obs = db.query(Observation).filter(
        Observation.case_id == case_id,
        Observation.normalized_value == entity.name,
    ).limit(50).all()

    docs = {}
    for o in obs:
        if o.source_document_id and str(o.source_document_id) not in docs:
            ev = db.query(Evidence).filter(Evidence.id == o.source_document_id).first()
            if ev:
                docs[str(ev.id)] = {"id": str(ev.id), "filename": ev.filename,
                                    "sha256": ev.sha256,
                                    "sequence_number": ev.sequence_number}

    return {
        "entity": {"id": str(entity.id), "name": entity.name, "type": entity.type},
        "chain": [
            {"stage": "Evidence", "items": list(docs.values())},
            {"stage": "Observation",
             "items": [{"id": str(o.id), "raw_text": o.raw_text,
                        "page": o.page_number, "method": o.extraction_method,
                        "confidence": o.extraction_confidence} for o in obs]},
            {"stage": "Canonical Entity",
             "items": [{"id": str(entity.id), "name": entity.name}]},
            {"stage": "Graph Analytics",
             "items": [investigative_priority(db, case_id, entity_id)]},
        ],
    }
