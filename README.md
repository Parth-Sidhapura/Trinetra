# TRINETRA

![Status](https://img.shields.io/badge/status-in--development-orange)
![License](https://img.shields.io/badge/license-MIT-blue)
![Stack](https://img.shields.io/badge/stack-Next.js%20%7C%20FastAPI%20%7C%20Neo4j%20%7C%20Supabase-informational)
![Hosting](https://img.shields.io/badge/hosting-free%2Fdev--tier-lightgrey)

**Smart India Hackathon 2026 · Problem Statement 26189**
Ministry of Home Affairs · National Crime Records Bureau (NCRB), Women Safety Division
Category: Software · Theme: Blockchain & Cybersecurity

> An investigation platform that turns fragmented FIRs, call records, bank transactions and vehicle logs into one explainable knowledge graph — surfacing who is connected to whom, why, and how confident the system is, without the AI ever declaring guilt on its own.

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [What We're Building](#what-were-building)
3. [Core Differentiators](#core-differentiators)
4. [Feature Modules](#feature-modules)
5. [Tech Stack](#tech-stack)
6. [System Architecture](#system-architecture)
7. [Indic\-Aware Extraction Strategy](#indic-aware-extraction-strategy)
8. [Performance & Reliability Safeguards](#performance-reliability-safeguards)
9. [Advanced Intelligence Layer](#advanced-intelligence-layer)
10. [Data Model](#data-model)
11. [Data & Knowledge Architecture](#data-knowledge-architecture)
12. [Repository Structure](#repository-structure)
13. [Getting Started (Local Development)](#getting-started-local-development)
14. [Environment Variables](#environment-variables)
15. [Deployment Guide (Free Tier, Step by Step)](#deployment-guide-free-tier-step-by-step)
16. [Air\-Gapped / On\-Premise Deployment](#air-gapped-on-premise-deployment-production-path)
17. [5\-Day Build Roadmap](#5-day-build-roadmap)
18. [The Demo](#the-demo)
19. [Responsible AI & Guardrails](#responsible-ai-guardrails)
20. [Security Model](#security-model)
21. [Legal & Forensic Compliance](#legal-forensic-compliance)
22. [Known Limitations & Non\-Goals](#known-limitations-non-goals)
23. [Beyond the Hackathon (Phase 2 Roadmap)](#beyond-the-hackathon-phase-2-roadmap)
24. [Team](#team)
25. [License](#license)

## Problem Statement

**PS ID 26189 — AI\-Powered Criminal Network Analysis System**

Modern criminal activity is organized and interconnected — associates, intermediaries, financial channels, communication links, locations and events all form a network. Law enforcement already collects large volumes of relevant data (FIRs, Call Detail Records, financial transaction records, surveillance reports, social media intelligence, criminal history databases, intelligence reports) but that data is **fragmented, unstructured, and spread across systems**. Manual analysis is slow and easily misses connections.

The ask: an AI system that automatically analyzes structured and unstructured crime\-related data to uncover hidden relationships, identify key influencers within a network, detect suspicious patterns, and hand investigators **actionable, visual, explainable intelligence** — while remaining an assistant to the investigator, never an autonomous judge.

## What We're Building

TRINETRA ingests raw case files (PDF FIRs, CSV/XLSX call and bank records, vehicle logs, surveillance reports, and criminal\-history records), extracts entities and relationships with NLP, resolves duplicate/aliased identities with a confidence\-scored matching pipeline, stores the result as a real knowledge graph, and gives investigators:

- A **graph explorer** to visually trace how people, phones, accounts, vehicles and locations connect
- **Investigative priority scoring** (centrality \+ cross\-case \+ evidence strength) to triage attention, never guilt
- **Temporal filtering** — replay the network as it looked before an incident
- **Anomaly detection** across three canonical types: financial (structuring), time\-based (communication bursts), and location (repeated co\-location)
- An **AI copilot** that answers natural\-language questions with cited, evidence\-grounded answers — never invented ones
- A **tamper\-evident evidence chain** (SHA\-256 hash chaining) that lets an investigator verify nothing was altered after upload

## Core Differentiators

1. Multi\-source criminal network reconstruction from heterogeneous file types
2. Multi\-stage entity resolution (exact → fuzzy/phonetic → semantic) with human\-in\-the\-loop confirmation
3. A real knowledge graph (Neo4j), not a static diagram
4. Temporal network analysis — the graph changes with the timeline
5. Cross\-source anomaly detection (financial \+ communication \+ location)
6. Explainable AI — every score and alert shows its reasoning and its evidence
7. Evidence provenance and tamper\-evident integrity verification
8. Human\-in\-the\-loop by design — the system proposes, the investigator decides
9. Fully deployable on free\-tier infrastructure — nothing here requires a budget
10. Built and demoed as one continuous investigation, not a feature tour

## Feature Modules

| Module | MVP (built for the hackathon) | Stretch (if time allows) |
| --- | --- | --- |
| Case & FIR workspace | ✅ | — |
| Data ingestion (PDF/CSV/XLSX) | ✅ FIRs, CDR, bank, vehicle logs, surveillance reports (PDF/text), criminal\-history records (CSV) | Video, XML |
| Entity extraction | ✅ spaCy (English) \+ India\-specific regex (vehicle plates, phone numbers, UPI, IFSC) \+ Gemini zero\-shot extraction for Hindi/Hinglish text | Dedicated trained Indic NER (AI4Bharat), OCR for scanned Devanagari FIRs |
| Local audio transcription | ✅ faster\-whisper (Hindi/Hinglish), feeds the same NER pipeline | Speaker diarization |
| Observation → Canonical entity pipeline | ✅ raw observations never overwritten; resolution candidates require human confirmation | — |
| Entity resolution | ✅ exact \+ fuzzy/phonetic (Soundex/Metaphone tuned for Indian names) \+ semantic (embeddings) | Contextual correlation scoring |
| Relationship lifecycle states | ✅ SOURCE\_OBSERVED → PROPOSED → HUMAN\_CONFIRMED/REJECTED, no hard deletes | SUPERSEDED/EXPIRED automation |
| Knowledge graph explorer | ✅ | — |
| End\-to\-end intelligence lineage | ✅ every score traces back to source evidence | "Trace this" UI action on every element |
| Predictive link discovery | ✅ Adamic\-Adar index (NetworkX), shown as a score \+ lead status, never a probability | Node2Vec embedding similarity |
| Temporal intelligence | ✅ | — |
| Anomaly detection | ✅ 3 rule\-based detectors \+ source\-precision\-aware HDBSCAN spatio\-temporal clustering | ML\-based detectors |
| Investigative priority score | ✅ explained, component\-level breakdown, capped/cached and graph\-version\-invalidated | — |
| AI investigator copilot | ✅ grounded Q&A, authz\-before\-retrieval, "insufficient evidence" state | Full RAG legal knowledge base |
| Map intelligence | ✅ co\-location view | Radius/proximity search |
| Evidence vault \+ hash chain \+ Merkle proof | ✅ | Classification/retention policy engine |
| Immutable evidence backup | ✅ scheduled append\-only manifest export to a separate storage location, never overwritten | Full offline vault \+ verified secondary replica |
| Secure evidence quarantine | ✅ MIME/extension/size validation \+ local ClamAV scan | Sandboxed detonation |
| BSA Section 63 certificate generator | ✅ draft PDF with hash ledger \+ explicit non\-admissibility disclaimer | Digital signature integration |
| RBAC (roles) | ✅ 3 roles, server\-enforced | Full ABAC |
| Data classification & clearance | ✅ classification enum \+ clearance\-based ABAC check | — |
| Case isolation guarantee | ✅ enforced across DB, graph, search, AI, and reports | — |
| Break\-glass access | ✅ lightweight: reason \+ time\-boxed token \+ mandatory audit review | Full approval workflow |
| Field\-level redaction \+ encryption | ✅ Aadhaar/phone/bank/address masked by role and encrypted at rest | Full ABAC field policies |
| Tamper\-evident audit log | ✅ hash\-chained, same pattern as evidence | — |
| Security Operations Center dashboard | ✅ live counts from audit/security\-event log | Full SIEM\-style timeline |
| Security event correlation | ✅ rule\-based, backed by session/device metadata | ML\-based scoring |
| Honeytoken canaries (demo\-only) | ✅ | — |
| Continuous security validation | ✅ Semgrep/Bandit/pip\-audit/Trivy/ZAP in CI \+ manual Kali Linux validation lab | Full third\-party pentest |
| Transactional outbox sync | ✅ Postgres → Neo4j via Redis/Celery worker, idempotent and graph\-versioned | Full event\-sourcing / CDC |
| Investigation brief (PDF export) | ✅ | — |
| Air\-gapped deployment | ✅ one\-command Docker Compose variant (local LLM, local DB, local audio pipeline) | Full on\-prem hardening, network segmentation |

## Tech Stack

The hosted demonstration is designed to run on currently available free/developer\-tier infrastructure, while the production architecture is designed for controlled on\-premise or air\-gapped deployment. The stack below ships in two deployment modes: a **Hosted Demo Instance** (optimized for a judge to click a live URL) and a fully **Air\-Gapped Variant** (see [Air\-Gapped / On\-Premise Deployment](#air-gapped-on-premise-deployment-production-path)). Presenting both is deliberate — it shows the hosted stack is a demo convenience, not a claim that this is production\-deployment\-ready as\-is; a real production deployment would need to meet whatever data\-classification, security, procurement, hosting, and data\-residency requirements actually apply, which the public hosted instance sidesteps entirely by using only synthetic demonstration data.

| Layer | Technology | Free tier |
| --- | --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui | Deployed on **Vercel** (Hobby, free forever) |
| Backend API | Python, FastAPI, Pydantic v2 | Deployed on **Render** (free web service, 750 hrs/mo) |
| Security gateway | `slowapi` rate limiting \+ strict Pydantic request validation \+ security headers, inside FastAPI | Free — no separate WAF service needed for the MVP |
| Edge WAF (optional upgrade) | Cloudflare free plan | Free, but needs a custom or free subdomain pointed at the backend — not required for judging |
| Relational database | PostgreSQL \+ pgvector | **Supabase** free tier (500MB DB) — air\-gapped variant runs the same schema on local Postgres |
| Auth | Supabase Auth (JWT, row\-level security) | Included in Supabase free tier |
| File / evidence storage | Supabase Storage | 1GB free |
| Graph database | **Neo4j AuraDB Free** | Permanent free instance (200k nodes / 400k relationships) |
| Graph analytics | NetworkX (in\-process, Python) | Free — capped and cached, see [Performance & Reliability Safeguards](#performance-reliability-safeguards) |
| Predictive link analytics | NetworkX Adamic\-Adar index; Node2Vec embeddings (stretch) | Free |
| Async task queue | Celery \+ Redis (**Upstash** free tier — serverless, doesn't sleep) | Free — powers the transactional outbox sync, audio transcription, and clustering jobs |
| NLP / NER | spaCy (English) \+ India\-specific regex (vehicle plates, phone formats, UPI, IFSC) \+ Gemini zero\-shot extraction for Hindi/Hinglish text | Free — see [Indic\-Aware Extraction Strategy](#indic-aware-extraction-strategy) |
| Speech\-to\-text | `faster-whisper` (quantized, CPU\-friendly) | Free, runs fully offline |
| Entity resolution | rapidfuzz, jellyfish (Soundex/Metaphone phonetic matching), Gemini embeddings \+ pgvector | Free |
| Spatio\-temporal clustering | `hdbscan` \+ shapely/GeoPandas | Free |
| Field\-level encryption | `cryptography` (Fernet), key from platform\-managed encrypted env vars | Free |
| Malware scanning | **ClamAV**, local and self\-hosted in the backend/worker | Free — evidence never leaves the deployment boundary, hosted or air\-gapped alike (see Performance & Reliability Safeguards for its RAM footprint) |
| LLM copilot | Google Gemini 2.0/2.5 Flash (Google AI Studio) | Free tier; Groq (Llama 3.3 70B) as a free backup key; local Ollama (Llama 3) in the air\-gapped variant |
| Graph visualization | Cytoscape.js | Free, open source |
| Map | MapLibre GL JS \+ OpenFreeMap tiles | Free, no API key ever |
| Charts | Recharts | Free |
| PDF report \+ legal certificate generation | WeasyPrint (self\-hosted in backend) | Free |
| CI \+ security scanning | GitHub Actions running Semgrep, Bandit, pip\-audit, Trivy, and an OWASP ZAP baseline scan | Free minutes |
| Uptime / keep\-warm | cron\-job.org | Free — pings Render so it's awake for judging |
| Security validation lab | Kali Linux (VM or live image), used externally against the team's own deployed demo | Free — not part of the application stack, see Security Model |

## System Architecture

```
Investigator (browser)
        │
        ▼
Next.js frontend (Vercel)          ← Cloudflare free plan optional, with a custom domain
        │  HTTPS
        ▼
FastAPI backend (Render)
        │  rate limiting (slowapi) + input validation + security headers
        ├─► Supabase Postgres   (system of record + outbox table)
        ├─► Supabase Auth       (JWT, RBAC + field-level redaction/encryption)
        ├─► Supabase Storage    (evidence files, written only after quarantine)
        ├─► Gemini API          (NLP assist, embeddings, copilot)
        └─► Redis (Upstash)     (task queue)
                     │
                     ▼
              Celery worker
                     ├─ Transactional outbox sync   → Neo4j AuraDB (relationship graph)
                     ├─ Local audio transcription    → faster-whisper → NER pipeline
                     ├─ Predictive link scoring       → NetworkX Adamic-Adar / Node2Vec
                     └─ Spatio-temporal clustering    → HDBSCAN (rendezvous detection)

NetworkX also runs centrality and community detection directly against subgraphs
pulled from Neo4j on demand — see Performance & Reliability Safeguards.
```

**Why an outbox, not a direct dual write.** Writing to Postgres and Neo4j in the same request risks silent drift if the second write fails after the first succeeds. Instead, every state change commits an `outbox_events` row in the *same* Postgres transaction as the primary write; a Celery worker polls that table and applies the change to Neo4j **idempotently**, keyed on `aggregate_id` \+ `aggregate_version` so retries and out\-of\-order delivery never duplicate an edge, and retrying on failure while marking the event processed only once it succeeds. Postgres stays the single source of truth even if Neo4j is briefly unreachable — the graph is always eventually consistent, never silently wrong. Each applied change also increments that case's `graph_version`; cached analytics are keyed on `case_id + graph_version + analytics_version`, so a stale score is invalidated rather than silently shown — see Data & Knowledge Architecture.

**Async ingestion pipeline:**

```
Upload file
   → quarantine + MIME/extension/size validation + local ClamAV malware scan
   → hash (SHA-256, chained + Merkle-proofed against previous evidence)
   → store in Supabase Storage, metadata in Postgres
   → parse (PDF/CSV/XLSX) or transcribe (faster-whisper, for audio)
   → spaCy NER + regex extraction + Gemini zero-shot extraction (Hindi/Hinglish)
   → entity resolution (exact → fuzzy/phonetic → semantic embedding)
   → write observation + resolution candidate + outbox event to Postgres (one transaction)
   → Celery worker applies the outbox event to Neo4j (idempotent, version-checked)
   → analytics refresh (NetworkX centrality/community/link-prediction, on next graph read)
```

## Indic\-Aware Extraction Strategy

Most real FIRs are written in Hindi, Hinglish, or a regional script — a plain English spaCy model alone cannot parse that, and pretending otherwise would be exactly the kind of gap a defense\-track judge is listening for. TRINETRA handles this at two levels rather than deferring it entirely to a "Phase 2 stretch goal":

- **Structured entity formats are language\-independent.** Vehicle registrations, phone numbers, UPI IDs, IFSC codes and account numbers follow fixed patterns regardless of the surrounding language, so a regex layer tuned to Indian formats extracts them reliably from any narrative: vehicle plates as `^[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,3}[-\s]?\d{4}$` (`MH12AB1234`), phone numbers as `(\+91[-\s]?)?[6-9]\d{9}`, and UPI IDs as `[\w.\-]{2,256}@[a-zA-Z]{2,64}`.
- **Name matching is phonetic, not spelling\-exact.** Entity resolution runs Soundex/Metaphone\-family phonetic matching (via `jellyfish`) alongside `rapidfuzz` edit\-distance matching, tuned against common Indian transliteration variants ("Mohd"/"Mohammed", "Kumar"/"Kr."), so "Ramesh Kumar" and "Ramesh Kr" resolve as the same person.
- **Hindi/Hinglish narrative text uses Gemini as a zero\-shot multilingual extractor.** Rather than train a dedicated Indic NER model in five days, FIR narrative text is sent to Gemini (already in the stack, free, and natively multilingual across Devanagari and Hinglish) with a structured\-JSON extraction prompt — a genuine, working Indic\-language capability for the MVP, not a placeholder.

What this MVP does **not** claim: OCR on scanned/handwritten Devanagari FIRs, or parity with a dedicated trained Indic NER model (AI4Bharat) on noisy, production\-scale real\-world text. That stays explicit Phase 2 scope — see [Beyond the Hackathon](#beyond-the-hackathon-phase-2-roadmap).

## Performance & Reliability Safeguards

Render's free tier caps the backend at roughly 512MB RAM — running NetworkX centrality/community detection over an uncapped graph (a realistic CDR file alone can produce tens of thousands of call edges) risks an out\-of\-memory crash mid\-demo. Three safeguards prevent that in front of a judge:

- **Bounded analytics scope.** Graph analytics run over a capped subgraph — a k\-hop neighborhood around the entities in view, or the most recent/relevant N edges — never the full unbounded graph in one pass.
- **Precomputed \+ cached results.** Centrality and community\-detection scores for the demo dataset are computed once and cached (in\-memory, TTL\-based, keyed by graph version) — a live judge interaction reads cached scores instead of triggering a fresh full computation.
- **A capped, realistic demo dataset.** The synthetic CDR/bank/vehicle files are sized to resemble a real single\-case dataset (hundreds to low thousands of edges), not an unrealistic full\-district dump — credible in scale, safely within free\-tier memory on every run.

### Data Management at Scale

Securing the data and managing it as it grows are two different problems, and the schema is built so growth doesn't force a rewrite:

- **Migrations.** Every schema change goes through Alembic, versioned and applied automatically on deploy — the schema's history is as auditable as the data it holds.
- **Indexing.** Every foreign key that's actually queried is indexed — `case_id` on every case\-scoped table, `entity_id` on relationships and criminal\_history, a GIN index on `entities.attributes` (jsonb) for attribute lookups, and an IVFFlat/HNSW index on the pgvector embedding column so semantic entity\-resolution search stays fast as the entity count grows.
- **Connection pooling.** FastAPI's async connection pool runs through Supabase's built\-in pooler (transaction\-mode PgBouncer), so a burst of concurrent requests doesn't exhaust the free tier's connection limit.
- **Scoped queries, always.** Every query is filtered by `case_id` first — the same case\-isolation boundary from the Security Model doubles as the cheapest possible query\-performance discipline: no query ever scans across cases it doesn't need to.
- **Retention is schema\-ready, not yet automated.** `cases.bnss_stage` already marks a case `disposed`; archiving disposed cases to cheaper storage or a read\-only partition is a config/cron change on top of that field, not a schema change — deliberately deferred to Phase 2 because free\-tier scale doesn't need it yet, not because the data model can't support it.

At hackathon scale — a handful of synthetic cases, low thousands of rows — this is comfortably inside Supabase's free 500MB. The honest scaling story for a real deployment is partitioning/archival by case status, Postgres read replicas, and periodic Neo4j graph pruning by case age — all Phase 2, and all things the current schema was designed not to fight against later.

## Advanced Intelligence Layer

Three capabilities that move TRINETRA from "shows the network that exists" to "helps an investigator find what's missing" — each grounded, explainable, and clearly labeled as a lead rather than a finding.

### Predictive Link Discovery

Beyond visualizing observed relationships, TRINETRA scores **unobserved but statistically likely** connections using NetworkX's built\-in Adamic\-Adar index (entities that share many mutual connections are more likely to be linked), with Node2Vec embedding similarity as a stretch enhancement for deeper structural prediction. An Adamic\-Adar score is a similarity measure, **not a calibrated probability** — so it is never phrased as a percentage likelihood. The correct framing:

```
Link Prediction Score: 0.78
Method: Adamic-Adar
Status: Unverified Investigative Lead
Evidence: None currently supports this relationship.
```

This never appears in an evidence\-linked report; it lives in a separate investigative\-leads panel, clearly separated from confirmed relationships.

### Local Audio Intelligence

Wiretap/interception audio is transcribed entirely offline via `faster-whisper` (a quantized, CPU\-friendly reimplementation of OpenAI Whisper) — handling Hindi, Hinglish, and code\-switched regional speech without a single byte leaving the deployment. The transcript feeds straight into the same NER/entity\-resolution pipeline used for text documents, so a phone number or name mentioned in a wiretap links into the same graph as one mentioned in an FIR. The hosted demo instance runs this against short clips with a small quantized model; the air\-gapped variant runs it at full capacity with zero cloud dependency — a direct answer to the "no external API for sensitive data" requirement.

### Spatio\-Temporal Rendezvous Detection

Rather than a simple "same location" rule, co\-location detection runs `HDBSCAN` density\-based clustering over location data — but the wording it uses depends on what the source data can actually support. Where genuinely precise coordinates are available (GPS\-level location data), the system may describe a **potential spatial\-temporal rendezvous** at a stated distance and time window — e.g. two devices within roughly 50 meters inside a 15\-minute window. Cell\-tower/CDR data does not offer that precision, so for tower\-derived location the system instead says devices were **associated with the same or a nearby serving cell during an overlapping time window** — never implying GPS\-level precision the source doesn't have. The UI surfaces which precision tier a given flag is based on. Flagged exactly like every other anomaly: pattern, entities, time window, confidence, source precision, and the evidence it's grounded in — "potential rendezvous," never "proof of meeting."

## Data Model

**Postgres (system of record)**

| Table | Key fields |
| --- | --- |
| `cases` | id, title, status, bnss\_stage (enum: `fir_registered`, `under_investigation`, `chargesheet_filed`, `trial`, `disposed`), data\_classification (enum: `public`, `internal`, `confidential`, `restricted`, `highly_restricted`), created\_at |
| `firs` | id, case\_id, fir\_number, police\_station, date\_registered, bns\_sections (text\[\] — e.g. `BNS-103`, `BNS-316`), complainant\_ref |
| `observations` | id, source\_document\_id, page\_number, text\_span, raw\_text, entity\_type, extraction\_confidence, extraction\_method, created\_at — **never overwritten** |
| `resolution_candidates` | entity\_a\_observation\_id, entity\_b\_observation\_id, resolution\_confidence, method, status (pending/confirmed/rejected) |
| `entities` | id (canonical), type, name, aliases\[\], attributes (jsonb), source\_observation\_ids\[\] |
| `criminal_history` | id, entity\_id, case\_ref, offense\_type, date, source\_document\_id — prior\-offense records linked to a canonical entity, ingested the same way as any other structured file |
| `relationships` | id, source\_id, target\_id, type, relationship\_confidence, status (`source_observed` / `inferred` / `proposed` / `human_confirmed` / `disputed` / `rejected` / `superseded` / `expired`), evidence\_id, occurred\_at, occurred\_from, occurred\_to, observed\_at, verified\_by, verified\_at |
| `provenance` | provenance\_id, source\_type, source\_id, document\_id, case\_id, page\_number, row\_number, text\_span, source\_timestamp, extraction\_method, confidence, created\_at |
| `evidence` | id, case\_id, file\_uri, sha256, sequence\_number, prev\_chain\_hash, chain\_hash, merkle\_leaf\_hash, uploaded\_at, uploaded\_by |
| `evidence_backup_manifests` | id, sequence\_number, manifest\_hash, storage\_uri, created\_at — append\-only export of the hash chain \+ audit log, written to separate storage, never overwritten |
| `outbox_events` | id, aggregate\_type, aggregate\_id, aggregate\_version, event\_type, payload (jsonb), status (pending/processed/failed), retry\_count, created\_at, processed\_at |
| `case_graph_state` | case\_id, graph\_version, analytics\_version, updated\_at — increments whenever an outbox event changes that case's graph; cached analytics are keyed on `case_id + graph_version + analytics_version` and invalidated when it changes |
| `sessions` | session\_id, user\_id, device\_id, ip\_address, user\_agent, created\_at, last\_seen, expires\_at — backs security event correlation |
| `break_glass_requests` | id, user\_id, case\_id, reason, granted\_at, expires\_at, reviewed\_by, reviewed\_at |
| `audit_log` | id, actor, action, resource, case\_id, trace\_id, result, event\_hash, previous\_event\_hash, sequence\_number, timestamp — append\-only, hash\-chained |

Mapping to BNS (Bharatiya Nyaya Sanhita, 2023) offense sections and BNSS (Bharatiya Nagarik Suraksha Sanhita) case\-progression stages — rather than only free\-text case descriptions — is what lets the investigation brief speak the same language as an actual chargesheet, and it's a detail evaluators from a legal/procedural background specifically check for. See [Data & Knowledge Architecture](#data-knowledge-architecture) for why observations, resolution candidates, and canonical entities are kept as separate tables rather than one mutable `entities` row.

**Neo4j (relationship graph)**

```cypher
(:Person)-[:USED {relationship_id, provenance_id, status, confidence_type, occurred_at, occurred_from, occurred_to, observed_at, graph_version}]->(:Phone)
(:Person)-[:OWNS {relationship_id, status, graph_version}]->(:Vehicle)
(:Person)-[:SENT_MONEY {relationship_id, amount, occurred_at, status, graph_version}]->(:BankAccount)
(:Person)-[:MENTIONED_IN]->(:FIR {fir_number, bns_sections, bnss_stage})
(:Person)-[:ASSOCIATED_WITH {relationship_id, confidence, confidence_type, evidence_id, status, graph_version}]->(:Person)
(:Person)-[:CO_LOCATED {relationship_id, occurred_at, status, graph_version}]->(:Location)
```

The graph projection intentionally carries more than `confidence + evidence_id` — every relationship keeps enough provenance (`relationship_id`, `provenance_id`, `graph_version`) to trace straight back to its authoritative Postgres record and, from there, to the original evidence. Neo4j is a queryable projection of the truth, never a lossier copy of it.

## Data & Knowledge Architecture

The rules below are what keep TRINETRA's output explainable rather than a black box — they cost nothing beyond careful schema design, and they're the difference between "the AI said so" and "here's exactly how the system got here."

### Observation → Resolution → Canonical Entity

TRINETRA never directly converts extracted text into a confirmed identity. Raw text stays a raw `observation` (exactly what a document said, where) forever — it is never edited or overwritten. A `resolution_candidate` is the system's hypothesis that two observations refer to the same person, carrying its own confidence and reasoning. Only after a human confirms it does a `canonical` entity exist. This means TRINETRA can always answer three separate questions: what the source stated, what the AI inferred, and what the investigator confirmed — never collapsing the three into one.

### Confirmed Knowledge vs. Investigative Leads

Two logically separate layers. **Confirmed knowledge** is observations, investigator\-verified relationships, and evidence\-backed facts — what renders in the main graph and in any exported report. **Investigative leads** is predictive links, statistical associations, and AI\-generated suggestions — rendered in a clearly separate panel, with no evidence field populated, status `UNVERIFIED LEAD`. A lead never silently becomes a confirmed relationship; a human has to promote it, and that promotion is itself an audited action.

### Confidence Is Not One Number

A single generic `confidence` field would blur five different things: **extraction confidence** (did we read the entity correctly), **resolution confidence** (are these two observations the same person), **relationship confidence** (is this connection correctly represented), **anomaly confidence** (does this pattern match the detector's definition), and **prediction score** (a statistical guess at an unobserved link). Keeping them distinct is what lets the UI say *why* a number is what it is — and none of the five is ever described as a probability of guilt.

### Temporal Precision

One `timestamp` isn't enough for investigative data. TRINETRA distinguishes `occurred_at` (when the event actually happened), `observed_at` (when it was captured in a source document), and `ingested_at` (when TRINETRA processed it) — and where the exact moment is uncertain, an `occurred_from`/`occurred_to` range instead of a false\-precision single timestamp. This is what makes the temporal slider trustworthy rather than misleading.

### Explainable Investigative Priority

A priority score is never shown as a bare number. It's always the component breakdown:

```
INVESTIGATIVE PRIORITY: 86

Cross-Case Association        91
Evidence Confidence           93
Temporal Correlation          88
Network Centrality            82
Communication Activity        79
Financial Connectivity        74
```

Each component is clickable through to the relationships and evidence behind it. The label stays **investigative priority** or **high\-influence entity** — never "kingpin" — because centrality is an analytical property, not proof of criminal leadership.

### Source of Truth

No analytical store is allowed to silently become authoritative:

| Store | Owns |
| --- | --- |
| PostgreSQL | Canonical operational data — cases, entities, evidence metadata, relationships, investigative decisions, audit, workflow state |
| Neo4j | Relationship\-analytics projection (eventually consistent via the outbox) |
| pgvector | Semantic retrieval (embeddings) |
| Supabase Storage | Original evidence files |
| Redis (Upstash) | Transient queues/cache only — never a system of record |

### Immutable Original Evidence

The uploaded original is hashed and stored once, then never touched again. OCR output, NER extractions, embeddings, and entity\-resolution results are all **derived** data — they can be regenerated and reprocessed as the pipeline improves without ever touching the original file or its hash. This keeps a clean line between *original evidence* and *analytical interpretation* of it.

### AI & Algorithm Version Provenance

Every AI\-derived result stores `model_name`, `model_version`, `algorithm_name`/`version`, and `prompt_version` alongside it. If an entity\-resolution match or an anomaly flag is questioned later, TRINETRA can say exactly which model and which threshold produced it — reproducibility, not just a black\-box score.

### End\-to\-End Intelligence Lineage

Every finding TRINETRA surfaces can be walked backward through the exact same chain it was built forward through:

```
Evidence (FIR.pdf)
   ↓
Observation
   ↓
Resolution Candidate → Canonical Entity
   ↓
Relationship (status-tracked)
   ↓
Graph Analytics (versioned)
   ↓
Anomaly / Investigative Priority / Predictive Lead
   ↓
Investigator Finding
```

This lineage is the single strongest sentence in the pitch: *"click any score on screen, and it traces back through the graph, through the relationship, through the entity resolution, to the exact page of the exact document it came from."* Make it visible in the UI — a "trace this" action on every score, alert, and graph edge — not just true in the schema.

## Repository Structure

```
trinetra/
├── frontend/                # Next.js app
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── services/            # API client
│   └── stores/               # Zustand state
│
├── backend/                 # FastAPI app
│   ├── app/
│   │   ├── api/              # route handlers
│   │   ├── core/             # config, security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # NLP, resolution, graph, anomaly, copilot
│   │   └── workers/          # async job handlers
│   └── migrations/           # Alembic
│
├── graph/
│   ├── queries/               # Cypher
│   └── analytics/             # NetworkX pipelines
│
├── data/
│   └── synthetic/             # synthetic FIR/CDR/bank/vehicle demo dataset
│
├── docs/
│   └── architecture/
│
├── docker-compose.yml         # local dev only (Postgres + Neo4j emulation)
├── .env.example
└── README.md
```

## Getting Started (Local Development)

```bash
# 1. Clone
git clone https://github.com/<your-org>/trinetra.git
cd trinetra

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in your keys — see below
alembic upgrade head
uvicorn app.main:app --reload

# 3. Frontend (new terminal)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Local development connects straight to your free\-tier Supabase and Neo4j Aura instances — there's no need to run Postgres or Neo4j in Docker locally unless you want a fully offline dev loop.

## Environment Variables

**`backend/.env`**

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | Supabase Postgres connection string |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | Supabase project credentials |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j AuraDB Free credentials |
| `GEMINI_API_KEY` | Google AI Studio key (NLP assist, embeddings, copilot) |
| `GROQ_API_KEY` | Backup LLM key |
| `REDIS_URL` | Upstash Redis connection string (Celery broker for the outbox, audio, and clustering workers) |
| `WHISPER_MODEL_SIZE` | `faster-whisper` model size to load (e.g. `tiny`, `base`) |
| `ENCRYPTION_KEY` | Fernet key for field\-level encryption of sensitive attributes |
| `SUPABASE_JWT_SECRET` | Verifies Supabase\-**issued** JWTs — Supabase is the token issuer; the backend verifies incoming tokens, it does not sign a second, separate token |
| `JWT_ISSUER` / `JWT_AUDIENCE` | Expected issuer/audience claims checked during verification |

**`frontend/.env.local`**

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Deployed backend URL |
| `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase client keys |

Never commit `.env` files — `.gitignore` already excludes them.

## Deployment Guide (Free Tier, Step by Step)

The steps below stand up the **Hosted Demo Instance** — the fastest path to a live URL a judge can click, and the version to actually demo on stage. It is explicitly a demo convenience, not a claim that public SaaS is where this would run in production; see [Air\-Gapped / On\-Premise Deployment](#air-gapped-on-premise-deployment-production-path) directly below for the offline\-capable path that answers that concern.

1. **Supabase** — create a project at supabase.com → note the DB URL and API keys → run the Alembic migrations against it → enable Row\-Level Security policies for the 3 roles.
2. **Neo4j AuraDB Free** — create a free instance at neo4j.com/cloud/aura\-free → download the credentials file immediately (the password is shown only once) → note the connection URI.
3. **Upstash Redis** — create a free database at upstash.com → note the connection string — this is the Celery broker for the transactional outbox, audio transcription, and clustering workers.
4. **Google AI Studio** — generate a free Gemini API key at aistudio.google.com. Generate a free Groq key at console.groq.com as a backup.
5. **Backend → Render** — connect the GitHub repo, create a free Web Service pointed at `/backend`, set the environment variables above, deploy.
6. **Frontend → Vercel** — connect the same GitHub repo, set the root to `/frontend`, add the environment variables, deploy. Vercel gives you a free `.vercel.app` URL immediately and a preview deploy on every push.
7. **Keep\-warm** — register the Render backend URL's health\-check endpoint at cron\-job.org on a 10\-minute schedule so it's never asleep when a judge opens the link.
8. **Smoke test** — walk through the full demo script below against the live deployed URL, not localhost, before submission.

## Air\-Gapped / On\-Premise Deployment (Production Path)

A real production deployment would need to meet whatever government data\-classification, security, procurement, hosting, and data\-residency requirements actually apply to an NCRB\-facing system — requirements the public Hosted Demo Instance sidesteps entirely by using only synthetic data. TRINETRA's air\-gapped variant is the answer to that constraint: it swaps every cloud dependency for a local equivalent and, once provisioned, runs entirely inside one `docker-compose.yml` with no ongoing internet access:

```yaml
services:
  postgres:
    image: postgres:16
  neo4j:
    image: neo4j:5-community
  ollama:
    image: ollama/ollama
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://postgres:5432/trinetra
      - NEO4J_URI=bolt://neo4j:7687
      - LLM_PROVIDER=ollama          # swaps Gemini/Groq for local Ollama
      - LLM_BASE_URL=http://ollama:11434
  frontend:
    build: ./frontend
```

An air\-gapped machine can't `docker pull` anything, so these images and the Ollama model are never fetched from inside the air\-gapped environment itself — they're pulled, scanned, and verified on a connected staging machine first, then carried across on approved media:

```
CONNECTED STAGING ENVIRONMENT
        ↓
Pull + scan + verify container images and model artifacts
        ↓
Sign artifacts (SHA-256 + signature)
        ↓
Approved removable media
        ↓
AIR-GAPPED ENVIRONMENT
        ↓
Verify hash + signature, import verified images
        ↓
Run completely offline
```

The application code targets an `LLM_PROVIDER` interface (`gemini` / `groq` / `ollama`) covering LLM, NER, *and* embeddings — not just chat — rather than calling any one vendor's SDK directly, so switching from the Hosted Demo Instance to the air\-gapped variant is a config change, not a rewrite. Frame this in the pitch as: *"what you're watching live today is the hosted demo instance — here is the one\-command, fully offline deployment we built alongside it, because we designed for the real deployment constraint from day one rather than bolting it on after."*

### Offline Model & Image Supply Chain

The same discipline applies to container images as to AI models: on an internet\-connected staging machine, download the image or model, generate its SHA\-256, sign the artifact (`gpg --sign`, free), then transfer via approved media. On the offline machine: verify the hash, verify the signature, and only install if both check out — otherwise quarantine it. This is a procedure the team documents and rehearses for five days, not a fully automated pipeline; treating both AI models and container images as a supply chain that needs the same integrity discipline as evidence is the differentiator worth stating out loud in the pitch.

## 5\-Day Build Roadmap

| Day | Focus |
| --- | --- |
| **1 — Foundation** | All free accounts created (including Upstash Redis); repo \+ FastAPI \+ Next.js skeletons; Supabase schema \+ Neo4j Aura connected; skeleton frontend and backend deployed end\-to\-end. Prove the whole chain connects before building features on top of it. |
| **2 — Ingestion \+ NLP \+ resolution** | Upload pipeline, synthetic dataset (two cross\-linked FIRs \+ CDR \+ bank \+ vehicle files \+ one criminal\-history CSV \+ one surveillance\-report PDF, plus one short wiretap audio clip), spaCy/regex/Gemini extraction, entity resolution stages 1–2 with a review queue. |
| **3 — Graph \+ analytics \+ map \+ timeline** | Neo4j sync via a first pass of the transactional outbox worker, NetworkX centrality/community detection, `/graph` API, Cytoscape explorer, MapLibre co\-location view, temporal filter. |
| **4 — Anomaly \+ AI copilot \+ resilience \+ compliance** | Rule\-based detectors \+ HDBSCAN spatio\-temporal clustering, Gemini\-grounded copilot, semantic entity resolution, evidence hash chain \+ verify endpoint, field\-level redaction \+ server\-enforced roles, audit logging, transactional outbox hardened (Redis/Celery), Adamic\-Adar predictive link scoring. |
| **5 — Reports \+ audio \+ polish \+ rehearsal** | PDF investigation brief \+ BSA Section 63 certificate generator, faster\-whisper audio pipeline wired into ingestion, UI polish and guardrail copy, keep\-warm pinger live, backup demo recording, pitch deck, two timed dry runs. |

See [Advanced Intelligence Layer](#advanced-intelligence-layer) for the priority order to build the Day 4–5 additions in if time runs short.

## The Demo

One continuous, synthetic investigation — never a feature tour. The full script below runs roughly 9–10 minutes; if your slot is shorter, cut step 9 (audio) first, then step 8 (predictive link) — everything else is the core story and should stay.

1. Upload `FIR.pdf`, `CDR.csv`, `BANK.csv`, `VEHICLE.xlsx`, `CRIMINAL_HISTORY.csv`, `SURVEILLANCE.pdf` — async processing visible on screen.
2. NER extracts people, aliases, phones, vehicles, accounts, locations across both linked FIRs.
3. Entity resolution proposes **"Ramesh" / "Ramesh Kumar" / "Kalia"** as one person, with a confidence score and its reasoning (alias, phonetic match, shared phone/vehicle/case). The investigator confirms the merge — nothing is auto\-merged.
4. The graph renders. Click on Person A.
5. Entity page shows connections, cases, phones, vehicles, accounts, locations, and an **investigative priority** score — explicitly not a guilt score.
6. Drag the temporal slider — the graph reshapes to the network as it looked immediately before the incident.
7. An anomaly alert fires — "potential financial structuring" — with transactions, amounts, time window, accounts, and evidence IDs, all clickable back to source. A second alert shows a **spatio\-temporal rendezvous**\: two devices co\-located within 50m for 15 minutes if the source is GPS\-precise, or "same serving cell, overlapping time window" if it's cell\-tower data — the wording always matches the source's actual precision.
8. Open the **investigative leads** panel — predictive link discovery shows a `Link Prediction Score: 0.78` (Adamic\-Adar) flagging an unverified potential connection between Suspect A and Mule B, clearly labeled as a lead with no supporting evidence yet, never phrased as a percentage likelihood.
9. Play a short wiretap audio clip — it transcribes live (Hindi/Hinglish) and a new phone number surfaces in the graph, extracted straight from the transcript.
10. Ask the AI copilot: *"Why is Person A connected to Account B?"* — it answers with a cited evidence path.
11. Generate the investigation brief, then generate the **BSA Section 63 Evidence Certificate draft** — one click, a PDF with the hash ledger and chain\-verification result, carrying its own disclaimer that it assists the prescribed certification process rather than establishing legal admissibility on its own.
12. Switch the logged\-in role from Constable to Inspector — an Aadhaar field goes from `[Aadhaar Redacted]` to fully visible, live, in front of the jury.
13. Click **Verify Integrity** — hash valid, chain valid, Merkle proof valid, no unexpected modification detected. Close with: *"Every finding here is explainable and traceable back to its source — the AI assists the investigator, it never replaces their judgment."*

## Responsible AI & Guardrails

These rules are enforced in the UI copy and the pipeline logic, not just stated in a slide:

- Centrality is never labeled "kingpin" — it's shown as **investigative priority** or **high\-influence entity**, always broken into its component scores (see [Data & Knowledge Architecture](#data-knowledge-architecture)).
- Anomalies are never described as proof — always **"potential suspicious pattern"** or **"investigative lead."**
- A link\-prediction score (Adamic\-Adar / Node2Vec) is a similarity measure, not a calibrated probability — it is shown as a score (e.g. `0.78`) and a status (`Unverified Investigative Lead`), never phrased as a percentage likelihood.
- The LLM never invents evidence — every copilot answer is grounded in retrieved graph data and evidence, with citations.
- Authorization happens **before** retrieval, not after — the copilot's query planner only ever runs against data the requesting user is already permitted to see; the LLM never decides access.
- When the retrieved evidence doesn't support the claim being asked about, the copilot returns **"INSUFFICIENT EVIDENCE"** and states what's missing, instead of speculating to complete an answer.
- Every citation in a copilot response is validated against the retrieved evidence set before being shown — a response citing something that doesn't exist is blocked, not displayed.
- The LLM never auto\-merges identities — every entity resolution match is proposed with a confidence score and requires human confirmation.
- Predicted links are never written into the confirmed relationship graph or an evidence\-linked report — they live in a separate investigative\-leads panel until a human verifies them against real evidence.
- A generated BSA Section 63 certificate assists the certification process; it never claims to establish legal admissibility on its own.
- Every relationship and score carries provenance back to its source evidence.

## Security Model

The story here isn't "we use JWT." It's five pillars: zero\-trust access, cryptographically verifiable evidence, defense\-in\-depth around the AI, redundant/tamper\-evident logging, and continuous external validation of the platform's own defenses — demonstrated on the Hosted Demo Instance, designed to run identically air\-gapped.

```
TRINETRA
 ├─ ZERO-TRUST ACCESS       identity · RBAC/ABAC · clearance · case/field/action authorization · session security
 ├─ SECURITY GATEWAY        HTTPS · rate limiting · input validation · security headers · WAF (optional)
 ├─ EVIDENCE INTEGRITY      SHA-256 · hash chain · Merkle tree · quarantine · local malware scan
 ├─ SECURITY MONITORING     tamper-evident audit log · event correlation · risk scoring · Security Center
 └─ AIR-GAPPED MODE         local DB · local graph · local storage · local LLM · offline model verification
```

### Zero\-Trust Request Pipeline

Every request is evaluated down this chain, not just checked for a valid login:

```
IDENTITY               ✅ Supabase Auth (JWT)
CASE AUTHORIZATION     ✅ Postgres RLS scoped by case/department
FIELD AUTHORIZATION    ✅ field-level redaction/encryption policy
ACTION AUTHORIZATION   ✅ per-route, server-side permission checks
DATA ACCESS            ✅ response never contains unauthorized data
───────────────────────────────────────────────────
DEVICE TRUST           ⏳ Phase 2 — needs managed-device attestation
NETWORK TRUST          ⏳ Phase 2 — the air-gapped variant's isolated
                            network *is* the practical version of this
```

Being explicit about which layers are real today and which are the honest target is itself part of the pitch — it reads as engineering maturity, not a gap.

### RBAC \+ ABAC \+ Risk\-Based Policy

Authorization is policy, not a hardcoded `if role == "admin"`\:

```
IF   role = CONSTABLE
AND  case.department = user.department
AND  resource.classification <= user.clearance
THEN ALLOW
ELSE DENY + AUDIT
```

### Security Operations Center

A dedicated dashboard, backed by real aggregation queries over `audit_log` and the security\-event table — not a static mockup:

```
SECURITY STATUS
───────────────────────────
API Threat Level          LOW
Failed Logins             3
Blocked Requests          17
Evidence Integrity        VALID
Audit Chain                VALID
```

This is what makes the cybersecurity story visible to a judge instead of asserted in a slide.

### Security Event Correlation

Backed by a `sessions` table (session\_id, user\_id, device\_id, ip\_address, user\_agent, created\_at, last\_seen, expires\_at), one more rule\-based detector is built the same way as the financial/communication/location anomaly detectors: a failed login, from a new `device_id` or unusual `ip_address`, followed by a bulk evidence download, raises a risk score and triggers re\-authentication, session invalidation, and a security alert — explainable heuristics grounded in real session data, not a claimed ML/SIEM system.

### Tamper\-Evident Audit Log

The audit log isn't just `actor | action | timestamp`. Every event carries `event_hash` and `previous_event_hash`, chained exactly like evidence — altering a past entry breaks every hash after it, and `AUDIT INTEGRITY: VALID` is a real, independently verifiable check, not a claim.

### Evidence Integrity: Hash Chain \+ Merkle Tree

On top of the linear SHA\-256 chain, evidence hashes are also assembled into a Merkle tree, so a single evidence record's integrity can be proven (a Merkle proof) without re\-verifying the entire chain:

```
             Merkle Root
              /       \
            H12       H34
           /   \     /   \
         H1    H2   H3    H4
         │     │    │     │
         E1    E2   E3    E4
```

Hashing and chaining establish **integrity and provenance**, not legal admissibility on their own — the pitch should never overstate this; see Legal & Forensic Compliance for what Section 63 actually requires.

### Why a Hash Chain, Not a Distributed Ledger

Given the hackathon theme is Blockchain & Cybersecurity, this is worth saying out loud rather than leaving implicit: TRINETRA deliberately builds a hash\-chained, Merkle\-proofed evidence ledger — not a multi\-node distributed ledger with consensus. A single organization's evidence chain doesn't need Byzantine fault tolerance or a token economy; it needs exactly the properties blockchain popularized — append\-only, tamper\-evident, independently verifiable — without the operational cost of running a peer\-to\-peer network. Every evidence record's hash is chained to the one before it and rolled into a Merkle tree, so altering any past record breaks a check any investigator, auditor, or judge can run themselves. That is the blockchain concept applied at the scale this problem actually needs, not a checkbox blockchain bolted on for the theme name.

### Immutable Evidence Backup

On top of the hash chain, a scheduled Celery beat job (hourly on the Hosted Demo Instance; on every evidence write in the air\-gapped variant) exports a signed manifest of the evidence hash chain and the audit log to a **separate** storage location — a second Supabase Storage bucket for the hosted demo, a separate disk/volume for air\-gapped. Manifests are named by sequence number and their own hash and are **never overwritten or deleted**, only appended to, so even if the primary database were compromised, a verifier can compare the live chain against the last exported manifest and see exactly where the two diverge. This isn't a full offline vault or a verified secondary database replica — that's real infrastructure work and stays honestly scoped to Phase 2 (see Known Limitations) — but it is a genuine, working, append\-only backup of the one thing that actually needs to survive a compromise: proof of what the evidence chain looked like at each point in time.

### Field\-Level Encryption & Redaction

Redaction (display\-time masking, see Legal & Forensic Compliance) and encryption (at\-rest protection) are complementary, and both are policy\-driven rather than hardcoded to Aadhaar alone:

| Resource.Field | Role | Treatment |
| --- | --- | --- |
| `PERSON.aadhaar` | CONSTABLE | Full redaction |
| `PERSON.phone` | CONSTABLE | Last 4 digits |
| `BANK.account` | CONSTABLE | Last 4 digits |
| `PERSON.address` | CONSTABLE | Locality only |

Sensitive fields are additionally encrypted at rest with `cryptography` (Fernet) — the database itself doesn't hold everything in plaintext.

### Secure Evidence Quarantine

An uploaded file is never processed immediately: `upload → quarantine → MIME + extension + size validation → local ClamAV scan → hash → sanitize/parse → sealed evidence store`, with explicit archive\-bomb and path\-traversal protection on any ZIP/compressed input. Scanning is local and self\-hosted rather than a third\-party API — evidence never leaves the deployment boundary, which keeps the same security model true for both the Hosted Demo Instance and the air\-gapped variant. ClamAV's virus\-definition database adds real memory weight on Render's free tier; see Performance & Reliability Safeguards and Known Limitations for how that's managed.

### AI Copilot Security

Document text retrieved for the copilot is **untrusted data, never instructions** — a malicious "ignore previous instructions" line inside an uploaded FIR cannot redirect the model. Authorization happens *before* retrieval (the query planner only ever runs against data the requesting user is already permitted to see — the LLM never decides access), and every response passes: evidence\-grounding check → authorization check → citation validation. A response citing something that doesn't exist in the retrieved set is **blocked**, not shown — and where the evidence doesn't support the claim being asked about, the copilot returns `INSUFFICIENT EVIDENCE` and says what's missing, instead of completing a speculative answer. See Responsible AI & Guardrails.

### Incident Response (Minimal Loop)

`detect → correlate → alert → contain → preserve → investigate → recover` is the target loop; the MVP implements the front half concretely — repeated failed logins trigger an automatic session revoke and account lock, logged as a security alert. Preserve/investigate/recover tooling beyond that is documented, not automated, in five days.

### Honeytokens (Demo Environment Only)

Synthetic canary records exist only in the demo dataset; any access to one is flagged as a security alert with the accessing user, resource, and timestamp. Clearly labeled as a security\-control demonstration, never mixed into real investigative data.

### Secret Management

Secrets are never committed — the Hosted Demo Instance uses each platform's built\-in encrypted environment\-variable store (Vercel, Render, Supabase) as the practical free "vault" for an MVP; the air\-gapped variant documents a local Vault \+ mTLS target for a real production rollout. Secrets never appear in logs, error messages, the frontend bundle, Git, or a database dump.

### Continuous Security Validation

Every push runs Semgrep (SAST), Bandit (Python\-specific SAST), pip\-audit (dependency scan), Trivy (container scan), and an OWASP ZAP baseline scan against the deployed URL — real, free, automated in GitHub Actions. Kali Linux sits **outside** the application entirely, as an isolated validation environment used to run Nmap, OWASP ZAP, Burp Community, and Wireshark against the team's own deployed demo — authorized testing of TRINETRA's own defenses, never a production dependency. The distinction matters: *Kali doesn't protect TRINETRA — Kali is used to test whether TRINETRA's defenses work.*

### Case Isolation

The same phone number, vehicle, or person can legitimately appear in two unrelated investigations. That a canonical entity is shared must never leak visibility across cases: every PostgreSQL query, Neo4j graph query, search query, AI copilot retrieval, analytics computation, and report is scoped by case authorization, and a cross\-case relationship is only ever exposed to an investigator who is authorized on **all** of the cases involved. Shared entities do not imply shared case access.

### Data Classification & Clearance

RBAC/ABAC is backed by an explicit classification scheme (`PUBLIC` / `INTERNAL` / `CONFIDENTIAL` / `RESTRICTED` / `HIGHLY_RESTRICTED`) on cases and evidence, and a clearance level on each user. The policy check becomes concrete rather than implied:

```
IF   user.role is authorized
AND  user has case authorization
AND  user.clearance >= resource.classification
THEN ALLOW
ELSE DENY + AUDIT
```

### Break\-Glass Access

For a genuine investigative emergency, a controlled override exists rather than a shared admin password: a break\-glass request requires an explicit written reason, forces re\-authentication, grants access scoped to one case for a fixed window (e.g. 30 minutes), is fully audit\-logged, and is flagged for mandatory post\-access supervisor review. It's a lightweight MVP version of the pattern — a request record, a time\-boxed elevated token, and an audit trail — not a full multi\-step approval workflow.

## Legal & Forensic Compliance

### BSA Section 63 Evidence Certificate Generator

Every evidence upload already carries a SHA\-256 hash chain and Merkle proof (see Security Model). On top of that, the investigation brief generator can produce a **BSA Section 63 Electronic Evidence Certificate draft** (Bharatiya Sakshya Adhiniyam, 2023) as a WeasyPrint PDF — bundling the deployment's software version, a system/hardware identifier, the full timestamped evidence hash ledger, and the chain\-verification result, structured the way Section 63 requires for electronic evidence. It carries an explicit disclaimer: *"This document assists the prescribed certification process; it does not itself establish legal admissibility."* Generating a PDF and attaching hashes is not, by itself, a claim of legal admissibility — the certificate is a structured aid to the certification process, not a substitute for it.

### Role\-Based Dynamic Field Redaction

RBAC in TRINETRA doesn't stop at page\-level access — it's enforced **field\-by\-field, server\-side, before serialization**. A `CONSTABLE` viewing a person record sees `[Aadhaar Redacted]` and `XXXX-XXXX-1234` for masked identifiers; an `INSPECTOR` or `ADMIN` with clearance on that case sees the unmasked field. The masking rule lives in the API response layer (a per\-field, per\-role policy), so there is no client\-side code path that can leak an unmasked value — the frontend never receives data a role isn't cleared to see in the first place.

## Known Limitations & Non\-Goals

- Built and demoed entirely on **synthetic data** — no real criminal records, real PII, or real case data are used at any point.
- The **Hosted Demo Instance** (Vercel/Render/Supabase/Neo4j Aura/Gemini) is explicitly a judging\-convenience deployment, not a claim that public SaaS is where this belongs in production — [Air\-Gapped / On\-Premise Deployment](#air-gapped-on-premise-deployment-production-path) is the answer to that, not an afterthought, but it is still a proof\-of\-concept\-grade offline deployment, not a hardened, network\-segmented, physically on\-prem production rollout.
- Indic\-language handling at MVP stage combines format\-aware regex, phonetic name matching, and Gemini zero\-shot extraction for Hindi/Hinglish narrative text — a genuine working capability, not full parity with a dedicated trained Indic NER model (AI4Bharat) on noisy, real\-world, production\-scale text, and it does not include OCR for scanned/handwritten Devanagari FIRs.
- Graph analytics are intentionally capped and cached for demo reliability on free\-tier memory limits — a deliberate MVP safeguard, not an unlimited\-scale guarantee; production scale needs the analytics layer re\-architected around Neo4j GDS or a dedicated compute tier.
- Free\-tier hosting means the backend can cold\-start after inactivity; the keep\-warm pinger mitigates this for a demo but is not a production answer.
- Predictive link scores (Adamic\-Adar / Node2Vec) are statistical similarity measures over a small synthetic graph, not calibrated probabilities and not validated against real criminal\-network data — always shown as a score and a lead\-status, never as a percentage likelihood or a finding, and never written into the confirmed graph.
- `faster-whisper` transcription accuracy on regional dialects and heavily code\-switched speech varies; the hosted demo runs a small quantized model sized for free\-tier CPU, so it's a proof\-of\-concept ASR pipeline, not production\-grade transcription.
- `hdbscan` and GeoPandas add real build weight to the backend image; if Render's free\-tier build time or size becomes a problem, the fallback is a lighter haversine\-distance clustering pass instead of full GeoPandas.
- ClamAV's local virus\-definition database adds real memory and image\-size weight on Render's free tier, alongside `hdbscan`/GeoPandas — if free\-tier limits bite, ClamAV runs as its own lightweight worker process rather than in the main API process, with MIME/extension/size validation as the baseline defense if scanning has to degrade to best\-effort.
- The transactional outbox reduces dual\-write drift risk but doesn't eliminate eventual\-consistency lag — the UI should visibly indicate when a just\-created relationship hasn't synced to the graph yet.
- The zero\-trust model's identity, case, field, and action checks are enforced server\-side today; device\-trust and network\-trust attestation are documented as the target, and realistically belong to a managed\-device, network\-segmented deployment — not something a hosted free\-tier demo can meaningfully claim.
- Evidence redundancy has a real, lightweight version — the append\-only hash\-chain/audit\-log manifest backup (see Security Model) — but a verified secondary database replica, an offline vault, and a full 3\-2\-1 backup strategy remain documented design targets, not implemented for the Hosted Demo Instance; Supabase's free tier is a single instance, and true redundancy needs paid infrastructure or a disciplined manual process out of scope for five days.
- Secret management for the MVP relies on each platform's built\-in encrypted environment\-variable store, not a dedicated secrets manager with short\-lived, rotated credentials — HashiCorp Vault is Phase 2 scope.
- Security event correlation and honeytoken alerting are simple, explainable rule\-based heuristics built for this demo's scale — they are not, and are not claimed to be, a production SIEM.
- Break\-glass access and case\-isolation enforcement are new, lightweight MVP controls for this build — they are demonstrated design patterns, not independently audited, hardened guarantees.
- A BSA Section 63 certificate generated by the system assists the prescribed certification process; it does not itself establish legal admissibility — the pitch and the document both say this explicitly.
- Criminal\-history and surveillance\-report ingestion are demonstrated as generic structured/unstructured file imports (a CSV and a PDF/text document through the same pipeline as any FIR) — not a live integration with a real NCRB criminal\-history database or an actual surveillance feed, which would need a formal data\-sharing agreement out of scope for a hackathon build.
- The evidence integrity layer is a hash\-chained, Merkle\-proofed ledger — the same tamper\-evident properties blockchain provides, built as a private application\-level structure rather than a distributed multi\-node ledger; see Security Model for why that trade\-off is deliberate, not a shortcut.
- Moving Target Defense (rotating IPs/ports, randomized service topology) is deliberately not attempted — it needs network/infrastructure control the free\-tier PaaS stack (Vercel/Render) doesn't expose, and claiming it without that control would be exactly the kind of unimplementable buzzword this document works hard to avoid.
- Secure multi\-party computation for cross\-agency entity matching is Phase 2 scope only (see Beyond the Hackathon) — genuinely relevant to a real multi\-department deployment, but not something five days and a single department's dataset can meaningfully build or demonstrate.

## Beyond the Hackathon (Phase 2 Roadmap)

If this moves toward a real NCRB\-facing deployment, the production path is well understood and deliberately deferred rather than skipped:

- Identity: Keycloak \+ OIDC \+ full RBAC/ABAC via Open Policy Agent, plus device\-trust and network\-trust attestation completing the zero\-trust model (managed device enrollment, network microsegmentation)
- Infrastructure: Kubernetes \+ Terraform \+ CI/CD, hardened network\-segmented on\-prem deployment (the Docker Compose air\-gapped variant above is the proof of concept, not the production rollout)
- Graph analytics at scale: Neo4j with the GDS plugin (paid Aura tier or self\-hosted), replacing the capped in\-process NetworkX pass
- Dedicated trained Indic NER (AI4Bharat / Indic NLP ecosystem) on authorized real\-world data, plus OCR for scanned/handwritten Devanagari FIRs, to replace the MVP's zero\-shot Gemini extraction
- Full RAG legal knowledge base (BNS/BNSS/BSA, departmental SOPs) with reranking, and BNS/BNSS fields extended from case\-level tagging to section\-level charge tracking
- HashiCorp Vault with short\-lived, automatically rotated credentials, replacing platform\-managed environment variables
- True evidence redundancy — a verified secondary replica, an offline/air\-gapped backup vault, periodic cross\-copy hash verification — and Postgres primary/replica high availability
- A dedicated WAF/edge security service beyond the free\-tier Cloudflare option, and a sandboxed malware\-detonation environment beyond the MVP's local ClamAV scan
- A signed, verified offline model supply\-chain pipeline for the air\-gapped variant, automating the documented hash/signature/quarantine process
- Privacy\-preserving cross\-agency entity matching (secure multi\-party computation / private set intersection), letting two departments check for overlapping suspects, phones, or accounts across cases without either one exposing its full case data to the other
- Observability: OpenTelemetry, Prometheus, Grafana, Loki
- Hardening: mTLS, dependency scanning at scale, formal container hardening
- An independent security audit / third\-party penetration test, beyond the team's own Kali Linux validation lab
- Retention policies, data classification, and formal evidentiary\-chain\-of\-custody compliance review

## Team

*Add your team name and member roles here.*

| Name | Role |
| --- | --- |
| — | Team Lead |
| — | Backend / AI |
| — | Frontend |
| — | Graph / Data |
| — | Design / Pitch |

## License

MIT — see `LICENSE`. Built for Smart India Hackathon 2026, Problem Statement 26189.
