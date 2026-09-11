"""Rule-based anomaly detection across three canonical types:
financial (structuring), time-based (communication burst), location (co-location).

Every finding is a "potential pattern" or "investigative lead" - never proof.
"""
import logging
import math
from collections import defaultdict
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Anomaly, Entity, Relationship

log = logging.getLogger("trinetra.anomalies")

DETECTOR_VERSION = "1.0"

# Indian reporting threshold for cash transactions
STRUCTURING_THRESHOLD = 50_000.0
STRUCTURING_WINDOW_HOURS = 48
STRUCTURING_MIN_TXNS = 3

BURST_WINDOW_MINUTES = 60
BURST_MULTIPLIER = 3.0
BURST_MIN_CALLS = 5

COLOCATION_RADIUS_M = 50
COLOCATION_WINDOW_MINUTES = 15


def _name(db: Session, entity_id) -> str:
    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    return ent.name if ent else str(entity_id)


def _clear_previous(db: Session, case_id: str, kind: str) -> None:
    db.query(Anomaly).filter(Anomaly.case_id == case_id,
                             Anomaly.kind == kind).delete()


# ------------------------------------------------------- FINANCIAL
def detect_financial_structuring(db: Session, case_id: str) -> list[Anomaly]:
    """Multiple sub-threshold transfers inside a short window - the classic
    pattern for staying under a reporting limit."""
    _clear_previous(db, case_id, "financial")

    rels = (db.query(Relationship)
              .filter(Relationship.case_id == case_id,
                      Relationship.type == "SENT_MONEY",
                      Relationship.occurred_at.isnot(None))
              .order_by(Relationship.occurred_at.asc()).all())

    by_sender: dict[str, list[Relationship]] = defaultdict(list)
    for rel in rels:
        by_sender[str(rel.source_id)].append(rel)

    found: list[Anomaly] = []
    window = timedelta(hours=STRUCTURING_WINDOW_HOURS)

    for sender, txns in by_sender.items():
        for i, anchor in enumerate(txns):
            bucket = [t for t in txns[i:]
                      if t.occurred_at - anchor.occurred_at <= window]
            if len(bucket) < STRUCTURING_MIN_TXNS:
                continue

            amounts = [float((t.attributes or {}).get("amount") or 0) for t in bucket]
            if not amounts or any(a <= 0 for a in amounts):
                continue

            # all individually under the threshold, but together well over it
            if max(amounts) >= STRUCTURING_THRESHOLD:
                continue
            total = sum(amounts)
            if total < STRUCTURING_THRESHOLD:
                continue

            # near-threshold amounts are the real signal
            avg = total / len(amounts)
            if avg < STRUCTURING_THRESHOLD * 0.4:
                continue

            entity_ids = {sender} | {str(t.target_id) for t in bucket}
            confidence = min(0.55 + 0.08 * len(bucket) +
                             0.2 * (avg / STRUCTURING_THRESHOLD), 0.95)

            anomaly = Anomaly(
                case_id=case_id, kind="financial",
                title="Potential financial structuring",
                description=(
                    f"{len(bucket)} transfers totalling ₹{total:,.0f} from "
                    f"{_name(db, sender)} within "
                    f"{STRUCTURING_WINDOW_HOURS}h, each individually below the "
                    f"₹{STRUCTURING_THRESHOLD:,.0f} reporting threshold "
                    f"(average ₹{avg:,.0f})."
                ),
                anomaly_confidence=round(confidence, 2),
                source_precision="n/a",
                entity_ids=list(entity_ids),
                evidence_ids=[str(t.evidence_id) for t in bucket if t.evidence_id],
                window_start=anchor.occurred_at,
                window_end=bucket[-1].occurred_at,
                details={"transaction_count": len(bucket), "total_amount": total,
                         "average_amount": round(avg, 2),
                         "threshold": STRUCTURING_THRESHOLD,
                         "amounts": amounts},
                detector_name="financial_structuring",
                detector_version=DETECTOR_VERSION,
            )
            db.add(anomaly)
            found.append(anomaly)
            break   # one flag per sender is enough

    db.commit()
    return found


# -------------------------------------------------------- TIME-BASED
def detect_communication_burst(db: Session, case_id: str) -> list[Anomaly]:
    """A spike in call volume against that entity's own baseline."""
    _clear_previous(db, case_id, "temporal")

    rels = (db.query(Relationship)
              .filter(Relationship.case_id == case_id,
                      Relationship.type.in_(["CALLED", "MESSAGED"]),
                      Relationship.occurred_at.isnot(None))
              .order_by(Relationship.occurred_at.asc()).all())

    by_entity: dict[str, list[Relationship]] = defaultdict(list)
    for rel in rels:
        by_entity[str(rel.source_id)].append(rel)

    found: list[Anomaly] = []
    window = timedelta(minutes=BURST_WINDOW_MINUTES)

    for entity_id, calls in by_entity.items():
        if len(calls) < BURST_MIN_CALLS:
            continue

        span_hours = max(
            (calls[-1].occurred_at - calls[0].occurred_at).total_seconds() / 3600.0,
            1.0)
        baseline_per_window = (len(calls) / span_hours) * (BURST_WINDOW_MINUTES / 60.0)

        best: list[Relationship] = []
        for i, anchor in enumerate(calls):
            bucket = [c for c in calls[i:]
                      if c.occurred_at - anchor.occurred_at <= window]
            if len(bucket) > len(best):
                best = bucket

        if len(best) < BURST_MIN_CALLS:
            continue
        if baseline_per_window > 0 and len(best) < baseline_per_window * BURST_MULTIPLIER:
            continue

        ratio = len(best) / baseline_per_window if baseline_per_window else BURST_MULTIPLIER
        counterparts = {str(c.target_id) for c in best}

        anomaly = Anomaly(
            case_id=case_id, kind="temporal",
            title="Potential communication burst",
            description=(
                f"{_name(db, entity_id)} placed {len(best)} calls to "
                f"{len(counterparts)} distinct numbers within "
                f"{BURST_WINDOW_MINUTES} minutes — roughly {ratio:.1f}× that "
                f"entity's own baseline rate for this dataset."
            ),
            anomaly_confidence=round(min(0.5 + 0.06 * len(best), 0.92), 2),
            source_precision="n/a",
            entity_ids=[entity_id, *counterparts],
            evidence_ids=[str(c.evidence_id) for c in best if c.evidence_id],
            window_start=best[0].occurred_at, window_end=best[-1].occurred_at,
            details={"call_count": len(best),
                     "distinct_counterparts": len(counterparts),
                     "baseline_per_window": round(baseline_per_window, 2),
                     "ratio": round(ratio, 2)},
            detector_name="communication_burst",
            detector_version=DETECTOR_VERSION,
        )
        db.add(anomaly)
        found.append(anomaly)

    db.commit()
    return found


# ---------------------------------------------------------- LOCATION
def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2 +
         math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def _hdbscan_clusters(points: list[tuple], eps_m: float,
                      window_min: int) -> list[list[int]]:
    """Density-based spatio-temporal clustering.

    Uses HDBSCAN when available. Scales time into the same metric space as
    distance so a cluster means "close in space AND close in time".
    Falls back to a pairwise haversine sweep when hdbscan isn't installed
    (see Known Limitations - GeoPandas/hdbscan build weight on free tiers).
    """
    if len(points) < 3:
        return []
    try:
        import hdbscan  # type: ignore
        import numpy as np
    except ImportError:
        log.info("hdbscan not installed - using haversine fallback")
        return []

    lat0 = sum(p[1] for p in points) / len(points)
    # metres per degree, corrected for latitude
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat0))
    t0 = min(p[3] for p in points)
    # time scaled so `window_min` minutes ~= eps_m metres of separation
    time_scale = eps_m / max(window_min * 60.0, 1.0)

    matrix = np.array([
        [(p[2] - points[0][2]) * m_per_deg_lon,
         (p[1] - points[0][1]) * m_per_deg_lat,
         (p[3] - t0).total_seconds() * time_scale]
        for p in points
    ], dtype=float)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=2, min_samples=1,
                                cluster_selection_epsilon=float(eps_m),
                                metric="euclidean")
    labels = clusterer.fit_predict(matrix)

    groups: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(labels):
        if label >= 0:                      # -1 == noise
            groups[int(label)].append(idx)
    return [g for g in groups.values() if len(g) >= 2]


def detect_colocation(db: Session, case_id: str) -> list[Anomaly]:
    """Co-location detection whose WORDING matches the source's real precision.

    GPS data -> a distance claim. Cell-tower/CDR data -> "same or nearby
    serving cell", never a metre figure the source cannot support.
    """
    _clear_previous(db, case_id, "location")

    rels = (db.query(Relationship)
              .filter(Relationship.case_id == case_id,
                      Relationship.occurred_at.isnot(None))
              .all())

    gps_points = []
    tower_points = []
    for rel in rels:
        attrs = rel.attributes or {}
        if attrs.get("lat") is not None and attrs.get("lon") is not None:
            gps_points.append((rel, float(attrs["lat"]), float(attrs["lon"])))
        elif attrs.get("tower_id"):
            tower_points.append((rel, str(attrs["tower_id"])))

    found: list[Anomaly] = []
    window = timedelta(minutes=COLOCATION_WINDOW_MINUTES)

    # --- HDBSCAN density-based pass over GPS points (preferred) ---
    hd_points = [(rel, lat, lon, rel.occurred_at)
                 for rel, lat, lon in gps_points]
    for cluster in _hdbscan_clusters(hd_points, COLOCATION_RADIUS_M,
                                     COLOCATION_WINDOW_MINUTES):
        members = [hd_points[i] for i in cluster]
        actors = {str(m[0].source_id) for m in members}
        if len(actors) < 2:
            continue
        times = [m[3] for m in members]
        spread = max(
            _haversine_m(a[1], a[2], b[1], b[2])
            for a in members for b in members)

        anomaly = Anomaly(
            case_id=case_id, kind="location",
            title="Potential spatial-temporal rendezvous (density cluster)",
            description=(
                f"HDBSCAN identified a density cluster of {len(members)} "
                f"location records from {len(actors)} distinct entities, "
                f"spanning roughly {spread:.0f} m within "
                f"{(max(times) - min(times)).total_seconds() / 60:.0f} minutes "
                f"(GPS-precision source)."
            ),
            anomaly_confidence=round(min(0.6 + 0.05 * len(members), 0.9), 2),
            source_precision="gps",
            entity_ids=sorted(actors),
            evidence_ids=[str(m[0].evidence_id) for m in members if m[0].evidence_id],
            window_start=min(times), window_end=max(times),
            details={"cluster_size": len(members), "spread_m": round(spread, 1),
                     "method": "hdbscan"},
            detector_name="colocation_hdbscan",
            detector_version=DETECTOR_VERSION,
        )
        db.add(anomaly)
        found.append(anomaly)

    # --- Pairwise haversine sweep: fallback / corroboration ---
    for i in range(len(gps_points)):
        rel_a, lat_a, lon_a = gps_points[i]
        for j in range(i + 1, len(gps_points)):
            rel_b, lat_b, lon_b = gps_points[j]
            if rel_a.source_id == rel_b.source_id:
                continue
            if abs((rel_a.occurred_at - rel_b.occurred_at)) > window:
                continue
            dist = _haversine_m(lat_a, lon_a, lat_b, lon_b)
            if dist > COLOCATION_RADIUS_M:
                continue

            anomaly = Anomaly(
                case_id=case_id, kind="location",
                title="Potential spatial-temporal rendezvous",
                description=(
                    f"{_name(db, rel_a.source_id)} and "
                    f"{_name(db, rel_b.source_id)} were recorded within "
                    f"{dist:.0f} m of each other inside a "
                    f"{COLOCATION_WINDOW_MINUTES}-minute window "
                    f"(GPS-precision source)."
                ),
                anomaly_confidence=round(max(0.6, 0.95 - dist / 200), 2),
                source_precision="gps",
                entity_ids=[str(rel_a.source_id), str(rel_b.source_id)],
                evidence_ids=[str(r.evidence_id) for r in (rel_a, rel_b)
                              if r.evidence_id],
                window_start=min(rel_a.occurred_at, rel_b.occurred_at),
                window_end=max(rel_a.occurred_at, rel_b.occurred_at),
                details={"distance_m": round(dist, 1),
                         "window_minutes": COLOCATION_WINDOW_MINUTES},
                detector_name="colocation_gps",
                detector_version=DETECTOR_VERSION,
            )
            db.add(anomaly)
            found.append(anomaly)

    # --- Cell tower: NO metre claim, only "same or nearby serving cell" ---
    by_tower: dict[str, list] = defaultdict(list)
    for rel, tower in tower_points:
        by_tower[tower].append(rel)

    for tower, group in by_tower.items():
        group.sort(key=lambda r: r.occurred_at)
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.source_id == b.source_id:
                    continue
                if b.occurred_at - a.occurred_at > window:
                    break

                anomaly = Anomaly(
                    case_id=case_id, kind="location",
                    title="Devices on same serving cell in overlapping window",
                    description=(
                        f"{_name(db, a.source_id)} and {_name(db, b.source_id)} "
                        f"were associated with the same or a nearby serving cell "
                        f"({tower}) during an overlapping time window. "
                        f"Cell-tower data does not support a precise distance claim."
                    ),
                    anomaly_confidence=0.6,
                    source_precision="cell_tower",
                    entity_ids=[str(a.source_id), str(b.source_id)],
                    evidence_ids=[str(r.evidence_id) for r in (a, b) if r.evidence_id],
                    window_start=a.occurred_at, window_end=b.occurred_at,
                    details={"tower_id": tower,
                             "window_minutes": COLOCATION_WINDOW_MINUTES},
                    detector_name="colocation_cell",
                    detector_version=DETECTOR_VERSION,
                )
                db.add(anomaly)
                found.append(anomaly)

    db.commit()
    return found


def run_all_detectors(db: Session, case_id: str) -> dict:
    financial = detect_financial_structuring(db, case_id)
    temporal = detect_communication_burst(db, case_id)
    location = detect_colocation(db, case_id)
    return {"financial": len(financial), "temporal": len(temporal),
            "location": len(location),
            "total": len(financial) + len(temporal) + len(location)}
