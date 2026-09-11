from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, authorize_case, require_role
from app.db.session import get_db
from app.models import Entity, PredictedLink, Relationship
from app.services.analytics import (compute_centrality, graph_version,
                                    investigative_priority, predict_links)

router = APIRouter(prefix="/cases/{case_id}/graph", tags=["graph"])

CONFIRMED = ["source_observed", "human_confirmed", "inferred"]


@router.get("")
def get_graph(case_id: str, user: CurrentUser,
              until: str | None = Query(None, description="ISO timestamp - temporal filter"),
              db: Session = Depends(get_db)):
    """Cytoscape-ready nodes + edges.

    CONFIRMED KNOWLEDGE only. Predicted links live in a separate endpoint and
    are never mixed into this graph.
    """
    authorize_case(db, user, case_id)

    entities = db.query(Entity).filter(Entity.case_id == case_id).limit(2000).all()
    q = db.query(Relationship).filter(Relationship.case_id == case_id,
                                      Relationship.status.in_(CONFIRMED))
    if until:
        from dateutil import parser as dp
        try:
            q = q.filter((Relationship.occurred_at.is_(None)) |
                         (Relationship.occurred_at <= dp.parse(until)))
        except (ValueError, TypeError):
            pass

    rels = q.limit(8000).all()
    metrics = compute_centrality(db, case_id)

    nodes = [{
        "data": {
            "id": str(e.id), "label": e.name, "type": e.type,
            "aliases": e.aliases or [],
            "degree": round(metrics["degree"].get(str(e.id), 0.0), 4),
            "betweenness": round(metrics["betweenness"].get(str(e.id), 0.0), 4),
            "community": metrics["communities"].get(str(e.id), 0),
        }
    } for e in entities]

    edges = [{
        "data": {
            "id": str(r.id), "source": str(r.source_id), "target": str(r.target_id),
            "label": r.type, "status": r.status,
            "confidence": r.relationship_confidence,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
            "evidence_id": str(r.evidence_id or ""),
            "attributes": r.attributes or {},
        }
    } for r in rels if r.source_id and r.target_id]

    return {"nodes": nodes, "edges": edges,
            "graph_version": metrics["graph_version"],
            "layer": "confirmed_knowledge",
            "counts": {"nodes": len(nodes), "edges": len(edges)}}


@router.get("/leads")
def get_leads(case_id: str, user: CurrentUser, refresh: bool = False,
              db: Session = Depends(get_db)):
    """INVESTIGATIVE LEADS layer - statistically likely but UNOBSERVED links.

    An Adamic-Adar score is a similarity measure, NOT a calibrated
    probability. It is never phrased as a percentage likelihood and never
    written into the confirmed graph.
    """
    authorize_case(db, user, case_id)
    if refresh:
        predict_links(db, case_id)

    rows = (db.query(PredictedLink)
              .filter(PredictedLink.case_id == case_id)
              .order_by(PredictedLink.score.desc()).limit(25).all())
    names = {str(e.id): e.name for e in
             db.query(Entity).filter(Entity.case_id == case_id).all()}

    return [{
        "id": str(p.id),
        "source": {"id": str(p.source_id), "name": names.get(str(p.source_id), "?")},
        "target": {"id": str(p.target_id), "name": names.get(str(p.target_id), "?")},
        "link_prediction_score": p.score,
        "method": "Adamic-Adar",
        "status": "Unverified Investigative Lead",
        "evidence": "None currently supports this relationship.",
        "graph_version": p.graph_version,
    } for p in rows]


@router.get("/priority")
def priority_ranking(case_id: str, user: CurrentUser, top: int = 10,
                     db: Session = Depends(get_db)):
    authorize_case(db, user, case_id)
    metrics = compute_centrality(db, case_id)
    ranked = sorted(metrics["degree"].items(), key=lambda kv: kv[1],
                    reverse=True)[:top]
    names = {str(e.id): e.name for e in
             db.query(Entity).filter(Entity.case_id == case_id).all()}
    return [{**investigative_priority(db, case_id, eid),
             "name": names.get(eid, "?")} for eid, _ in ranked]


@router.post("/sync")
def force_sync(case_id: str, user: CurrentUser, db: Session = Depends(get_db),
               _=Depends(require_role("INSPECTOR"))):
    """Drain the outbox now, then backfill anything missing in Neo4j."""
    authorize_case(db, user, case_id)
    from app.services.graph_sync import backfill_case, drain_outbox
    drained = drain_outbox(db)
    filled = backfill_case(db, case_id)
    return {"drained": drained, "backfilled": filled,
            "graph_version": graph_version(db, case_id)}


@router.get("/map")
def map_points(case_id: str, user: CurrentUser, db: Session = Depends(get_db)):
    """Co-location view data.

    Each point carries its SOURCE PRECISION so the map can render GPS fixes
    and cell-site associations differently — a tower association must never
    be drawn as if it were a precise coordinate.
    """
    authorize_case(db, user, case_id)
    from app.models import Anomaly

    rels = (db.query(Relationship)
              .filter(Relationship.case_id == case_id,
                      Relationship.occurred_at.isnot(None))
              .limit(3000).all())
    names = {str(e.id): e.name for e in
             db.query(Entity).filter(Entity.case_id == case_id).all()}

    points = []
    for rel in rels:
        attrs = rel.attributes or {}
        lat, lon = attrs.get("lat"), attrs.get("lon")
        tower = attrs.get("tower_id")

        if lat is not None and lon is not None:
            points.append({
                "id": str(rel.id), "lat": float(lat), "lon": float(lon),
                "precision": "gps", "radius_m": 25,
                "entity_id": str(rel.source_id),
                "entity_name": names.get(str(rel.source_id), "?"),
                "occurred_at": rel.occurred_at.isoformat(),
                "type": rel.type,
            })
        elif tower and tower in TOWER_COORDS:
            t = TOWER_COORDS[tower]
            points.append({
                "id": str(rel.id), "lat": t["lat"], "lon": t["lon"],
                "precision": "cell_tower",
                # drawn as a coverage area, never a point fix
                "radius_m": t.get("radius_m", 800),
                "tower_id": tower,
                "entity_id": str(rel.source_id),
                "entity_name": names.get(str(rel.source_id), "?"),
                "occurred_at": rel.occurred_at.isoformat(),
                "type": rel.type,
            })

    colocations = [{
        "id": str(a.id), "title": a.title, "precision": a.source_precision,
        "entities": [names.get(e, "?") for e in (a.entity_ids or [])],
        "window_start": a.window_start, "window_end": a.window_end,
        "details": a.details or {},
    } for a in db.query(Anomaly).filter(Anomaly.case_id == case_id,
                                        Anomaly.kind == "location").all()]

    return {"points": points, "colocations": colocations,
            "legend": {
                "gps": "Precise coordinate — distance claims are defensible",
                "cell_tower": ("Serving-cell association — shown as a coverage "
                               "area, NOT a precise location"),
            }}


# Demo tower positions (synthetic - Delhi NCR approximations)
TOWER_COORDS = {
    "TWR-DEL-114": {"lat": 28.5355, "lon": 77.2410, "radius_m": 900},
    "TWR-DEL-207": {"lat": 28.5672, "lon": 77.2100, "radius_m": 850},
    "TWR-GGN-051": {"lat": 28.4595, "lon": 77.0266, "radius_m": 1100},
    "TWR-NOI-083": {"lat": 28.5355, "lon": 77.3910, "radius_m": 1000},
}


class LifecycleChange(BaseModel):
    status: str
    reason: str = ""
    superseded_by: str | None = None


@router.post("/relationships/{relationship_id}/status")
def change_relationship_status(case_id: str, relationship_id: str,
                               body: LifecycleChange, user: CurrentUser,
                               db: Session = Depends(get_db),
                               _=Depends(require_role("INSPECTOR"))):
    """Relationship lifecycle transitions. NO HARD DELETES — a relationship is
    only ever moved to disputed / rejected / superseded / expired, and the
    transition is audit-logged with a reason."""
    from datetime import datetime, timezone

    from app.services.audit import write_audit
    from app.services.ingestion import emit_outbox

    authorize_case(db, user, case_id)

    allowed = {"source_observed", "inferred", "proposed", "human_confirmed",
               "disputed", "rejected", "superseded", "expired"}
    if body.status not in allowed:
        raise HTTPException(400, f"status must be one of {sorted(allowed)}")

    # Confirming or disputing evidence-backed knowledge is an Inspector action.
    if body.status in ("human_confirmed", "superseded") and not user.outranks("INSPECTOR"):
        raise HTTPException(403, "Requires INSPECTOR or higher")

    rel = db.query(Relationship).filter(Relationship.id == relationship_id,
                                        Relationship.case_id == case_id).first()
    if rel is None:
        raise HTTPException(404, "Relationship not found")

    previous = rel.status
    rel.status = body.status
    if body.status == "human_confirmed":
        rel.verified_by = user.email
        rel.verified_at = datetime.now(timezone.utc)
    if body.superseded_by:
        rel.attributes = {**(rel.attributes or {}),
                          "superseded_by": body.superseded_by}

    emit_outbox(db, aggregate_type="relationship", aggregate_id=str(rel.id),
                event_type=f"relationship.{body.status}", case_id=case_id,
                payload={"from": previous, "to": body.status})
    db.commit()

    write_audit(db, actor=user.email, actor_role=user.role,
                action=f"relationship.{body.status}",
                resource=f"relationship:{relationship_id}", case_id=case_id,
                detail={"from": previous, "to": body.status,
                        "reason": body.reason[:300]})

    return {"id": str(rel.id), "previous_status": previous,
            "status": rel.status, "verified_by": rel.verified_by,
            "note": "No hard delete — the record is retained with its new state."}
