from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, authorize_case, require_role
from app.db.session import get_db
from app.models import Anomaly, Entity
from app.services.anomalies import run_all_detectors

router = APIRouter(prefix="/cases/{case_id}/anomalies", tags=["anomalies"])


@router.get("")
def list_anomalies(case_id: str, user: CurrentUser,
                   db: Session = Depends(get_db)):
    authorize_case(db, user, case_id)
    rows = (db.query(Anomaly).filter(Anomaly.case_id == case_id)
              .order_by(Anomaly.anomaly_confidence.desc()).all())
    names = {str(e.id): e.name for e in
             db.query(Entity).filter(Entity.case_id == case_id).all()}
    return [{
        "id": str(a.id), "kind": a.kind, "title": a.title,
        "description": a.description,
        "anomaly_confidence": a.anomaly_confidence,
        "source_precision": a.source_precision,
        "entities": [{"id": e, "name": names.get(e, "?")}
                     for e in (a.entity_ids or [])],
        "evidence_ids": a.evidence_ids or [],
        "window_start": a.window_start, "window_end": a.window_end,
        "details": a.details or {},
        "detector": {"name": a.detector_name, "version": a.detector_version},
        "disclaimer": "Potential pattern requiring verification — not proof.",
    } for a in rows]


@router.post("/run")
def run_detectors(case_id: str, user: CurrentUser,
                  db: Session = Depends(get_db),
                  _=Depends(require_role("INSPECTOR"))):
    authorize_case(db, user, case_id)
    return run_all_detectors(db, case_id)
