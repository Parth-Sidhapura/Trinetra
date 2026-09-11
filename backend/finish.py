from app.db.session import SessionLocal
from app.services.resolution import build_candidates
from app.services.analytics import refresh_case_analytics
from app.services.anomalies import run_all_detectors
from app.services.honeytokens import seed_canaries

CASE = "727c4b97-876a-4e18-bf90-2b746d429d87"
db = SessionLocal()

c = build_candidates(db, CASE, use_semantic=True)
print("candidates:", len(c))
for x in c[:12]:
    print("   ", x.method, "|", round(x.resolution_confidence, 2), "|", x.reasoning[:95])

print("analytics:", refresh_case_analytics(db, CASE))
print("canaries:", seed_canaries(db, CASE))
print("anomalies:", run_all_detectors(db, CASE))
print("\nCASE READY:", CASE)
db.close()
