#!/usr/bin/env python3
"""One-command demo seeding.

Creates the demo case, uploads every synthetic file, runs extraction,
resolution, analytics and the anomaly detectors. After this the UI has a
complete, demo-ready case.

Usage:  cd backend && python seed_demo.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal          # noqa: E402
from app.models import Case, FIR                 # noqa: E402
from app.services import ingestion               # noqa: E402
from app.services.analytics import refresh_case_analytics  # noqa: E402
from app.services.anomalies import run_all_detectors       # noqa: E402
from app.services.resolution import build_candidates       # noqa: E402

DATA = Path(__file__).parent.parent / "data" / "synthetic"
ACTOR = "seed@trinetra.local"

FILES = ["FIR_0142_2026.pdf", "FIR_0142_2026.txt", "FIR_0187_2026.txt",
         "SURVEILLANCE_REPORT.txt", "CDR.csv", "BANK.csv",
         "VEHICLE.csv", "CRIMINAL_HISTORY.csv"]


def main(use_llm: bool = False):
    if not DATA.exists():
        print(f"✗ {DATA} not found. Run:  python ../data/generate_dataset.py")
        return 1

    db = SessionLocal()
    try:
        case = Case(
            title="Operation Nexus — cyber fraud network, South District",
            bnss_stage="under_investigation",
            data_classification="confidential",
            department="CYBER_CELL",
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        case_id = str(case.id)
        print(f"✓ Case created: {case_id}")

        for number, station, sections in (
            ("0142/2026", "Cyber Cell, South District",
             ["BNS-318", "BNS-317", "BNS-61"]),
            ("0187/2026", "Cyber Cell, South District",
             ["BNS-318", "BNS-61", "BNS-111"]),
        ):
            db.add(FIR(case_id=case_id, fir_number=number,
                       police_station=station, bns_sections=sections))
        db.commit()
        print("✓ 2 FIRs linked (BNS sections mapped)")

        uploaded = 0
        for name in FILES:
            path = DATA / name
            if not path.exists():
                continue
            # prefer the PDF over the txt twin
            if name.endswith(".txt") and (DATA / name.replace(".txt", ".pdf")).exists():
                continue
            try:
                ev = ingestion.store_evidence(
                    db, case_id=case_id, filename=name,
                    data=path.read_bytes(), uploaded_by=ACTOR)
                print(f"  → {name:26} seq {ev.sequence_number}  "
                      f"sha {ev.sha256[:12]}…")
                result = ingestion.process_evidence(db, str(ev.id), use_llm=use_llm)
                print(f"     extracted {result.get('observations', 0)} observations "
                      f"({result.get('kind')})")
                uploaded += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗ {name}: {exc}")

        print(f"✓ {uploaded} files ingested")

        chain = ingestion.verify_chain(db, case_id)
        print(f"✓ Hash chain: {'VALID' if chain['chain_valid'] else 'BROKEN'} "
              f"({chain['evidence_count']} records)")
        print(f"  merkle root {chain['merkle_root'][:32]}…")

        if use_llm:
            from app.services.resolution import backfill_embeddings
            n = backfill_embeddings(db, case_id)
            print(f"✓ {n} pgvector embeddings backfilled (semantic resolution)")

        cands = build_candidates(db, case_id, use_semantic=use_llm)
        print(f"✓ {len(cands)} resolution candidates proposed (awaiting human review)")
        for c in cands[:5]:
            print(f"    [{c.method}] {c.reasoning[:88]}")

        analytics = refresh_case_analytics(db, case_id)
        print(f"✓ Analytics: {analytics['nodes']} nodes / {analytics['edges']} edges "
              f"· {analytics['predicted_links']} predicted links")

        from app.services.honeytokens import seed_canaries
        planted = seed_canaries(db, case_id)
        print(f"✓ {planted} honeytoken canaries planted (demo environment only)")

        detected = run_all_detectors(db, case_id)
        print(f"✓ Anomalies: {detected['financial']} financial, "
              f"{detected['temporal']} time-based, {detected['location']} location")

        print(f"\n{'='*62}")
        print(f"Demo case ready:  {case_id}")
        print(f"Open the UI, sign in, and it will appear in your case list.")
        print(f"{'='*62}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    use_llm = "--llm" in sys.argv
    if use_llm:
        print("(LLM extraction enabled — needs GEMINI_API_KEY)\n")
    sys.exit(main(use_llm))
