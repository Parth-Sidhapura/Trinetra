from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, authorize_case, require_role
from app.db.session import get_db
from app.models import Case, Entity, Evidence, FIR, Relationship
from app.services.audit import write_audit

router = APIRouter(prefix="/cases", tags=["cases"])


class CaseIn(BaseModel):
    title: str
    bnss_stage: str = "fir_registered"
    data_classification: str = "confidential"
    department: str = "CYBER_CELL"


class FIRIn(BaseModel):
    fir_number: str
    police_station: str = ""
    bns_sections: list[str] = []
    complainant_ref: str = ""


@router.get("")
def list_cases(user: CurrentUser, db: Session = Depends(get_db)):
    """Case isolation: a user only ever sees cases they're authorized on."""
    q = db.query(Case)
    if user.role != "ADMIN":
        q = q.filter(Case.department == user.department)
    out = []
    for case in q.order_by(Case.created_at.desc()).all():
        if not user.cleared_for(case.data_classification):
            continue
        out.append({
            "id": str(case.id), "title": case.title, "status": case.status,
            "bnss_stage": case.bnss_stage,
            "data_classification": case.data_classification,
            "created_at": case.created_at,
            "counts": {
                "evidence": db.query(Evidence).filter(Evidence.case_id == case.id).count(),
                "entities": db.query(Entity).filter(Entity.case_id == case.id).count(),
                "relationships": db.query(Relationship).filter(
                    Relationship.case_id == case.id).count(),
            },
        })
    return out


@router.post("", status_code=201)
def create_case(body: CaseIn, user: CurrentUser, db: Session = Depends(get_db),
                _=Depends(require_role("INSPECTOR"))):
    """Opening a case is a write action - CONSTABLE is read-only."""
    case = Case(title=body.title, bnss_stage=body.bnss_stage,
                data_classification=body.data_classification,
                department=body.department or user.department)
    db.add(case)
    db.commit()
    db.refresh(case)
    write_audit(db, actor=user.email, actor_role=user.role,
                action="case.create", resource=f"case:{case.id}",
                case_id=str(case.id))
    return {"id": str(case.id), "title": case.title}


@router.get("/{case_id}")
def get_case(case_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    case = authorize_case(db, user, case_id)
    firs = db.query(FIR).filter(FIR.case_id == case_id).all()
    return {
        "id": str(case.id), "title": case.title, "status": case.status,
        "bnss_stage": case.bnss_stage,
        "data_classification": case.data_classification,
        "department": case.department, "created_at": case.created_at,
        "firs": [{"id": str(f.id), "fir_number": f.fir_number,
                  "police_station": f.police_station,
                  "bns_sections": f.bns_sections or []} for f in firs],
    }


@router.post("/{case_id}/firs", status_code=201)
def add_fir(case_id: str, body: FIRIn, user: CurrentUser,
            db: Session = Depends(get_db),
            _=Depends(require_role("INSPECTOR"))):
    authorize_case(db, user, case_id)
    fir = FIR(case_id=case_id, fir_number=body.fir_number,
              police_station=body.police_station,
              bns_sections=body.bns_sections,
              complainant_ref=body.complainant_ref)
    db.add(fir)
    db.commit()
    write_audit(db, actor=user.email, actor_role=user.role,
                action="fir.create", resource=f"fir:{fir.id}", case_id=case_id)
    return {"id": str(fir.id)}
