# Air-Gapped Deployment

The hosted demo runs on free-tier cloud. This is the offline path — the same
codebase, every cloud dependency swapped for a local equivalent.

```bash
docker compose -f docker-compose.airgapped.yml up -d
```

## What swaps

| Layer | Hosted | Air-gapped |
|---|---|---|
| Relational DB | Supabase Postgres | local `pgvector/pgvector:pg16` |
| Graph | Neo4j AuraDB Free | local `neo4j:5-community` |
| Queue | Upstash Redis | local `redis:7-alpine` |
| LLM / NER / embeddings | Gemini → Groq | local Ollama (`LLM_PROVIDER=ollama`) |
| Malware scan | local ClamAV | local ClamAV (same) |
| Audio | faster-whisper | faster-whisper (same, full model) |
| Storage | Supabase Storage | local volume |

The application targets an `LLM_PROVIDER` interface covering **LLM, NER and
embeddings** — not just chat — so switching is a config change, not a rewrite.

## Offline Model & Image Supply Chain

An air-gapped machine cannot `docker pull` anything. Images and models are
never fetched from inside the air-gapped environment. They are pulled,
scanned, signed and verified on a connected staging machine first, then
carried across on approved media.

```
CONNECTED STAGING ENVIRONMENT
        |
Pull + scan + verify container images and model artifacts
        |
Sign artifacts (SHA-256 + GPG signature)
        |
Approved removable media
        |
AIR-GAPPED ENVIRONMENT
        |
Verify hash + signature, import verified images
        |
Run completely offline
```

### On the staging machine

```bash
# 1. Pull everything
docker pull pgvector/pgvector:pg16
docker pull neo4j:5-community
docker pull redis:7-alpine
docker pull ollama/ollama
docker pull clamav/clamav:stable

# 2. Scan before it ever touches the secure side
trivy image --severity HIGH,CRITICAL pgvector/pgvector:pg16

# 3. Export
docker save -o trinetra-images.tar \
  pgvector/pgvector:pg16 neo4j:5-community redis:7-alpine \
  ollama/ollama clamav/clamav:stable

# 4. Pull the model too
ollama pull llama3
tar -czf ollama-models.tar.gz ~/.ollama/models

# 5. Hash and sign both artifacts
sha256sum trinetra-images.tar ollama-models.tar.gz > MANIFEST.sha256
gpg --armor --detach-sign MANIFEST.sha256
```

### On the air-gapped machine

```bash
# 1. Verify signature FIRST — before touching the payload
gpg --verify MANIFEST.sha256.asc MANIFEST.sha256

# 2. Verify hashes
sha256sum -c MANIFEST.sha256

# 3. Only if BOTH pass, import. Otherwise quarantine.
docker load -i trinetra-images.tar
tar -xzf ollama-models.tar.gz -C ~/

# 4. Run
docker compose -f docker-compose.airgapped.yml up -d
```

**If either check fails, the artifact is quarantined and never imported.**

This is a procedure the team documents and rehearses — not a fully automated
pipeline. Treating AI models and container images as a supply chain needing
the same integrity discipline as evidence is the point.

## Post-deployment

```bash
docker compose -f docker-compose.airgapped.yml exec backend alembic upgrade head
docker compose -f docker-compose.airgapped.yml exec ollama ollama run llama3 "test"
```

Set real passwords via `.env` beside the compose file:

```
DB_PASSWORD=<strong-value>
NEO4J_PASSWORD=<strong-value>
```
