"""Multi-stage entity resolution: exact -> fuzzy/phonetic -> semantic.

TRINETRA NEVER auto-merges. Every match is a proposal with a confidence
score and a human-readable reason. A human confirms.
"""
import logging
import re
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.models import Observation, ResolutionCandidate

log = logging.getLogger("trinetra.resolution")

RESOLVER_VERSION = "1.0"
RESOLVER_ALGORITHMS = {
    "exact": "exact_normalized_match",
    "fuzzy": "rapidfuzz_token_sort",
    "phonetic": "jellyfish_metaphone",
    "semantic": "pgvector_cosine_embedding",
}

# Common Indian transliteration variants
TRANSLIT = {
    "mohd": "mohammed", "mohammad": "mohammed", "muhammad": "mohammed",
    "md": "mohammed", "kr": "kumar", "kr.": "kumar", "sh": "singh",
    "shri": "", "smt": "", "mr": "", "mrs": "", "ms": "",
}
ALIAS_MARKERS = re.compile(r"\b(urf|उर्फ|alias|a\.k\.a\.?|aka)\b", re.I)

EXACT_THRESHOLD = 1.0
FUZZY_THRESHOLD = 0.82
PHONETIC_THRESHOLD = 0.75
SEMANTIC_THRESHOLD = 0.93


@dataclass
class Match:
    observation_a: str
    observation_b: str
    confidence: float
    method: str
    reasoning: str


def normalize_name(name: str) -> str:
    name = re.sub(r"[^\w\s]", " ", name.lower())
    tokens = [TRANSLIT.get(t, t) for t in name.split()]
    return " ".join(t for t in tokens if t).strip()


def phonetic_key(name: str) -> str:
    """Soundex/Metaphone family - spelling-insensitive name matching."""
    try:
        import jellyfish
        return " ".join(jellyfish.metaphone(t) for t in normalize_name(name).split())
    except Exception:  # noqa: BLE001
        return normalize_name(name)


def _fuzzy_score(a: str, b: str) -> float:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    return max(
        fuzz.token_sort_ratio(na, nb),
        fuzz.partial_ratio(na, nb) * 0.95,
    ) / 100.0


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def compare(obs_a: Observation, obs_b: Observation,
            *, use_semantic: bool = False) -> Match | None:
    """Run the resolution ladder. Returns the FIRST (highest-precision) hit."""
    if obs_a.entity_type != obs_b.entity_type:
        return None
    if obs_a.id == obs_b.id:
        return None

    a_val = (obs_a.normalized_value or obs_a.raw_text or "").strip()
    b_val = (obs_b.normalized_value or obs_b.raw_text or "").strip()
    if not a_val or not b_val:
        return None

    # --- Stage 1: exact ---
    if a_val.lower() == b_val.lower():
        if obs_a.entity_type not in ('PERSON','ORGANIZATION'):
            return None
        return Match(obs_a.id, obs_b.id, 0.99, "exact",
                     f"Identical normalized value: '{a_val}'")

    # Structured identifiers only ever match exactly - no fuzzy phone numbers.
    if obs_a.entity_type not in ("PERSON", "ORGANIZATION"):
        return None

    # --- Stage 2: fuzzy ---
    fuzzy = _fuzzy_score(a_val, b_val)
    if fuzzy >= FUZZY_THRESHOLD:
        return Match(obs_a.id, obs_b.id, round(fuzzy * 0.95, 3), "fuzzy",
                     f"Fuzzy name similarity {fuzzy:.0%} between "
                     f"'{a_val}' and '{b_val}' after transliteration normalisation")

    # --- Stage 2b: phonetic ---
    pa, pb = phonetic_key(a_val), phonetic_key(b_val)
    if pa and pa == pb:
        return Match(obs_a.id, obs_b.id, 0.84, "phonetic",
                     f"Phonetic match (Metaphone '{pa}') between "
                     f"'{a_val}' and '{b_val}' - common transliteration variant")

    phon = _fuzzy_score(pa, pb)
    if phon >= PHONETIC_THRESHOLD and fuzzy >= 0.6:
        return Match(obs_a.id, obs_b.id, round(phon * 0.85, 3), "phonetic",
                     f"Phonetic similarity {phon:.0%} with name similarity "
                     f"{fuzzy:.0%} between '{a_val}' and '{b_val}'")

    # --- Stage 3: semantic (pgvector embeddings) ---
    if use_semantic:
        vec_a = obs_a.embedding if obs_a.embedding is not None else None
        vec_b = obs_b.embedding if obs_b.embedding is not None else None
        if vec_a is None or vec_b is None:
            from app.services.llm import embed
            vec_a = vec_a if vec_a is not None else embed(a_val)
            vec_b = vec_b if vec_b is not None else embed(b_val)
        sim = _cosine(
            list(vec_a) if vec_a is not None else [],
            list(vec_b) if vec_b is not None else [],
        )
        if sim >= SEMANTIC_THRESHOLD:
            return Match(obs_a.id, obs_b.id, round(sim * 0.80, 3), "semantic",
                         f"Semantic embedding similarity {sim:.0%} between "
                         f"'{a_val}' and '{b_val}' (pgvector cosine)")
    return None


def backfill_embeddings(db: Session, case_id: str, limit: int = 500) -> int:
    """Populate the pgvector column so semantic search runs in Postgres
    instead of recomputing embeddings on every comparison."""
    from app.services.llm import embed

    rows = (db.query(Observation)
              .filter(Observation.case_id == case_id,
                      Observation.embedding.is_(None),
                      Observation.entity_type.in_(
                          ["PERSON", "ORGANIZATION"]))
              .limit(limit).all())
    done = 0
    for obs in rows:
        value = obs.normalized_value or obs.raw_text
        if not value:
            continue
        vec = embed(value)
        if vec:
            obs.embedding = vec
            done += 1
    db.commit()
    log.info("Backfilled %s embeddings for case %s", done, case_id)
    return done


def semantic_neighbours(db: Session, case_id: str, observation_id: str,
                        top_k: int = 5) -> list[tuple[Observation, float]]:
    """Nearest neighbours via the pgvector IVFFlat index (cosine distance)."""
    anchor = db.query(Observation).filter(Observation.id == observation_id).first()
    if anchor is None or anchor.embedding is None:
        return []
    rows = (db.query(Observation,
                     Observation.embedding.cosine_distance(anchor.embedding)
                     .label("distance"))
              .filter(Observation.case_id == case_id,
                      Observation.id != observation_id,
                      Observation.embedding.isnot(None),
                      Observation.entity_type == anchor.entity_type)
              .order_by("distance").limit(top_k).all())
    return [(row[0], 1.0 - float(row[1])) for row in rows]


def detect_inline_aliases(text: str) -> list[tuple[str, str]]:
    """Catch 'Ramesh Kumar urf Kalia' inside the narrative itself."""
    pairs: list[tuple[str, str]] = []
    for m in ALIAS_MARKERS.finditer(text or ""):
        before = text[max(0, m.start() - 40):m.start()].strip().split("\n")[-1]
        after = text[m.end():m.end() + 40].strip().split("\n")[0]
        left = " ".join(before.split()[-3:])
        right = " ".join(after.split()[:3])
        if left and right:
            pairs.append((left.strip(" ,.:;"), right.strip(" ,.:;")))
    return pairs


def build_candidates(db: Session, case_id: str,
                     *, use_semantic: bool = False,
                     max_pairs: int = 4000) -> list[ResolutionCandidate]:
    """Compare observations pairwise within a case and store proposals.

    Capped at max_pairs so a big CDR import can't blow up free-tier memory.
    """
    observations = (
        db.query(Observation)
        .filter(Observation.case_id == case_id,
                Observation.entity_type.in_(
                    ["PERSON", "ORGANIZATION"]))
        .all()
    )

    existing = {
        (c.entity_a_observation_id, c.entity_b_observation_id)
        for c in db.query(ResolutionCandidate)
                   .filter(ResolutionCandidate.case_id == case_id).all()
    }

    created: list[ResolutionCandidate] = []
    compared = 0

    by_type: dict[str, list[Observation]] = {}
    for obs in observations:
        by_type.setdefault(obs.entity_type, []).append(obs)

    for etype, group in by_type.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if compared >= max_pairs:
                    log.warning("Resolution pair cap (%s) reached for case %s",
                                max_pairs, case_id)
                    break
                compared += 1
                a, b = group[i], group[j]
                if (a.id, b.id) in existing or (b.id, a.id) in existing:
                    continue
                match = compare(a, b, use_semantic=use_semantic)
                if match is None:
                    continue
                candidate = ResolutionCandidate(
                    case_id=case_id,
                    entity_a_observation_id=match.observation_a,
                    entity_b_observation_id=match.observation_b,
                    resolution_confidence=match.confidence,
                    method=match.method,
                    algorithm_name=RESOLVER_ALGORITHMS.get(match.method, match.method),
                    algorithm_version=RESOLVER_VERSION,
                    reasoning=match.reasoning,
                    status="pending",
                )
                db.add(candidate)
                created.append(candidate)

    db.commit()
    log.info("Case %s: compared %s pairs, proposed %s merges",
             case_id, compared, len(created))
    return created
