import io, ast
p = "app/services/extractors.py"
s = io.open(p, encoding="utf-8").read()

guard = '''
_BAD_NAME = re.compile(r"(BNS|BNSS|IPC|CrPC)[\\s.-]*\\d", re.I)


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


'''

anchor = "def extract_all("
if "_plausible_name" not in s:
    s = s.replace(anchor, guard + anchor)

old = """    if use_llm:
        for extraction in extract_by_llm(text):
            key = (extraction.entity_type, extraction.normalized_value.lower())
            if key not in known:"""
new = """    if use_llm:
        for extraction in extract_by_llm(text):
            if (extraction.entity_type in ("PERSON", "ORGANIZATION", "LOCATION")
                    and not _plausible_name(extraction.normalized_value)):
                continue
            key = (extraction.entity_type, extraction.normalized_value.lower())
            if key not in known:"""

if old in s:
    s = s.replace(old, new)
    io.open(p, "w", encoding="utf-8").write(s)
    ast.parse(s)
    print("FILTER ADDED OK")
else:
    print("anchor not found - skip, not critical")
