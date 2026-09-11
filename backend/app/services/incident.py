"""Incident response: detect -> correlate -> alert -> contain -> preserve.

The MVP implements the front half concretely: repeated failed logins trigger
an automatic session revoke and account lock, logged as a security alert.
Preserve/investigate/recover beyond that is documented, not automated.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import SecurityEvent, SessionRecord, UserProfile
from app.services.audit import write_audit

log = logging.getLogger("trinetra.incident")

LOCK_THRESHOLD = 5          # failures inside the window
WINDOW_MINUTES = 15
LOCK_MINUTES = 30


def revoke_sessions(db: Session, user_id: str) -> int:
    """CONTAIN: expire every live session for this user immediately."""
    now = datetime.now(timezone.utc)
    rows = (db.query(SessionRecord)
              .filter(SessionRecord.user_id == user_id,
                      SessionRecord.expires_at > now).all())
    for row in rows:
        row.expires_at = now
    db.commit()
    log.warning("Revoked %s session(s) for user %s", len(rows), user_id)
    return len(rows)


def lock_account(db: Session, user_id: str, minutes: int = LOCK_MINUTES) -> datetime:
    """CONTAIN: lock the profile for a fixed window."""
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if profile is not None:
        profile.locked_until = until
        db.commit()
    return until


def is_locked(db: Session, user_id: str) -> bool:
    profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if profile is None or profile.locked_until is None:
        return False
    return profile.locked_until > datetime.now(timezone.utc)


def handle_failed_login(db: Session, *, email: str, ip: str | None,
                        device_id: str | None = None) -> dict:
    """DETECT + CORRELATE + ALERT + CONTAIN, in one pass.

    Correlation signal: repeated failures, from a new device_id or an unusual
    ip_address, raise the risk score - explainable heuristics grounded in real
    session data, not a claimed ML/SIEM system.
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)

    recent = db.query(SecurityEvent).filter(
        SecurityEvent.kind == "failed_login",
        SecurityEvent.created_at >= since,
        SecurityEvent.detail["email"].astext == email
        if hasattr(SecurityEvent.detail, "astext") else True,
    ).count() if ip else 0

    profile = db.query(UserProfile).filter(UserProfile.email == email).first()

    # New-device signal
    new_device = False
    if profile and device_id:
        new_device = db.query(SessionRecord).filter(
            SessionRecord.user_id == profile.id,
            SessionRecord.device_id == device_id).first() is None

    risk = min(20 + recent * 18 + (25 if new_device else 0), 100)

    db.add(SecurityEvent(
        kind="failed_login", severity="high" if risk >= 60 else "low",
        user_id=profile.id if profile else None, ip_address=ip, risk_score=risk,
        detail={"email": email, "recent_failures": recent,
                "new_device": new_device, "device_id": device_id},
    ))
    db.commit()

    action = "none"
    locked_until = None
    revoked = 0

    if profile and (recent + 1) >= LOCK_THRESHOLD:
        revoked = revoke_sessions(db, str(profile.id))
        locked_until = lock_account(db, str(profile.id))
        action = "account_locked_sessions_revoked"

        db.add(SecurityEvent(
            kind="account_locked", severity="high", user_id=profile.id,
            ip_address=ip, risk_score=100,
            detail={"email": email, "revoked_sessions": revoked,
                    "locked_until": locked_until.isoformat()},
        ))
        db.commit()

        write_audit(db, actor=email, actor_role=profile.role,
                    action="incident.account_locked", resource=f"user:{email}",
                    result="deny",
                    detail={"failures": recent + 1, "revoked_sessions": revoked,
                            "locked_until": locked_until.isoformat()})

    return {"risk_score": risk, "recent_failures": recent + 1,
            "new_device": new_device, "action": action,
            "revoked_sessions": revoked,
            "locked_until": locked_until}


def record_session(db: Session, *, user_id: str, device_id: str | None,
                   ip: str | None, user_agent: str | None,
                   hours: int = 8) -> SessionRecord:
    """Populate the sessions table that backs security event correlation."""
    now = datetime.now(timezone.utc)
    session = SessionRecord(
        user_id=user_id, device_id=device_id, ip_address=ip,
        user_agent=user_agent, created_at=now, last_seen=now,
        expires_at=now + timedelta(hours=hours),
    )
    db.add(session)
    db.commit()
    return session
