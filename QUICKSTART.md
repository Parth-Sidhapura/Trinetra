# TRINETRA — Quickstart (COMPLETE BUILD)

Tumhara kaam: accounts banao, `.env` bharo, run karo.
Mera kaam: code.

**Poora system ban chuka hai** — ingestion, extraction, resolution, graph,
analytics, anomalies, copilot, security, reports, sab. Tumhe sirf accounts
banane hain, `.env` bharna hai, aur run karna hai.

---

## 0. Prerequisites

- Python 3.11 or 3.12  (3.13 pe kuch libs abhi flaky hain — 3.12 use karo)
- Node 20+
- Docker (optional, sirf local Postgres/Neo4j ke liye)

---

## 1. Accounts (~40 min, ye serial kaam hai — ek banda ye kare)

| Service | Kya chahiye | Kahan milega |
|---|---|---|
| **Supabase** | Project (region: **Mumbai/Singapore**) | supabase.com |
| **Neo4j AuraDB Free** | Instance + credentials file | neo4j.com/cloud/aura-free |
| **Upstash** | Redis database | upstash.com |
| **Google AI Studio** | Gemini API key | aistudio.google.com |
| **Groq** | Backup key | console.groq.com |
| **Render** | Account (deploy baad mein) | render.com |
| **Vercel** | Account | vercel.com |

### Supabase se ye 5 cheezein chahiye
1. **Settings → Database → Connection string → Transaction pooler** (port `6543`) → `DATABASE_URL`
2. **Settings → Database → Connection string → Direct** (port `5432`) → `DATABASE_DIRECT_URL`
3. **Settings → API → Project URL** → `SUPABASE_URL`
4. **Settings → API → service_role key** → `SUPABASE_SERVICE_KEY`
5. **Settings → API → JWT Secret** → `SUPABASE_JWT_SECRET`

### Supabase mein 3 cheezein karni hain
```sql
-- SQL Editor mein chalao:
CREATE EXTENSION IF NOT EXISTS vector;
```
- **Storage** → do buckets banao: `evidence` aur `evidence-backups`
- **Authentication → Users** → 3 test users banao (constable@demo.in,
  inspector@demo.in, admin@demo.in) — roles backend khud assign karega

### ⚠️ Neo4j AuraDB warning
Password **sirf ek baar** dikhta hai — credentials file turant download karo.
Free instance **72 ghante inactivity** ke baad auto-pause ho jaata hai.
Isliye `/health` endpoint Neo4j ko bhi ping karta hai (already coded).

---

## 2. Backend chalao (~10 min)

```bash
cd backend

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm

cp .env.example .env              # ab .env bharo (upar wali values)
```

**Encryption key generate karo** aur `.env` mein daalo:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Migration chalao:**
```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

**Demo data generate karo aur seed karo:**
```bash
python ../data/generate_dataset.py      # synthetic FIR/CDR/BANK/VEHICLE banata hai
python seed_demo.py                     # case banata hai + sab ingest karta hai
# LLM extraction ke saath (GEMINI_API_KEY chahiye):
# python seed_demo.py --llm
```

**Server start:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Celery worker (alag terminal — optional, background processing ke liye):**
```bash
celery -A app.workers.celery_app worker --beat --loglevel=info --concurrency=1
```
Agar Celery nahi chala rahe toh `.env` mein `CELERY_ENABLED=false` kar do —
processing FastAPI BackgroundTasks se ho jaayegi.

Check karo: http://localhost:8000/health
Expected: `{"api":"ok","postgres":"ok","neo4j":"ok","healthy":true}`

---

## 3. Frontend chalao (~5 min)

```bash
cd frontend
npm install
cp .env.local.example .env.local  # NEXT_PUBLIC_* values bharo
npm run dev
```

Kholo: http://localhost:3000
Teen green dots dikhne chahiye — API, Postgres, Neo4j.

**Agar red dikhe:** backend chal raha hai? CORS mein `http://localhost:3000`
allowed hai? `.env` ka `DATABASE_URL` sahi hai?

---

## 4. Local Postgres/Neo4j chahiye toh (optional)

```bash
docker compose up -d
```
Phir `.env` mein:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trinetra
DATABASE_DIRECT_URL=postgresql://postgres:postgres@localhost:5432/trinetra
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=trinetra123
REDIS_URL=redis://localhost:6379/0
```

---

## 5. Deploy (Day 1, hour 3 tak ye ho jaana chahiye)

### Backend → Render
- New **Web Service** → repo connect
- Root Directory: `backend`
- Build: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment: `.env` ki saari values daalo
- ⚠️ `$PORT` env var hi use karna — hardcoded port pe Render unhealthy mark karega

### Celery worker → Render (second **Web Service**, background worker nahi)
Render free tier pe Background Workers nahi milte. Isliye:
- Root Directory: `backend`
- Start: `celery -A app.workers.celery_app worker --loglevel=info --concurrency=1 & python -m http.server $PORT`
- (Stage 2 mein `app/workers/celery_app.py` aayega)

### Frontend → Vercel
- Root Directory: `frontend`
- Framework: Next.js (auto-detect)
- Env vars: `NEXT_PUBLIC_API_URL` (Render URL), `NEXT_PUBLIC_SUPABASE_URL`,
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- ⚠️ `NEXT_PUBLIC_*` build time pe bake hote hain — badloge toh **redeploy** karna padega

### Backend CORS update karo
Render pe `ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000`

### Keep-warm
cron-job.org → har 10 min → `https://your-backend.onrender.com/health`
(Ye Render aur Neo4j dono ko jaga rakhta hai.)

---

## Stage 1 done ka matlab

- [ ] `localhost:8000/health` → teeno green
- [ ] `localhost:3000` → teen green dots
- [ ] Login page se Supabase user sign-in ho raha hai
- [ ] Render pe backend deployed, `/health` green
- [ ] Vercel pe frontend deployed, deployed backend se baat kar raha hai

**Ye sab tick ho gaya? Mujhe batao — Stage 2 (upload + parsing + extraction
pipeline) bhej deta hoon.**

Koi error aaye toh poora traceback paste kar dena, fix karke dunga.


---

## 6. Demo script (13 steps)

1. Sign in → case list → "Operation Nexus" kholo
2. **Evidence tab** — 6 files uploaded dikhenge, sab hash-chained
3. **Resolution queue** — "Ramesh Kumar" ≟ "Ramesh Kr." dikhega reasoning ke saath → **Confirm merge** dabao
4. **Graph tab** — network render hoga, node size = centrality
5. Kisi node pe click → right panel mein **investigative priority** component breakdown ke saath
6. **Temporal filter** — datetime set karo, graph reshape hoga
7. **Anomalies tab** → "Run detectors" → financial structuring + communication burst + co-location
8. Dekho co-location wala "same or nearby serving cell" bolta hai, metre claim nahi — kyunki source cell-tower hai
9. **Investigative leads tab** → "Recompute predictions" → `Link Prediction Score: 0.78` + `Unverified Investigative Lead`
10. **Copilot tab** → pucho: *"Why is Ramesh Kumar connected to account 50100234567893?"* → cited answer
11. **Brief PDF** aur **BSA §63 draft** buttons — dono generate honge
12. Admin se role change karke Constable banao → Aadhaar `[REDACTED]` ho jaayega live
13. **Verify integrity** → hash chain VALID + merkle root + audit chain VALID

## 7. Role setup (redaction demo ke liye zaroori)

Pehla user jo sign-in karta hai wo automatically `CONSTABLE` banta hai.
Apne aap ko ADMIN banane ke liye Supabase SQL editor mein:

```sql
UPDATE user_profiles SET role = 'ADMIN', clearance = 'highly_restricted'
WHERE email = 'tumhara@email.com';
```

Uske baad UI se ya `/admin/users/role` se dusre users ke roles set kar sakte ho.

## 8. Kuch kaam nahi kar raha?

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: rapidfuzz` | `pip install -r requirements.txt` dobara chalao |
| spaCy model error | `python -m spacy download en_core_web_sm` |
| Neo4j connect nahi ho raha | `.env` mein `NEO4J_ENABLED=false` — app phir bhi chalega, graph Postgres se aayega |
| Celery/Redis error | `.env` mein `CELERY_ENABLED=false` |
| WeasyPrint install fail | Skip karo — reports HTML mein aayenge, PDF ki jagah |
| CORS error | Backend ke `ALLOWED_ORIGINS` mein frontend URL add karo |
| Alembic DDL error | Pooler nahi, `DATABASE_DIRECT_URL` (port 5432) use ho raha hai check karo |

**Har feature independently degrade hota hai** — Neo4j, Celery, ClamAV, Whisper,
WeasyPrint band ho toh bhi baaki system chalta rahega.


---

## 9. Optional heavy features

`requirements-heavy.txt` mein 4 optional cheezein hain. Inke bina bhi sab chalta
hai — feature honestly degrade hota hai, crash nahi karta.

```bash
pip install -r requirements-heavy.txt   # sirf agar RAM/disk headroom hai
```

| Package | Deta hai | Bina iske |
|---|---|---|
| `hdbscan` + `scikit-learn` | Density-based spatio-temporal clustering | Pairwise haversine sweep chalta hai |
| `faster-whisper` | Offline audio transcription | Audio skip, baaki pipeline chalti hai |
| `weasyprint` | Asli PDF reports | Reports HTML mein aate hain |

Semantic (pgvector) resolution ke liye `GEMINI_API_KEY` chahiye —
`python seed_demo.py --llm` chalao, embeddings backfill ho jaayenge.
