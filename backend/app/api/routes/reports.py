from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, authorize_case, require_role
from app.db.session import get_db
from app.services.audit import write_audit
from app.services.reports import bsa_section63_certificate, investigation_brief

router = APIRouter(prefix="/cases/{case_id}/reports", tags=["reports"])


@router.get("/brief")
def brief(case_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    authorize_case(db, user, case_id)
    data, mime = investigation_brief(db, case_id, actor=user.email)
    write_audit(db, actor=user.email, actor_role=user.role,
                action="report.brief", case_id=case_id)
    ext = "pdf" if mime == "application/pdf" else "html"
    return Response(content=data, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="brief_{case_id[:8]}.{ext}"'})


@router.get("/bsa-certificate")
def certificate(case_id: str, user: CurrentUser, db: Session = Depends(get_db),
                _=Depends(require_role("INSPECTOR"))):
    """BSA Section 63 certificate DRAFT. Assists the prescribed certification
    process; does not itself establish legal admissibility."""
    authorize_case(db, user, case_id)
    data, mime = bsa_section63_certificate(db, case_id, actor=user.email)
    write_audit(db, actor=user.email, actor_role=user.role,
                action="report.bsa_certificate", case_id=case_id)
    ext = "pdf" if mime == "application/pdf" else "html"
    return Response(content=data, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="bsa63_draft_{case_id[:8]}.{ext}"'})
