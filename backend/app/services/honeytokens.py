"""Honeytoken canaries — DEMO ENVIRONMENT ONLY.

Synthetic canary records exist only in the demo dataset. Any access to one is
flagged as a security alert with the accessing user, resource and timestamp.
Clearly labelled as a security-control demonstration; never mixed into real
investigative data.
"""
import logging

from sqlalchemy.orm import Session

from app.models import Entity, SecurityEvent

log = logging.getLogger("trinetra.honeytokens")

CANARY_MARKER = "__canary__"

CANARIES = [
    {"type": "PERSON",  "name": "Rajkumar Testwala"},
    {"type": "PHONE",   "name": "9999900001"},
    {"type": "ACCOUNT", "name": "50100000000001"},
]


def seed_canaries(db: Session, case_id: str) -> int:
    """Plant canary entities. They connect to nothing, so no legitimate
    investigation path leads to them - only deliberate browsing does."""
    planted = 0
    for spec in CANARIES:
        exists = (db.query(Entity)
                    .filter(Entity.case_id == case_id,
                            Entity.name == spec["name"]).first())
        if exists:
            continue
        db.add(Entity(case_id=case_id, type=spec["type"], name=spec["name"],
                      aliases=[],
                      attributes={CANARY_MARKER: True,
                                  "note": "Synthetic canary - demo only"}))
        planted += 1
    db.commit()
    log.info("Planted %s honeytoken canaries in case %s", planted, case_id)
    return planted


def is_canary(entity: Entity | None) -> bool:
    return bool(entity and (entity.attributes or {}).get(CANARY_MARKER))


def trip(db: Session, *, entity: Entity, actor: str, actor_role: str,
         ip: str | None = None) -> None:
    """Record the hit as a high-severity security event."""
    db.add(SecurityEvent(
        kind="honeytoken_hit", severity="high", ip_address=ip, risk_score=85,
        detail={"entity_id": str(entity.id), "entity_name": entity.name,
                "entity_type": entity.type, "actor": actor,
                "actor_role": actor_role,
                "note": "Canary record accessed — no legitimate investigative "
                        "path leads to this entity."},
    ))
    db.commit()
    log.warning("HONEYTOKEN TRIPPED: %s accessed canary %s", actor, entity.name)
