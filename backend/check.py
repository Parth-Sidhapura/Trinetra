from app.db.session import SessionLocal
from app.models import ResolutionCandidate, Observation
from app.services.resolution import build_candidates

CASE = "8592c128-5e30-47c0-baad-15452c6312b3"
db = SessionLocal()

rows = db.query(Observation).filter(
    Observation.entity_type.in_(["PERSON", "ORGANIZATION", "LOCATION"])).all()
names = sorted(set((o.entity_type, o.normalized_value) for o in rows))
print("=== EXTRACTED NAMES:", len(names))
for t, v in names:
    print("   ", t, "|", v)

db.query(ResolutionCandidate).delete()
db.commit()
c = build_candidates(db, CASE)
print("=== CANDIDATES:", len(c))
for x in c[:15]:
    print("   ", x.method, "|", round(x.resolution_confidence, 2), "|", x.reasoning[:100])
db.close()
