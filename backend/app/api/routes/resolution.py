from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, authorize_case, require_role
from app.db.session import get_db
from app.models import Entity, Observation, ResolutionCandidate
from app.services.audit import write_audit
from app.services.ingestion import emit_outbox

router = APIRouter(prefix="/cases/{case_id}/resolution", tags=["resolution"])


class Decision(BaseModel):
    decision: str          # "confirm" | "reject"


@router.get("/candidates")
def list_candidates(case_id: str, user: CurrentUser,
                    status: str = "pending", db: Session = Depends(get_db)):
    """The review queue. Nothing here is merged until a human says so."""
    authorize_case(db, user, case_id)
    rows = (db.query(ResolutionCandidate)
              .filter(ResolutionCandidate.case_id == case_id,
                      ResolutionCandidate.status == status)
              .order_by(ResolutionCandidate.resolution_confidence.desc())
              .limit(200).all())

    obs_ids = {c.entity_a_observation_id for c in rows} | \
              {c.entity_b_observation_id for c in rows}
    obs = {str(o.id): o for o in db.query(Observation)
           .filter(Observation.id.in_(obs_ids)).all()} if obs_ids else {}

    def side(oid):
        o = obs.get(str(oid))
        if o is None:
            return None
        return {"observation_id": str(o.id), "raw_text": o.raw_text,
                "normalized_value": o.normalized_value,
                "entity_type": o.entity_type,
                "extraction_method": o.extraction_method,
                "extraction_confidence": o.extraction_confidence,
                "page": o.page_number, "row": o.row_number,
                "document_id": str(o.source_document_id or "")}

    return [{"id": str(c.id),
             "a": side(c.entity_a_observation_id),
             "b": side(c.entity_b_observation_id),
             "resolution_confidence": c.resolution_confidence,
             "method": c.method, "reasoning": c.reasoning,
             "status": c.status} for c in rows]


@router.post("/candidates/{candidate_id}")
def decide(case_id: str, candidate_id: str, body: Decision, user: CurrentUser,
           db: Session = Depends(get_db),
           _=Depends(require_role("INSPECTOR"))):
    """Human-in-the-loop. Confirming creates/merges the canonical entity and
    emits an outbox event; Postgres commits both in the same transaction."""
    authorize_case(db, user, case_id)
    cand = db.query(ResolutionCandidate).filter(
        ResolutionCandidate.id == candidate_id,
        ResolutionCandidate.case_id == case_id).first()
    if cand is None:
        raise HTTPException(404, "Candidate not found")
    if body.decision not in ("confirm", "reject"):
        raise HTTPException(400, "decision must be 'confirm' or 'reject'")

    cand.status = "confirmed" if body.decision == "confirm" else "rejected"
    cand.reviewed_by = user.email
    cand.reviewed_at = datetime.now(timezone.utc)

    created_entity = None
    if body.decision == "confirm":
        a = db.query(Observation).filter(
            Observation.id == cand.entity_a_observation_id).first()
        b = db.query(Observation).filter(
            Observation.id == cand.entity_b_observation_id).first()
        if a and b:
            primary = a.normalized_value or a.raw_text
            alias = b.normalized_value or b.raw_text

            entity = (db.query(Entity)
                        .filter(Entity.case_id == case_id,
                                Entity.type == a.entity_type,
                                Entity.name == primary).first())
            if entity is None:
                entity = Entity(case_id=case_id, type=a.entity_type,
                                name=primary, aliases=[],
                                source_observation_ids=[])
                db.add(entity)
                db.flush()

            aliases = set(entity.aliases or [])
            if alias and alias != primary:
                aliases.add(alias)
            entity.aliases = sorted(aliases)
            entity.source_observation_ids = sorted(
                set(entity.source_observation_ids or []) | {str(a.id), str(b.id)})

            emit_outbox(db, aggregate_type="entity", aggregate_id=str(entity.id),
                        event_type="entity.merged", case_id=case_id,
                        payload={"name": entity.name,
                                 "aliases": entity.aliases})
            created_entity = str(entity.id)

    db.commit()
    write_audit(db, actor=user.email, actor_role=user.role,
                action=f"resolution.{body.decision}",
                resource=f"candidate:{candidate_id}", case_id=case_id,
                detail={"method": cand.method,
                        "confidence": cand.resolution_confidence})
    return {"id": str(cand.id), "status": cand.status,
            "entity_id": created_entity}
