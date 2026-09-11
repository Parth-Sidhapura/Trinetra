"""Tamper-evident audit log. Same hash-chain pattern as evidence."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.hashing import sha256_text, GENESIS
from app.models import AuditLog


def write_audit(db: Session, *, actor: str, actor_role: str, action: str,
                resource: str = "", case_id: str | None = None,
                result: str = "allow", detail: dict | None = None,
                trace_id: str | None = None) -> AuditLog:
    last = db.query(AuditLog).order_by(AuditLog.sequence_number.desc()).first()
    seq = (last.sequence_number + 1) if last else 1
    prev_hash = last.event_hash if last else GENESIS

    body = f"{prev_hash}|{seq}|{actor}|{action}|{resource}|{case_id}|{result}"
    event_hash = sha256_text(body)

    entry = AuditLog(
        sequence_number=seq, actor=actor, actor_role=actor_role, action=action,
        resource=resource, case_id=case_id, result=result,
        detail=detail or {}, trace_id=trace_id,
        previous_event_hash=prev_hash, event_hash=event_hash,
    )
    db.add(entry)
    db.commit()
    return entry


def verify_audit_chain(db: Session) -> dict:
    """Walk the chain and confirm nothing was altered."""
    rows = db.query(AuditLog).order_by(AuditLog.sequence_number.asc()).all()
    prev_hash = GENESIS
    for row in rows:
        body = (f"{prev_hash}|{row.sequence_number}|{row.actor}|{row.action}|"
                f"{row.resource}|{row.case_id}|{row.result}")
        if sha256_text(body) != row.event_hash:
            return {"valid": False, "broken_at": row.sequence_number,
                    "total_events": len(rows)}
        prev_hash = row.event_hash
    return {"valid": True, "broken_at": None, "total_events": len(rows)}
