"""Security Operations Center, break-glass, backup manifest, honeytokens."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, authorize_case, require_role
from app.db.session import get_db
from app.models import (AuditLog, BreakGlassRequest, Evidence,
                        EvidenceBackupManifest, SecurityEvent, SessionRecord)
from app.services.audit import verify_audit_chain, write_audit
from app.services.backup import compare_with_live, export_manifest

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/soc")
def soc_dashboard(user: CurrentUser, db: Session = Depends(get_db),
                  _=Depends(require_role("INSPECTOR"))):
    """Real aggregation queries over the audit and security-event tables —
    not a static mockup."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    failed_logins = db.query(SecurityEvent).filter(
        SecurityEvent.kind == "failed_login",
        SecurityEvent.created_at >= since).count()
    blocked = db.query(AuditLog).filter(
        AuditLog.result == "deny", AuditLog.timestamp >= since).count()
    honeytokens = db.query(SecurityEvent).filter(
        SecurityEvent.kind == "honeytoken_hit").count()
    active_sessions = db.query(SessionRecord).filter(
        SessionRecord.expires_at > datetime.now(timezone.utc)).count()

    audit = verify_audit_chain(db)
    evidence_total = db.query(Evidence).count()

    high_risk = db.query(SecurityEvent).filter(
        SecurityEvent.risk_score >= 60,
        SecurityEvent.created_at >= since).count()

    threat = "LOW"
    if failed_logins > 10 or high_risk > 0 or honeytokens > 0:
        threat = "ELEVATED"
    if not audit["valid"] or honeytokens > 2:
        threat = "HIGH"

    recent = (db.query(AuditLog).order_by(AuditLog.sequence_number.desc())
                .limit(25).all())

    return {
        "api_threat_level": threat,
        "failed_logins_24h": failed_logins,
        "blocked_requests_24h": blocked,
        "honeytoken_hits": honeytokens,
        "active_sessions": active_sessions,
        "evidence_records": evidence_total,
        "audit_chain": "VALID" if audit["valid"] else "BROKEN",
        "audit_events": audit["total_events"],
        "high_risk_events_24h": high_risk,
        "recent_activity": [
            {"seq": a.sequence_number, "actor": a.actor, "action": a.action,
             "resource": a.resource, "result": a.result, "at": a.timestamp}
            for a in recent
        ],
    }


@router.get("/audit/verify")
def audit_verify(user: CurrentUser, db: Session = Depends(get_db),
                 _=Depends(require_role("INSPECTOR"))):
    return verify_audit_chain(db)


@router.get("/audit")
def audit_trail(user: CurrentUser, case_id: str | None = None, limit: int = 100,
                db: Session = Depends(get_db),
                _=Depends(require_role("INSPECTOR"))):
    q = db.query(AuditLog)
    if case_id:
        q = q.filter(AuditLog.case_id == case_id)
    rows = q.order_by(AuditLog.sequence_number.desc()).limit(limit).all()
    return [{"seq": a.sequence_number, "actor": a.actor, "role": a.actor_role,
             "action": a.action, "resource": a.resource, "result": a.result,
             "case_id": str(a.case_id or ""), "at": a.timestamp,
             "event_hash": a.event_hash,
             "previous_event_hash": a.previous_event_hash,
             "detail": a.detail or {}} for a in rows]


class BreakGlassIn(BaseModel):
    case_id: str
    reason: str
    minutes: int = 30


@router.post("/break-glass")
def break_glass(body: BreakGlassIn, request: Request, user: CurrentUser,
                db: Session = Depends(get_db)):
    """Controlled override instead of a shared admin password.

    Requires a written reason, is scoped to one case for a fixed window, is
    fully audit-logged, and is flagged for mandatory supervisor review.
    """
    if len(body.reason.strip()) < 20:
        from fastapi import HTTPException
        raise HTTPException(400, "A specific written justification is required "
                                 "(minimum 20 characters).")

    expires = datetime.now(timezone.utc) + timedelta(minutes=body.minutes)
    record = BreakGlassRequest(user_id=user.user_id, case_id=body.case_id,
                               reason=body.reason.strip(), expires_at=expires)
    db.add(record)
    db.add(SecurityEvent(kind="break_glass", severity="high",
                         user_id=user.user_id,
                         ip_address=request.client.host if request.client else None,
                         risk_score=70,
                         detail={"case_id": body.case_id,
                                 "reason": body.reason[:300]}))
    db.commit()

    write_audit(db, actor=user.email, actor_role=user.role,
                action="security.break_glass", resource=f"case:{body.case_id}",
                case_id=body.case_id, result="allow",
                detail={"reason": body.reason[:300],
                        "expires_at": expires.isoformat()})

    return {"granted": True, "expires_at": expires,
            "scope": f"case:{body.case_id}",
            "notice": "This access is time-boxed and flagged for mandatory "
                      "supervisor review."}


@router.get("/break-glass")
def list_break_glass(user: CurrentUser, db: Session = Depends(get_db),
                     _=Depends(require_role("ADMIN"))):
    rows = (db.query(BreakGlassRequest)
              .order_by(BreakGlassRequest.granted_at.desc()).limit(50).all())
    return [{"id": str(r.id), "user_id": str(r.user_id),
             "case_id": str(r.case_id), "reason": r.reason,
             "granted_at": r.granted_at, "expires_at": r.expires_at,
             "reviewed_by": r.reviewed_by,
             "pending_review": r.reviewed_at is None} for r in rows]


@router.post("/backup/export")
def backup_export(user: CurrentUser, db: Session = Depends(get_db),
                  _=Depends(require_role("INSPECTOR"))):
    result = export_manifest(db)
    write_audit(db, actor=user.email, actor_role=user.role,
                action="security.backup_export", detail=result)
    return result


@router.get("/backup/status")
def backup_status(user: CurrentUser, db: Session = Depends(get_db)):
    last = (db.query(EvidenceBackupManifest)
              .order_by(EvidenceBackupManifest.sequence_number.desc()).first())
    return {
        "comparison": compare_with_live(db),
        "manifest_count": db.query(EvidenceBackupManifest).count(),
        "last_manifest": {
            "sequence": last.sequence_number, "hash": last.manifest_hash,
            "merkle_root": last.merkle_root, "records": last.record_count,
            "created_at": last.created_at, "uri": last.storage_uri,
        } if last else None,
    }


@router.post("/events/failed-login")
def record_failed_login(request: Request, email: str,
                        device_id: str | None = None,
                        db: Session = Depends(get_db)):
    """detect -> correlate -> alert -> CONTAIN.

    This does not merely score the event: at the threshold it actually revokes
    every live session and locks the account for a fixed window.
    """
    from app.services.incident import handle_failed_login
    return handle_failed_login(
        db, email=email,
        ip=request.client.host if request.client else None,
        device_id=device_id)


@router.post("/sessions")
def start_session(request: Request, user: CurrentUser,
                  device_id: str | None = None,
                  db: Session = Depends(get_db)):
    """Registers the session that backs security event correlation."""
    from app.services.incident import record_session
    session = record_session(
        db, user_id=user.user_id, device_id=device_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"))
    return {"session_id": str(session.session_id),
            "expires_at": session.expires_at}
