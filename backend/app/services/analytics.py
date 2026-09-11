"""Graph analytics in NetworkX.

AuraDB Free has no GDS plugin, so a CAPPED subgraph is pulled into Python.
Results are cached and keyed on case_id + graph_version + analytics_version,
so a stale score is invalidated rather than silently shown.
"""
import logging
import time
from dataclasses import dataclass

import networkx as nx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CaseGraphState, Entity, PredictedLink, Relationship

log = logging.getLogger("trinetra.analytics")

ANALYTICS_VERSION = 1

# key -> (payload, expires_at)
_CACHE: dict[str, tuple[dict, float]] = {}

CONFIRMED = ("source_observed", "human_confirmed", "inferred")


@dataclass
class ScoreComponents:
    """A priority score is NEVER shown as a bare number."""
    network_centrality: float = 0.0
    cross_case_association: float = 0.0
    evidence_confidence: float = 0.0
    temporal_correlation: float = 0.0
    communication_activity: float = 0.0
    financial_connectivity: float = 0.0

    def total(self) -> float:
        weights = {
            "network_centrality": 0.25,
            "cross_case_association": 0.20,
            "evidence_confidence": 0.20,
            "temporal_correlation": 0.10,
            "communication_activity": 0.15,
            "financial_connectivity": 0.10,
        }
        return round(sum(getattr(self, k) * w for k, w in weights.items()), 1)

    def as_dict(self) -> dict:
        return {
            "Network Centrality": round(self.network_centrality, 1),
            "Cross-Case Association": round(self.cross_case_association, 1),
            "Evidence Confidence": round(self.evidence_confidence, 1),
            "Temporal Correlation": round(self.temporal_correlation, 1),
            "Communication Activity": round(self.communication_activity, 1),
            "Financial Connectivity": round(self.financial_connectivity, 1),
        }


def graph_version(db: Session, case_id: str) -> int:
    state = db.query(CaseGraphState).filter(
        CaseGraphState.case_id == case_id).first()
    return state.graph_version if state else 0


def _cache_key(case_id: str, version: int, suffix: str) -> str:
    return f"{case_id}:{version}:{ANALYTICS_VERSION}:{suffix}"


def build_networkx(db: Session, case_id: str,
                   *, statuses: tuple = CONFIRMED) -> nx.Graph:
    """Bounded subgraph - never the full unbounded graph in one pass."""
    rels = (db.query(Relationship)
              .filter(Relationship.case_id == case_id,
                      Relationship.status.in_(statuses))
              .order_by(Relationship.ingested_at.desc())
              .limit(settings.MAX_GRAPH_EDGES).all())

    graph = nx.Graph()
    for rel in rels:
        if not rel.source_id or not rel.target_id:
            continue
        src, dst = str(rel.source_id), str(rel.target_id)
        if graph.number_of_nodes() >= settings.MAX_GRAPH_NODES:
            break
        weight = float(rel.relationship_confidence or 0.5)
        if graph.has_edge(src, dst):
            graph[src][dst]["weight"] += weight
            graph[src][dst]["count"] += 1
        else:
            graph.add_edge(src, dst, weight=weight, count=1,
                           type=rel.type, status=rel.status)
    return graph


def compute_centrality(db: Session, case_id: str) -> dict:
    version = graph_version(db, case_id)
    key = _cache_key(case_id, version, "centrality")
    cached = _CACHE.get(key)
    if cached and cached[1] > time.time():
        return cached[0]

    graph = build_networkx(db, case_id)
    if graph.number_of_nodes() == 0:
        payload = {"degree": {}, "betweenness": {}, "communities": {},
                   "graph_version": version, "nodes": 0, "edges": 0}
    else:
        degree = nx.degree_centrality(graph)
        # betweenness is O(V*E) - sample on anything non-trivial
        k = min(graph.number_of_nodes(), 60)
        betweenness = nx.betweenness_centrality(
            graph, k=k if graph.number_of_nodes() > 60 else None, weight="weight")

        communities: dict[str, int] = {}
        try:
            for idx, group in enumerate(
                    nx.community.louvain_communities(graph, weight="weight", seed=42)):
                for node in group:
                    communities[node] = idx
        except Exception:  # noqa: BLE001
            for idx, comp in enumerate(nx.connected_components(graph)):
                for node in comp:
                    communities[node] = idx

        payload = {"degree": degree, "betweenness": betweenness,
                   "communities": communities, "graph_version": version,
                   "nodes": graph.number_of_nodes(),
                   "edges": graph.number_of_edges()}

    _CACHE[key] = (payload, time.time() + settings.ANALYTICS_CACHE_TTL)
    return payload


def investigative_priority(db: Session, case_id: str,
                           entity_id: str) -> dict:
    """Explainable priority. Never called a 'kingpin score', never a guilt score."""
    metrics = compute_centrality(db, case_id)
    eid = str(entity_id)

    degree = metrics["degree"].get(eid, 0.0)
    betweenness = metrics["betweenness"].get(eid, 0.0)

    rels = db.query(Relationship).filter(
        Relationship.case_id == case_id,
        Relationship.status.in_(CONFIRMED),
        (Relationship.source_id == entity_id) | (Relationship.target_id == entity_id),
    ).all()

    comms = sum(1 for r in rels if r.type in ("CALLED", "MESSAGED"))
    money = sum(1 for r in rels if r.type == "SENT_MONEY")
    timed = sum(1 for r in rels if r.occurred_at is not None)
    avg_conf = (sum(float(r.relationship_confidence or 0) for r in rels) / len(rels)
                if rels else 0.0)

    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    cross_case = 0.0
    if entity:
        others = db.query(Entity).filter(
            Entity.type == entity.type,
            Entity.name == entity.name,
            Entity.case_id != case_id,
        ).count()
        cross_case = min(others * 35.0, 100.0)

    components = ScoreComponents(
        network_centrality=min((degree * 0.6 + betweenness * 0.4) * 250, 100),
        cross_case_association=cross_case,
        evidence_confidence=avg_conf * 100,
        temporal_correlation=min(timed * 6.0, 100),
        communication_activity=min(comms * 8.0, 100),
        financial_connectivity=min(money * 12.0, 100),
    )

    return {
        "entity_id": eid,
        "investigative_priority": components.total(),
        "components": components.as_dict(),
        "graph_version": metrics["graph_version"],
        "analytics_version": ANALYTICS_VERSION,
        "label": "investigative priority",
        "disclaimer": ("Analytical prominence in the observed network. "
                       "This is not a measure of guilt."),
    }


def predict_links(db: Session, case_id: str, top_n: int = 10) -> list[dict]:
    """Adamic-Adar index over the confirmed graph.

    A similarity measure, NOT a calibrated probability - so it is never
    phrased as a percentage likelihood, and never written into relationships.
    """
    graph = build_networkx(db, case_id)
    if graph.number_of_nodes() < 3:
        return []

    version = graph_version(db, case_id)
    candidates = [(u, v) for u, v in nx.non_edges(graph)][:20000]
    try:
        scored = sorted(nx.adamic_adar_index(graph, candidates),
                        key=lambda x: x[2], reverse=True)[:top_n]
    except Exception:  # noqa: BLE001
        return []

    db.query(PredictedLink).filter(PredictedLink.case_id == case_id).delete()

    out = []
    for u, v, score in scored:
        if score <= 0:
            continue
        db.add(PredictedLink(case_id=case_id, source_id=u, target_id=v,
                             score=round(float(score), 3),
                             method="adamic_adar", graph_version=version))
        out.append({
            "source_id": u, "target_id": v,
            "link_prediction_score": round(float(score), 3),
            "method": "Adamic-Adar",
            "status": "Unverified Investigative Lead",
            "evidence": "None currently supports this relationship.",
        })
    db.commit()
    return out


def refresh_case_analytics(db: Session, case_id: str) -> dict:
    metrics = compute_centrality(db, case_id)
    links = predict_links(db, case_id)
    return {"nodes": metrics["nodes"], "edges": metrics["edges"],
            "graph_version": metrics["graph_version"],
            "predicted_links": len(links)}
