"""The pipeline: upload -> quarantine -> hash -> store -> parse -> extract
-> observations -> relationships -> outbox event.

Everything commits in ONE Postgres transaction, including the outbox row.
Postgres is truth; Neo4j catches up afterwards.
"""
import logging
from datetime import datetime, timezone

from dateutil import parser as dateparser
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.hashing import chain_hash, sha256_bytes, merkle_root
from app.models import (
    Evidence, Observation, Provenance, Relationship, Entity,
    OutboxEvent, CaseGraphState, CriminalHistory,
)
from app.services import extractors, parsers, quarantine, storage

log = logging.getLogger("trinetra.ingestion")

# Reproducibility: every AI-derived result records exactly which algorithm
# and version produced it, so a questioned match can be traced later.
EXTRACTOR_VERSION = "1.0"
EXTRACTOR_ALGORITHMS = {
    "regex": "india_format_regex",
    "spacy": "spacy_en_core_web_sm",
    "llm": "llm_zero_shot_extraction",
}


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return dateparser.parse(str(value))
    except (ValueError, TypeError, OverflowError):
        return None


def _pick(row: dict, *names: str) -> str | None:
    lowered = {k.lower().strip(): v for k, v in row.items()}
    for n in names:
        v = lowered.get(n.lower())
        if v not in (None, ""):
            return str(v)
    return None


# --------------------------------------------------------------- evidence
def store_evidence(db: Session, *, case_id: str, filename: str, data: bytes,
                   uploaded_by: str, content_type: str = "") -> Evidence:
    """Quarantine, hash-chain, and seal one file."""
    checks = quarantine.process_upload(filename, data)

    last = (db.query(Evidence)
              .filter(Evidence.case_id == case_id)
              .order_by(Evidence.sequence_number.desc())
              .first())
    seq = (last.sequence_number + 1) if last else 1
    prev_hash = last.chain_hash if last else None

    file_hash = sha256_bytes(data)
    ch = chain_hash(prev_hash, file_hash, seq)

    uri = storage.put("evidence", f"{case_id}/{seq:04d}_{filename}", data,
                      content_type or "application/octet-stream")

    evidence = Evidence(
        case_id=case_id, filename=filename, file_uri=uri,
        mime_type=content_type, size_bytes=len(data),
        sha256=file_hash, sequence_number=seq,
        prev_chain_hash=prev_hash, chain_hash=ch, merkle_leaf_hash=file_hash,
        scan_result=checks["scan"]["result"],
        processing_status="pending", uploaded_by=uploaded_by,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def verify_chain(db: Session, case_id: str) -> dict:
    """Recompute the whole chain. Any altered record breaks every hash after it."""
    rows = (db.query(Evidence)
              .filter(Evidence.case_id == case_id)
              .order_by(Evidence.sequence_number.asc()).all())
    prev = None
    for row in rows:
        expected = chain_hash(prev, row.sha256, row.sequence_number)
        if expected != row.chain_hash:
            return {"chain_valid": False, "broken_at": row.sequence_number,
                    "evidence_count": len(rows), "merkle_root": None}
        prev = row.chain_hash

    root = merkle_root([r.merkle_leaf_hash or r.sha256 for r in rows])
    return {"chain_valid": True, "broken_at": None,
            "evidence_count": len(rows), "merkle_root": root}


# ------------------------------------------------------------ processing
def process_evidence(db: Session, evidence_id: str, *,
                     use_llm: bool = True) -> dict:
    """Parse + extract. Called in the background after upload."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if evidence is None:
        return {"error": "evidence not found"}

    evidence.processing_status = "processing"
    db.commit()

    try:
        data = storage.get(evidence.file_uri)
        doc = parsers.parse_file(evidence.filename, data)

        obs_count = 0
        if doc.pages:
            obs_count += _ingest_text(db, evidence, doc, use_llm=use_llm)
        if doc.rows:
            obs_count += _ingest_rows(db, evidence, doc)

        evidence.processing_status = "done"
        db.commit()
        return {"evidence_id": evidence_id, "kind": doc.kind,
                "observations": obs_count}

    except Exception as exc:  # noqa: BLE001
        log.exception("Processing failed for %s", evidence_id)
        evidence.processing_status = "failed"
        db.commit()
        return {"evidence_id": evidence_id, "error": str(exc)}


def _record_observation(db: Session, evidence: Evidence, ex, *,
                        page: int | None = None, row: int | None = None):
    prov = Provenance(
        source_type="document", source_id=evidence.id,
        document_id=evidence.id, case_id=evidence.case_id,
        page_number=page, row_number=row, text_span=ex.context[:500],
        extraction_method=ex.method, confidence=ex.confidence,
    )
    db.add(prov)

    obs = Observation(
        case_id=evidence.case_id, source_document_id=evidence.id,
        page_number=page, row_number=row,
        text_span=ex.context[:500], raw_text=ex.raw_text,
        entity_type=ex.entity_type, normalized_value=ex.normalized_value,
        extraction_confidence=ex.confidence, extraction_method=ex.method,
        model_name=ex.meta.get("model"),
        model_version=ex.meta.get("provider"),
        algorithm_name=EXTRACTOR_ALGORITHMS.get(ex.method, ex.method),
        algorithm_version=EXTRACTOR_VERSION,
        prompt_version=ex.meta.get("prompt_version"),
        observed_at=evidence.uploaded_at,
    )
    db.add(obs)
    return obs


def _ingest_text(db: Session, evidence: Evidence, doc: parsers.ParsedDocument,
                 *, use_llm: bool) -> int:
    count = 0
    for page_no, page_text in enumerate(doc.pages, start=1):
        if not page_text.strip():
            continue
        for ex in extractors.extract_all(page_text, use_llm=use_llm):
            _record_observation(db, evidence, ex, page=page_no)
            count += 1
    db.commit()
    return count


def _ingest_rows(db: Session, evidence: Evidence,
                 doc: parsers.ParsedDocument) -> int:
    """Structured rows create observations AND source-observed relationships."""
    count = 0
    entity_cache: dict[tuple[str, str], Entity] = {}

    def get_entity(etype: str, value: str) -> Entity | None:
        if not value:
            return None
        key = (etype, value.lower())
        if key in entity_cache:
            return entity_cache[key]
        ent = (db.query(Entity)
                 .filter(Entity.case_id == evidence.case_id,
                         Entity.type == etype,
                         func.lower(Entity.name) == value.lower())
                 .first())
        if ent is None:
            ent = Entity(case_id=evidence.case_id, type=etype, name=value,
                         attributes={"source": doc.kind})
            db.add(ent)
            db.flush()
        entity_cache[key] = ent
        return ent

    for idx, row in enumerate(doc.rows, start=1):
        blob = " ".join(str(v) for v in row.values() if v)
        for ex in extractors.extract_by_regex(blob):
            _record_observation(db, evidence, ex, row=idx)
            count += 1

        if doc.kind == "cdr":
            a = _pick(row, "caller", "a_party", "from", "calling_number")
            b = _pick(row, "callee", "b_party", "to", "called_number")
            ts = _parse_dt(_pick(row, "timestamp", "datetime", "call_time", "date"))
            dur = _pick(row, "duration", "duration_sec", "seconds")
            tower = _pick(row, "tower_id", "cell_id", "cgi", "tower")
            lat = _pick(row, "lat", "latitude")
            lon = _pick(row, "lon", "long", "longitude")
            if a and b:
                ea, eb = get_entity("PHONE", a), get_entity("PHONE", b)
                if ea and eb:
                    db.add(Relationship(
                        case_id=evidence.case_id, source_id=ea.id, target_id=eb.id,
                        type="CALLED", relationship_confidence=0.95,
                        status="source_observed", evidence_id=evidence.id,
                        occurred_at=ts, observed_at=ts,
                        attributes={"duration": dur, "tower_id": tower,
                                    "lat": float(lat) if lat else None,
                                    "lon": float(lon) if lon else None,
                                    "row": idx},
                    ))

        elif doc.kind == "bank":
            src = _pick(row, "from_account", "sender", "debit_account", "from")
            dst = _pick(row, "to_account", "receiver", "credit_account", "to")
            amt = _pick(row, "amount", "amt", "value")
            ts = _parse_dt(_pick(row, "timestamp", "datetime", "date", "txn_date"))
            if src and dst:
                ea, eb = get_entity("ACCOUNT", src), get_entity("ACCOUNT", dst)
                if ea and eb:
                    try:
                        amount = float(str(amt).replace(",", "")) if amt else 0.0
                    except ValueError:
                        amount = 0.0
                    db.add(Relationship(
                        case_id=evidence.case_id, source_id=ea.id, target_id=eb.id,
                        type="SENT_MONEY", relationship_confidence=0.95,
                        status="source_observed", evidence_id=evidence.id,
                        occurred_at=ts, observed_at=ts,
                        attributes={"amount": amount, "row": idx},
                    ))

        elif doc.kind == "vehicle":
            plate = _pick(row, "registration_no", "vehicle_no", "plate")
            owner = _pick(row, "owner", "owner_name", "registered_to")
            if plate and owner:
                ev, eo = get_entity("VEHICLE", plate), get_entity("PERSON", owner)
                if ev and eo:
                    db.add(Relationship(
                        case_id=evidence.case_id, source_id=eo.id, target_id=ev.id,
                        type="OWNS", relationship_confidence=0.97,
                        status="source_observed", evidence_id=evidence.id,
                        attributes={"row": idx},
                    ))

        elif doc.kind == "criminal_history":
            person = _pick(row, "person", "name", "accused")
            offense = _pick(row, "offense_type", "offence_type", "offence")
            ref = _pick(row, "case_ref", "prior_case", "case_no")
            when = _parse_dt(_pick(row, "date", "year"))
            if person:
                ep = get_entity("PERSON", person)
                if ep:
                    db.add(CriminalHistory(
                        entity_id=ep.id, case_ref=ref, offense_type=offense,
                        date=when, source_document_id=evidence.id,
                    ))

    db.commit()
    _bump_graph_version(db, evidence.case_id)
    return count


# ------------------------------------------------------------ graph sync
def _bump_graph_version(db: Session, case_id: str) -> int:
    state = db.query(CaseGraphState).filter(
        CaseGraphState.case_id == case_id).first()
    if state is None:
        state = CaseGraphState(case_id=case_id, graph_version=1)
        db.add(state)
    else:
        state.graph_version += 1
        state.updated_at = datetime.now(timezone.utc)
    db.commit()
    return state.graph_version


def emit_outbox(db: Session, *, aggregate_type: str, aggregate_id: str,
                event_type: str, case_id: str, payload: dict) -> OutboxEvent:
    """Called INSIDE the same transaction as the primary write."""
    version = _bump_graph_version(db, case_id)
    event = OutboxEvent(
        aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, event_type=event_type,
        case_id=case_id, payload=payload, status="pending",
    )
    db.add(event)
    return event
