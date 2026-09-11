"""Structured entity extraction.

Vehicle plates, phone numbers, UPI IDs, IFSC codes and account numbers follow
fixed formats regardless of the surrounding language - so regex works on
Hindi, Hinglish and English narrative alike.
"""
import re
from dataclasses import dataclass, field

# --- India-specific patterns ---
PATTERNS: dict[str, re.Pattern] = {
    "VEHICLE": re.compile(r"\b[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b"),
    "PHONE": re.compile(r"(?:\+?91[\s-]?)?[6-9]\d{9}\b"),
    "UPI": re.compile(r"\b[\w.\-]{2,256}@(?:okaxis|oksbi|okhdfcbank|okicici|paytm|ybl|upi|apl|axl)\b", re.I),
    "IFSC": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    "ACCOUNT": re.compile(r"\b\d{11,18}\b"),
    "AADHAAR": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "FIR_NUMBER": re.compile(r"\b(?:FIR|एफआईआर)[\s.:#-]*(\d{1,5}\s*/\s*20\d{2})\b", re.I),
    "IMEI": re.compile(r"\b\d{15}\b"),
}

# Confidence by how forgeable/ambiguous the format is
CONFIDENCE = {
    "VEHICLE": 0.95, "PHONE": 0.92, "UPI": 0.97, "IFSC": 0.97,
    "ACCOUNT": 0.70, "AADHAAR": 0.85, "FIR_NUMBER": 0.90, "IMEI": 0.65,
}


@dataclass
class Extraction:
    entity_type: str
    raw_text: str
    normalized_value: str
    confidence: float
    method: str
    span: tuple[int, int] | None = None
    context: str = ""
    meta: dict = field(default_factory=dict)


def _normalize(entity_type: str, value: str) -> str:
    v = value.strip()
    if entity_type == "PHONE":
        digits = re.sub(r"\D", "", v)
        return digits[-10:]
    if entity_type in ("VEHICLE", "IFSC"):
        return re.sub(r"[\s-]", "", v).upper()
    if entity_type in ("AADHAAR", "ACCOUNT", "IMEI"):
        return re.sub(r"\D", "", v)
    if entity_type == "UPI":
        return v.lower()
    return v


def extract_by_regex(text: str) -> list[Extraction]:
    """Language-independent. Runs on Hindi, Hinglish, English identically."""
    out: list[Extraction] = []
    seen: set[tuple[str, str]] = set()

    for etype, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            raw = m.group(0)
            norm = _normalize(etype, raw)

            # Aadhaar and account both match 12-digit runs; prefer Aadhaar
            if etype == "ACCOUNT" and len(norm) == 12:
                continue
            if etype == "IMEI" and len(norm) != 15:
                continue

            key = (etype, norm)
            if key in seen:
                continue
            seen.add(key)

            start, end = m.span()
            out.append(Extraction(
                entity_type=etype,
                raw_text=raw,
                normalized_value=norm,
                confidence=CONFIDENCE.get(etype, 0.7),
                method="regex",
                span=(start, end),
                context=text[max(0, start - 60):min(len(text), end + 60)],
            ))
    return out


_NLP = None


def _get_spacy():
    global _NLP
    if _NLP is None:
        try:
            import spacy
            _NLP = spacy.load("en_core_web_sm")
        except Exception:  # noqa: BLE001
            _NLP = False   # mark as unavailable, don't retry every call
    return _NLP or None


SPACY_MAP = {"PERSON": "PERSON", "GPE": "LOCATION", "LOC": "LOCATION",
             "ORG": "ORGANIZATION", "FAC": "LOCATION"}


def extract_by_spacy(text: str) -> list[Extraction]:
    nlp = _get_spacy()
    if nlp is None:
        return []
    doc = nlp(text[:100_000])
    out: list[Extraction] = []
    seen: set[tuple[str, str]] = set()
    for ent in doc.ents:
        etype = SPACY_MAP.get(ent.label_)
        if not etype:
            continue
        norm = ent.text.strip()
        if len(norm) < 3:
            continue
        key = (etype, norm.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(Extraction(
            entity_type=etype, raw_text=ent.text, normalized_value=norm,
            confidence=0.75, method="spacy",
            span=(ent.start_char, ent.end_char),
            context=text[max(0, ent.start_char - 60):ent.end_char + 60],
            meta={"spacy_label": ent.label_},
        ))
    return out


PROMPT_VERSION = "extraction-v1"

GEMINI_SYSTEM = """You are an information extraction engine for Indian police FIR documents.
You extract entities from Hindi, Hinglish, and English text.
You NEVER infer, guess, or invent. You only extract what is literally written.
You always reply with a JSON array and nothing else."""

GEMINI_PROMPT = """Extract every named entity from the FIR text below.

Allowed entity_type values: PERSON, LOCATION, ORGANIZATION, PHONE, VEHICLE, ACCOUNT, UPI.

Rules:
- Extract names exactly as written (Devanagari stays Devanagari).
- If a person has an alias/nickname ("urf", "उर्फ"), emit BOTH as separate entries and link them via "alias_of".
- confidence: 0.0-1.0, how certain you are this is really that entity type.
- Do not extract anything not present in the text.

Reply ONLY with a JSON array of objects:
[{{"entity_type":"PERSON","raw_text":"...","normalized_value":"...","confidence":0.9,"alias_of":null}}]

FIR TEXT:
---
{text}
---"""


def extract_by_llm(text: str) -> list[Extraction]:
    """Zero-shot multilingual extraction for Hindi/Hinglish narrative text.

    This is a genuine working Indic capability - not a placeholder - but it is
    NOT parity with a trained Indic NER model (AI4Bharat). See README.
    """
    from app.services.llm import chat_json, LLMError, provider_info
    if not text.strip():
        return []
    try:
        data = chat_json(GEMINI_PROMPT.format(text=text[:12000]),
                         system=GEMINI_SYSTEM)
    except (LLMError, Exception):  # noqa: BLE001
        return []
    if not isinstance(data, list):
        return []

    info = provider_info()
    out: list[Extraction] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        etype = str(item.get("entity_type", "")).upper()
        raw = str(item.get("raw_text", "")).strip()
        if not etype or not raw:
            continue
        norm = str(item.get("normalized_value") or raw).strip()
        try:
            conf = float(item.get("confidence", 0.6))
        except (TypeError, ValueError):
            conf = 0.6
        out.append(Extraction(
            entity_type=etype, raw_text=raw,
            normalized_value=_normalize(etype, norm),
            confidence=min(max(conf, 0.0), 1.0), method="llm",
            meta={"alias_of": item.get("alias_of"),
                  "model": info["model"], "provider": info["provider"],
                  "prompt_version": PROMPT_VERSION},
        ))
    return out



_BAD_NAME = re.compile(r"(BNS|BNSS|IPC|CrPC)[\s.-]*\d", re.I)


def _plausible_name(value: str) -> bool:
    """Reject section numbers, sentences and identifiers wrongly typed as names."""
    v = (value or "").strip()
    if not (3 <= len(v) <= 40):
        return False
    if len(v.split()) > 4:
        return False
    if any(ch.isdigit() for ch in v):
        return False
    if _BAD_NAME.search(v):
        return False
    return True


def extract_all(text: str, *, use_llm: bool = True) -> list[Extraction]:
    """Regex first (highest precision), then spaCy, then LLM for narrative.
    Later methods never overwrite an earlier, higher-confidence hit."""
    results = extract_by_regex(text)
    known = {(e.entity_type, e.normalized_value.lower()) for e in results}

    for extraction in extract_by_spacy(text):
        key = (extraction.entity_type, extraction.normalized_value.lower())
        if key not in known:
            known.add(key)
            results.append(extraction)

    if use_llm:
        for extraction in extract_by_llm(text):
            if (extraction.entity_type in ("PERSON", "ORGANIZATION", "LOCATION")
                    and not _plausible_name(extraction.normalized_value)):
                continue
            key = (extraction.entity_type, extraction.normalized_value.lower())
            if key not in known:
                known.add(key)
                results.append(extraction)

    return results
