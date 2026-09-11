from fastapi import (APIRouter, BackgroundTasks, Depends, File, HTTPException,
                     UploadFile, status)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import CurrentUser, authorize_case, require_role
from app.db.session import SessionLocal, get_db
from app.models import Evidence
from app.services import ingestion
from app.services.audit import write_audit
from app.services.quarantine import QuarantineError

router = APIRouter(prefix="/cases/{case_id}/evidence", tags=["evidence"])


def _process_in_background(evidence_id: str):
    """Used when Celery isn't available - keeps the request non-blocking."""
    db = SessionLocal()
    try:
        ingestion.process_evidence(db, evidence_id)
        from app.services.resolution import build_candidates
        ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if ev:
            build_candidates(db, str(ev.case_id))
    finally:
        db.close()


@router.post("", status_code=201)
async def upload(case_id: str, user: CurrentUser, background: BackgroundTasks,
                 file: UploadFile = File(...), db: Session = Depends(get_db),
                 _=Depends(require_role("INSPECTOR"))):
    authorize_case(db, user, case_id)
    data = await file.read()

    try:
        evidence = ingestion.store_evidence(
            db, case_id=case_id, filename=file.filename or "upload.bin",
            data=data, uploaded_by=user.email,
            content_type=file.content_type or "")
    except QuarantineError as exc:
        write_audit(db, actor=user.email, actor_role=user.role,
                    action="evidence.rejected", resource=file.filename or "",
                    case_id=case_id, result="deny", detail={"reason": str(exc)})
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    write_audit(db, actor=user.email, actor_role=user.role,
                action="evidence.upload", resource=f"evidence:{evidence.id}",
                case_id=case_id, detail={"sha256": evidence.sha256,
                                         "filename": evidence.filename})

    if settings.CELERY_ENABLED:
        try:
            from app.workers.tasks import build_candidates_task, process_evidence_task
            process_evidence_task.delay(str(evidence.id))
            build_candidates_task.apply_async(args=[case_id], countdown=25)
        except Exception:  # noqa: BLE001 - broker down, fall back inline
            background.add_task(_process_in_background, str(evidence.id))
    else:
        background.add_task(_process_in_background, str(evidence.id))

    return {"id": str(evidence.id), "filename": evidence.filename,
            "sha256": evidence.sha256, "sequence_number": evidence.sequence_number,
            "chain_hash": evidence.chain_hash,
            "scan_result": evidence.scan_result,
            "processing_status": evidence.processing_status}


@router.get("")
def list_evidence(case_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    authorize_case(db, user, case_id)
    rows = (db.query(Evidence).filter(Evidence.case_id == case_id)
              .order_by(Evidence.sequence_number).all())
    return [{"id": str(e.id), "filename": e.filename,
             "sequence_number": e.sequence_number, "sha256": e.sha256,
             "chain_hash": e.chain_hash, "size_bytes": e.size_bytes,
             "scan_result": e.scan_result,
             "processing_status": e.processing_status,
             "uploaded_at": e.uploaded_at, "uploaded_by": e.uploaded_by}
            for e in rows]


@router.get("/verify")
def verify_integrity(case_id: str, user: CurrentUser,
                     db: Session = Depends(get_db)):
    """Recomputes the whole chain + Merkle root, and checks the audit chain
    and the last immutable backup manifest."""
    authorize_case(db, user, case_id)
    from app.services.audit import verify_audit_chain
    from app.services.backup import compare_with_live

    chain = ingestion.verify_chain(db, case_id)
    audit = verify_audit_chain(db)
    backup = compare_with_live(db)

    write_audit(db, actor=user.email, actor_role=user.role,
                action="evidence.verify", case_id=case_id,
                detail={"chain_valid": chain["chain_valid"]})

    return {
        "evidence_chain": chain,
        "audit_chain": audit,
        "backup_manifest": backup,
        "overall": ("VALID" if chain["chain_valid"] and audit["valid"]
                    else "TAMPERING DETECTED"),
    }
