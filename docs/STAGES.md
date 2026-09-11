# Build stages — ALL DELIVERED

| Stage | Kya hai | Files |
|---|---|---|
| **1 — Foundation** | Config, full 18-table schema, JWT verify + RBAC/ABAC, case isolation, hash chain + Merkle, Fernet encryption + redaction policy, hash-chained audit log | `core/`, `db/`, `models/`, `services/audit.py` |
| **2 — Ingestion** | Upload, quarantine (MIME/magic/size/archive-bomb), local ClamAV over INSTREAM, SHA-256 chaining, Supabase Storage + local fallback, PDF/CSV/XLSX/audio parsers | `services/quarantine.py`, `storage.py`, `parsers.py`, `ingestion.py` |
| **3 — Extraction** | India regex (vehicle/phone/UPI/IFSC/Aadhaar/IMEI), spaCy NER, Gemini zero-shot Hindi/Hinglish, LLM provider abstraction (gemini/groq/ollama) covering chat + embeddings | `services/extractors.py`, `llm.py` |
| **4 — Resolution** | exact → rapidfuzz → jellyfish Metaphone → pgvector semantic, transliteration map, inline `urf`/उर्फ alias detection, human confirm/reject | `services/resolution.py`, `api/routes/resolution.py` |
| **5 — Graph** | Neo4j projection with FULL provenance, transactional outbox (idempotent on aggregate_id+version), Celery worker + beat, graph_version invalidation | `services/graph_sync.py`, `workers/` |
| **6 — Analytics** | NetworkX degree/betweenness/Louvain, capped + TTL-cached subgraphs, 6-component explainable priority score, Adamic-Adar link prediction | `services/analytics.py` |
| **7 — Anomalies** | Financial structuring, communication burst vs own baseline, co-location with **source-precision-aware wording** (GPS = metres, cell-tower = "same/nearby serving cell") | `services/anomalies.py` |
| **8 — Copilot** | Grounded Gemini Q&A, authz-BEFORE-retrieval, prompt-injection sanitisation, citation validation with hard block, INSUFFICIENT EVIDENCE state | `services/copilot.py` |
| **9 — Security** | SOC dashboard (real aggregations), rule-based event correlation, break-glass with mandatory justification, honeytokens, immutable append-only backup manifests | `api/routes/security.py`, `services/backup.py` |
| **10 — Output** | Investigation brief PDF, BSA §63 certificate DRAFT with non-admissibility disclaimer, air-gapped compose, Dockerfiles, Render blueprint | `services/reports.py`, `docker-compose.airgapped.yml` |
| **Frontend** | Login, case list, evidence ledger, resolution queue, Cytoscape graph explorer, entity panel with score breakdown, temporal filter, anomalies, leads panel, copilot chat, SOC dashboard | `frontend/app/`, `frontend/components/` |
| **Demo data** | Synthetic generator encoding every pattern the detectors are built to find | `data/generate_dataset.py`, `backend/seed_demo.py` |

## Graceful degradation

Har heavy dependency optional hai. Missing ho toh feature honestly degrade
hota hai, crash nahi karta:

| Missing | Behaviour |
|---|---|
| Neo4j | `NEO4J_ENABLED=false` — graph Postgres se serve hota hai |
| Redis/Celery | `CELERY_ENABLED=false` — FastAPI BackgroundTasks |
| ClamAV | validation-only, logged as `degraded` |
| faster-whisper | audio skip, baaki pipeline chalti hai |
| WeasyPrint | reports HTML mein aate hain |
| Gemini | Groq fallback, phir regex+spaCy only |
