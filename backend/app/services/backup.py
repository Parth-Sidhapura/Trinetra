"""Immutable evidence backup.

Exports a signed manifest of the evidence hash chain + audit log to a
SEPARATE storage location. Manifests are named by sequence + their own hash
and are never overwritten or deleted - only appended to. If the primary
database were compromised, a verifier can compare the live chain against the
last exported manifest and see exactly where they diverge.
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.hashing import merkle_root, sha256_text
from app.models import AuditLog, Evidence, EvidenceBackupManifest
from app.services import storage

log = logging.getLogger("trinetra.backup")


def export_manifest(db: Session) -> dict:
    evidence = db.query(Evidence).order_by(Evidence.uploaded_at.asc()).all()
    audit = db.query(AuditLog).order_by(AuditLog.sequence_number.asc()).all()

    if not evidence and not audit:
        return {"skipped": "nothing to back up"}

    last = (db.query(EvidenceBackupManifest)
              .order_by(EvidenceBackupManifest.sequence_number.desc()).first())
    seq = (last.sequence_number + 1) if last else 1

    root = merkle_root([e.merkle_leaf_hash or e.sha256 for e in evidence])

    body = {
        "manifest_sequence": seq,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "merkle_root": root,
        "evidence": [
            {"id": str(e.id), "case_id": str(e.case_id),
             "filename": e.filename, "sha256": e.sha256,
             "sequence_number": e.sequence_number,
             "chain_hash": e.chain_hash,
             "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None}
            for e in evidence
        ],
        "audit_head": {
            "count": len(audit),
            "last_sequence": audit[-1].sequence_number if audit else 0,
            "last_event_hash": audit[-1].event_hash if audit else None,
        },
    }

    payload = json.dumps(body, indent=2, sort_keys=True).encode()
    manifest_hash = sha256_text(payload.decode())

    # Named by sequence + its own hash. Never overwritten.
    path = f"manifests/{seq:06d}_{manifest_hash[:16]}.json"
    uri = storage.put(settings.BACKUP_BUCKET, path, payload, "application/json")

    record = EvidenceBackupManifest(
        sequence_number=seq, manifest_hash=manifest_hash,
        merkle_root=root, storage_uri=uri, record_count=len(evidence),
    )
    db.add(record)
    db.commit()

    log.info("Exported backup manifest %s (%s evidence records)", seq, len(evidence))
    return {"manifest_sequence": seq, "manifest_hash": manifest_hash,
            "merkle_root": root, "records": len(evidence), "uri": uri}


def compare_with_live(db: Session) -> dict:
    """Does the live chain still agree with the last exported manifest?"""
    last = (db.query(EvidenceBackupManifest)
              .order_by(EvidenceBackupManifest.sequence_number.desc()).first())
    if last is None:
        return {"status": "no_manifest",
                "detail": "No backup manifest has been exported yet."}

    evidence = db.query(Evidence).order_by(Evidence.uploaded_at.asc()).all()
    live_root = merkle_root([e.merkle_leaf_hash or e.sha256 for e in evidence])

    if live_root == last.merkle_root:
        return {"status": "match", "merkle_root": live_root,
                "manifest_sequence": last.sequence_number}
    return {"status": "divergent", "live_merkle_root": live_root,
            "manifest_merkle_root": last.merkle_root,
            "manifest_sequence": last.sequence_number,
            "detail": ("Live evidence chain no longer matches the last exported "
                       "manifest. Records may have been added, or altered.")}
