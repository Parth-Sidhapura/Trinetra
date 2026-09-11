#!/usr/bin/env python3
"""Load the synthetic demo case folders straight into TRINETRA.

Same path the UI upload takes — store_evidence() hash-chains the file, then
process_evidence() parses and extracts. Nothing is bypassed, so the chain,
the audit log and the observations all come out exactly as they would if you
had clicked upload twenty-one times.

Usage, from the backend folder with the venv active:

    python load_cases.py "C:\\Users\\HP\\Downloads\\cases"

Add --no-llm to skip Gemini (much faster, but far fewer PERSON names, so the
review queue will be almost empty).
"""
import argparse
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal                        # noqa: E402
from app.models import Case, FIR                               # noqa: E402
from app.services import ingestion                             # noqa: E402
from app.services.analytics import refresh_case_analytics      # noqa: E402
from app.services.anomalies import run_all_detectors           # noqa: E402
from app.services.resolution import build_candidates           # noqa: E402

ACTOR = "demo-loader@trinetra.local"

# folder name -> (case title, bnss stage, classification)
CASES = {
    "01_Operation_Silk_Route": (
        "Operation Silk Route — hawala remittance channel, West Zone Mumbai",
        "under_investigation", "confidential"),
    "02_Operation_Chakravyuh": (
        "Operation Chakravyuh — vehicle theft and re-stamping, NCR to Rajasthan",
        "under_investigation", "confidential"),
    "03_Operation_Kavach": (
        "Operation Kavach — fake recruitment call centre targeting women, North District",
        "fir_registered", "restricted"),
}

STATION = {
    "01_Operation_Silk_Route": "Economic Offences Wing, West Zone, Mumbai",
    "02_Operation_Chakravyuh": "Crime Branch, Gurugram, Haryana",
    "03_Operation_Kavach": "Cyber Cell, North District, New Delhi",
}

SECTIONS = {
    "01_Operation_Silk_Route": ["BNS-318", "BNS-61"],
    "02_Operation_Chakravyuh": ["BNS-303", "BNS-317", "BNS-336", "BNS-61"],
    "03_Operation_Kavach": ["BNS-318", "BNS-336", "BNS-61"],
}

# FIR first so it takes sequence number 1 in the chain, then the rest
ORDER = [".pdf", ".txt", ".csv", ".xlsx"]


def sort_key(p: Path):
    fir = 0 if p.name.upper().startswith("FIR_") else 1
    try:
        ext = ORDER.index(p.suffix.lower())
    except ValueError:
        ext = len(ORDER)
    return (fir, ext, p.name)


def fir_number_from(name: str) -> str | None:
    """FIR_0311_2026.pdf -> 0311/2026"""
    stem = Path(name).stem
    parts = stem.split("_")
    if len(parts) >= 3 and parts[0].upper() == "FIR":
        return f"{parts[1]}/{parts[2]}"
    return None


def load_folder(db, folder: Path, use_llm: bool) -> bool:
    key = folder.name
    if key not in CASES:
        print(f"  skipping {key} — not one of the three demo folders")
        return False

    title, stage, classification = CASES[key]

    existing = db.query(Case).filter(Case.title == title).first()
    if existing:
        print(f"  already loaded as case {str(existing.id)[:8]} — skipping.")
        print("  (delete that case first if you want to load it again)")
        return False

    case = Case(title=title, bnss_stage=stage,
                data_classification=classification, department="CYBER_CELL")
    db.add(case)
    db.commit()
    db.refresh(case)
    case_id = str(case.id)
    print(f"  case created  {case_id}")

    files = sorted([p for p in folder.iterdir()
                    if p.is_file() and p.suffix.lower() in ORDER],
                   key=sort_key)

    for path in files:
        num = fir_number_from(path.name)
        if num:
            db.add(FIR(case_id=case_id, fir_number=num,
                       police_station=STATION[key], bns_sections=SECTIONS[key]))
            db.commit()
            print(f"  FIR linked    {num}")

        try:
            ev = ingestion.store_evidence(db, case_id=case_id,
                                          filename=path.name,
                                          data=path.read_bytes(),
                                          uploaded_by=ACTOR)
            res = ingestion.process_evidence(db, str(ev.id), use_llm=use_llm)
            print(f"  ingested      seq {ev.sequence_number:<2} {path.name:<34} "
                  f"{res.get('observations', 0):>4} observations ({res.get('kind')})")
        except Exception as exc:                                  # noqa: BLE001
            print(f"  FAILED        {path.name}: {exc}")

    chain = ingestion.verify_chain(db, case_id)
    print(f"  hash chain    {'VALID' if chain['chain_valid'] else 'BROKEN'} "
          f"({chain['evidence_count']} records)")

    if use_llm:
        try:
            from app.services.resolution import backfill_embeddings
            n = backfill_embeddings(db, case_id)
            print(f"  embeddings    {n} backfilled")
        except Exception as exc:                                  # noqa: BLE001
            print(f"  embeddings    skipped ({exc})")

    cands = build_candidates(db, case_id, use_semantic=use_llm)
    print(f"  review queue  {len(cands)} candidates awaiting a human decision")

    stats = refresh_case_analytics(db, case_id)
    print(f"  graph         {stats['nodes']} nodes / {stats['edges']} edges "
          f"· {stats['predicted_links']} predicted links")

    try:
        from app.services.honeytokens import seed_canaries
        print(f"  honeytokens   {seed_canaries(db, case_id)} canaries planted")
    except Exception:                                             # noqa: BLE001
        pass

    found = run_all_detectors(db, case_id)
    print(f"  anomalies     {found['financial']} financial, "
          f"{found['temporal']} time-based, {found['location']} location")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="folder containing the 01_/02_/03_ case folders")
    ap.add_argument("--no-llm", action="store_true",
                    help="skip Gemini extraction (fast, but few PERSON names)")
    args = ap.parse_args()

    root = Path(args.path).expanduser()
    if not root.exists():
        print(f"Path not found: {root}")
        return 1

    # tolerate being pointed at the zip's parent, or at 'cases' itself
    folders = sorted([p for p in root.iterdir() if p.is_dir()
                      and p.name in CASES])
    if not folders:
        inner = root / "cases"
        if inner.is_dir():
            folders = sorted([p for p in inner.iterdir() if p.is_dir()
                              and p.name in CASES])

    if not folders:
        print(f"No case folders found under {root}")
        print("Expected folders named 01_Operation_Silk_Route etc.")
        return 1

    use_llm = not args.no_llm
    print(f"Loading {len(folders)} case(s) from {root}")
    print(f"Gemini extraction: {'on' if use_llm else 'off'}\n")

    db = SessionLocal()
    loaded = 0
    try:
        for folder in folders:
            print(f"[{folder.name}]")
            try:
                if load_folder(db, folder, use_llm):
                    loaded += 1
            except Exception:                                     # noqa: BLE001
                db.rollback()
                print("  ERROR loading this case:")
                traceback.print_exc()
            print()
    finally:
        db.close()

    print("=" * 66)
    print(f"{loaded} case(s) loaded. Refresh the dashboard in your browser.")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
