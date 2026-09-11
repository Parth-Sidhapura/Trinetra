"""Background tasks. Everything slow or CPU-heavy runs here, never inline."""
import logging

from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

log = logging.getLogger("trinetra.tasks")


def _session():
    return SessionLocal()


@celery_app.task(name="trinetra.process_evidence")
def process_evidence_task(evidence_id: str, use_llm: bool = True):
    from app.services.ingestion import process_evidence
    db = _session()
    try:
        return process_evidence(db, evidence_id, use_llm=use_llm)
    finally:
        db.close()


@celery_app.task(name="trinetra.build_candidates")
def build_candidates_task(case_id: str, use_semantic: bool = False):
    from app.services.resolution import build_candidates
    db = _session()
    try:
        created = build_candidates(db, case_id, use_semantic=use_semantic)
        return {"candidates": len(created)}
    finally:
        db.close()


@celery_app.task(name="trinetra.drain_outbox")
def drain_outbox_task():
    from app.services.graph_sync import drain_outbox
    db = _session()
    try:
        return drain_outbox(db)
    finally:
        db.close()


@celery_app.task(name="trinetra.run_analytics")
def run_analytics_task(case_id: str):
    from app.services.analytics import refresh_case_analytics
    db = _session()
    try:
        return refresh_case_analytics(db, case_id)
    finally:
        db.close()


@celery_app.task(name="trinetra.detect_anomalies")
def detect_anomalies_task(case_id: str):
    from app.services.anomalies import run_all_detectors
    db = _session()
    try:
        return run_all_detectors(db, case_id)
    finally:
        db.close()


@celery_app.task(name="trinetra.export_backup_manifest")
def export_backup_manifest_task():
    from app.services.backup import export_manifest
    db = _session()
    try:
        return export_manifest(db)
    finally:
        db.close()
