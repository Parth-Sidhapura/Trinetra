"""SQLAlchemy models - the full TRINETRA schema.

Postgres is the system of record. Neo4j is a projection of this, never
the other way around.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY, Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint, Index,
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------
BNSS_STAGE = ("fir_registered", "under_investigation", "chargesheet_filed", "trial", "disposed")
CLASSIFICATION = ("public", "internal", "confidential", "restricted", "highly_restricted")
REL_STATUS = ("source_observed", "inferred", "proposed", "human_confirmed",
              "disputed", "rejected", "superseded", "expired")
CANDIDATE_STATUS = ("pending", "confirmed", "rejected")
OUTBOX_STATUS = ("pending", "processed", "failed")
ROLES = ("CONSTABLE", "INSPECTOR", "ADMIN")


# --------------------------------------------------------------------------
# Cases & FIRs
# --------------------------------------------------------------------------
class Case(Base):
    __tablename__ = "cases"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    title = Column(String(300), nullable=False)
    status = Column(String(50), default="open")
    bnss_stage = Column(Enum(*BNSS_STAGE, name="bnss_stage"), default="fir_registered")
    data_classification = Column(Enum(*CLASSIFICATION, name="classification"), default="confidential")
    department = Column(String(120), default="CYBER_CELL")
    created_at = Column(DateTime(timezone=True), default=_now)

    firs = relationship("FIR", back_populates="case", cascade="all, delete-orphan")


class FIR(Base):
    __tablename__ = "firs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True, nullable=False)
    fir_number = Column(String(80), nullable=False)
    police_station = Column(String(200))
    date_registered = Column(DateTime(timezone=True))
    bns_sections = Column(ARRAY(String), default=list)
    complainant_ref = Column(String(200))

    case = relationship("Case", back_populates="firs")


# --------------------------------------------------------------------------
# Evidence + integrity chain
# --------------------------------------------------------------------------
class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True, nullable=False)
    filename = Column(String(400), nullable=False)
    file_uri = Column(Text)
    mime_type = Column(String(120))
    size_bytes = Column(Integer)
    sha256 = Column(String(64), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    prev_chain_hash = Column(String(64))
    chain_hash = Column(String(64), nullable=False)
    merkle_leaf_hash = Column(String(64))
    scan_result = Column(String(40), default="not_scanned")
    processing_status = Column(String(40), default="pending")
    uploaded_at = Column(DateTime(timezone=True), default=_now)
    uploaded_by = Column(String(200))

    __table_args__ = (Index("ix_evidence_case_seq", "case_id", "sequence_number"),)


class EvidenceBackupManifest(Base):
    """Append-only export of the hash chain + audit log to separate storage."""
    __tablename__ = "evidence_backup_manifests"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    sequence_number = Column(Integer, nullable=False)
    manifest_hash = Column(String(64), nullable=False)
    merkle_root = Column(String(64))
    storage_uri = Column(Text)
    record_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)


# --------------------------------------------------------------------------
# Observation -> Resolution -> Canonical Entity
# --------------------------------------------------------------------------
class Observation(Base):
    """Exactly what a document said, and where. NEVER overwritten."""
    __tablename__ = "observations"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True, nullable=False)
    source_document_id = Column(UUID(as_uuid=False), ForeignKey("evidence.id"), index=True)
    page_number = Column(Integer)
    row_number = Column(Integer)
    text_span = Column(Text)
    raw_text = Column(Text, nullable=False)
    entity_type = Column(String(60), nullable=False)   # PERSON, PHONE, VEHICLE, ACCOUNT, LOCATION
    normalized_value = Column(String(400), index=True)
    extraction_confidence = Column(Float, default=0.0)
    extraction_method = Column(String(80))             # spacy | regex | gemini
    # --- AI & algorithm version provenance ---
    model_name = Column(String(120))
    model_version = Column(String(60))
    algorithm_name = Column(String(120))
    algorithm_version = Column(String(60))
    prompt_version = Column(String(60))
    # pgvector column - semantic entity resolution searches over this
    embedding = Column(Vector(768), nullable=True)
    # --- temporal precision: three distinct timestamps, never one ---
    observed_at = Column(DateTime(timezone=True))   # when the source captured it
    ingested_at = Column(DateTime(timezone=True), default=_now)  # when we processed it
    created_at = Column(DateTime(timezone=True), default=_now)


class ResolutionCandidate(Base):
    """The system's HYPOTHESIS that two observations are the same person.
    Never auto-promoted - a human confirms."""
    __tablename__ = "resolution_candidates"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True)
    entity_a_observation_id = Column(UUID(as_uuid=False), ForeignKey("observations.id"))
    entity_b_observation_id = Column(UUID(as_uuid=False), ForeignKey("observations.id"))
    resolution_confidence = Column(Float, default=0.0)
    method = Column(String(80))                        # exact | fuzzy | phonetic | semantic
    algorithm_name = Column(String(120))
    algorithm_version = Column(String(60))
    reasoning = Column(Text)                           # shown in the UI
    status = Column(Enum(*CANDIDATE_STATUS, name="candidate_status"), default="pending")
    reviewed_by = Column(String(200))
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_now)


class Entity(Base):
    """Canonical entity - exists only after human confirmation."""
    __tablename__ = "entities"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True, nullable=False)
    type = Column(String(60), nullable=False, index=True)
    name = Column(String(400), nullable=False)
    aliases = Column(ARRAY(String), default=list)
    attributes = Column(JSONB, default=dict)
    source_observation_ids = Column(ARRAY(String), default=list)
    created_at = Column(DateTime(timezone=True), default=_now)

    __table_args__ = (Index("ix_entities_case_type", "case_id", "type"),)


class CriminalHistory(Base):
    __tablename__ = "criminal_history"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    entity_id = Column(UUID(as_uuid=False), ForeignKey("entities.id"), index=True)
    case_ref = Column(String(120))
    offense_type = Column(String(200))
    date = Column(DateTime(timezone=True))
    source_document_id = Column(UUID(as_uuid=False), ForeignKey("evidence.id"))


class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True, nullable=False)
    source_id = Column(UUID(as_uuid=False), ForeignKey("entities.id"), index=True)
    target_id = Column(UUID(as_uuid=False), ForeignKey("entities.id"), index=True)
    type = Column(String(80), nullable=False)          # USED, OWNS, SENT_MONEY, ASSOCIATED_WITH...
    relationship_confidence = Column(Float, default=0.0)
    status = Column(Enum(*REL_STATUS, name="rel_status"), default="source_observed")
    evidence_id = Column(UUID(as_uuid=False), ForeignKey("evidence.id"))
    provenance_id = Column(UUID(as_uuid=False), ForeignKey("provenance.provenance_id"))
    attributes = Column(JSONB, default=dict)
    occurred_at = Column(DateTime(timezone=True))
    occurred_from = Column(DateTime(timezone=True))
    occurred_to = Column(DateTime(timezone=True))
    observed_at = Column(DateTime(timezone=True))
    ingested_at = Column(DateTime(timezone=True), default=_now)
    verified_by = Column(String(200))
    verified_at = Column(DateTime(timezone=True))

    __table_args__ = (Index("ix_rel_case_status", "case_id", "status"),)


class Provenance(Base):
    __tablename__ = "provenance"
    provenance_id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    source_type = Column(String(80))
    source_id = Column(UUID(as_uuid=False))
    document_id = Column(UUID(as_uuid=False), ForeignKey("evidence.id"))
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True)
    page_number = Column(Integer)
    row_number = Column(Integer)
    text_span = Column(Text)
    source_timestamp = Column(DateTime(timezone=True))
    extraction_method = Column(String(80))
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), default=_now)


# --------------------------------------------------------------------------
# Anomalies & analytics
# --------------------------------------------------------------------------
class Anomaly(Base):
    __tablename__ = "anomalies"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True, nullable=False)
    kind = Column(String(60), nullable=False)          # financial | temporal | location
    title = Column(String(300))
    description = Column(Text)
    anomaly_confidence = Column(Float, default=0.0)
    source_precision = Column(String(40))              # gps | cell_tower | n/a
    entity_ids = Column(ARRAY(String), default=list)
    evidence_ids = Column(ARRAY(String), default=list)
    window_start = Column(DateTime(timezone=True))
    window_end = Column(DateTime(timezone=True))
    details = Column(JSONB, default=dict)
    detector_name = Column(String(120))
    detector_version = Column(String(40))
    created_at = Column(DateTime(timezone=True), default=_now)


class PredictedLink(Base):
    """Unverified investigative lead. NEVER written into relationships."""
    __tablename__ = "predicted_links"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), index=True)
    source_id = Column(UUID(as_uuid=False), ForeignKey("entities.id"))
    target_id = Column(UUID(as_uuid=False), ForeignKey("entities.id"))
    score = Column(Float, default=0.0)                 # NOT a probability
    method = Column(String(60), default="adamic_adar")
    algorithm_name = Column(String(120), default="adamic_adar")
    algorithm_version = Column(String(60), default="networkx-3.4")
    graph_version = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)


class CaseGraphState(Base):
    __tablename__ = "case_graph_state"
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"), primary_key=True)
    graph_version = Column(Integer, default=0)
    analytics_version = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


# --------------------------------------------------------------------------
# Sync (transactional outbox)
# --------------------------------------------------------------------------
class OutboxEvent(Base):
    """Written in the SAME transaction as the primary write. A worker
    replays these into Neo4j idempotently."""
    __tablename__ = "outbox_events"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    aggregate_type = Column(String(80), nullable=False)
    aggregate_id = Column(UUID(as_uuid=False), nullable=False)
    aggregate_version = Column(Integer, nullable=False, default=1)
    event_type = Column(String(80), nullable=False)
    case_id = Column(UUID(as_uuid=False), index=True)
    payload = Column(JSONB, default=dict)
    status = Column(Enum(*OUTBOX_STATUS, name="outbox_status"), default="pending", index=True)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)
    processed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("aggregate_id", "aggregate_version", "event_type",
                         name="uq_outbox_idempotency"),
    )


# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------
class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(UUID(as_uuid=False), primary_key=True)   # matches Supabase auth uid
    email = Column(String(320), unique=True)
    full_name = Column(String(200))
    role = Column(Enum(*ROLES, name="user_role"), default="CONSTABLE")
    department = Column(String(120), default="CYBER_CELL")
    clearance = Column(Enum(*CLASSIFICATION, name="clearance"), default="internal")
    locked_until = Column(DateTime(timezone=True))   # set by incident response
    created_at = Column(DateTime(timezone=True), default=_now)


class SessionRecord(Base):
    __tablename__ = "sessions"
    session_id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), index=True)
    device_id = Column(String(200))
    ip_address = Column(String(60))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)
    last_seen = Column(DateTime(timezone=True), default=_now)
    expires_at = Column(DateTime(timezone=True))


class BreakGlassRequest(Base):
    __tablename__ = "break_glass_requests"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), index=True)
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.id"))
    reason = Column(Text, nullable=False)
    granted_at = Column(DateTime(timezone=True), default=_now)
    expires_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(200))
    reviewed_at = Column(DateTime(timezone=True))


class AuditLog(Base):
    """Append-only, hash-chained. Altering a past entry breaks every hash after it."""
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    sequence_number = Column(Integer, nullable=False)
    actor = Column(String(320))
    actor_role = Column(String(40))
    action = Column(String(120), nullable=False)
    resource = Column(String(200))
    case_id = Column(UUID(as_uuid=False), index=True)
    trace_id = Column(String(80))
    result = Column(String(40), default="allow")
    detail = Column(JSONB, default=dict)
    previous_event_hash = Column(String(64))
    event_hash = Column(String(64), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=_now)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    kind = Column(String(80))             # failed_login | bulk_download | honeytoken_hit
    severity = Column(String(20), default="low")
    user_id = Column(UUID(as_uuid=False))
    ip_address = Column(String(60))
    detail = Column(JSONB, default=dict)
    risk_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)
