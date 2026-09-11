from app.db.session import SessionLocal
from app.models import ResolutionCandidate
from app.services.resolution import build_candidates

CASE = "727c4b97-876a-4e18-bf90-2b746d429d87"
db = SessionLocal()

db.query(ResolutionCandidate).delete()
db.commit()

c = build_candidates(db, CASE, use_semantic=True)
print("candidates:", len(c))
for x in sorted(c, key=lambda y: -y.resolution_confidence):
    print("   ", x.method, "|", round(x.resolution_confidence, 2), "|", x.reasoning[:95])
db.close()
