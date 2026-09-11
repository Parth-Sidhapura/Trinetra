"""Central configuration. Everything comes from environment variables."""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "TRINETRA"
    ENV: Literal["dev", "prod", "airgapped"] = "dev"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # --- Postgres (system of record) ---
    # Supabase: use the POOLER string (port 6543) for the app.
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/trinetra"
    # Direct string (port 5432) - Alembic only. Pooler mode breaks DDL.
    DATABASE_DIRECT_URL: str = ""

    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    JWT_ISSUER: str = ""
    JWT_AUDIENCE: str = "authenticated"
    EVIDENCE_BUCKET: str = "evidence"
    BACKUP_BUCKET: str = "evidence-backups"

    # --- Neo4j (graph projection) ---
    NEO4J_URI: str = ""
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_ENABLED: bool = True

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_ENABLED: bool = True

    # --- LLM provider abstraction ---
    # gemini | groq | ollama  -> swap the whole AI layer with one variable
    LLM_PROVIDER: Literal["gemini", "groq", "ollama"] = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBED_MODEL: str = "models/gemini-embedding-001"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # --- Encryption ---
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # --- Optional heavy features (degrade gracefully) ---
    WHISPER_MODEL_SIZE: str = "tiny"
    WHISPER_ENABLED: bool = False
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    # --- Analytics safeguards (free-tier RAM protection) ---
    MAX_GRAPH_NODES: int = 2000
    MAX_GRAPH_EDGES: int = 8000
    ANALYTICS_CACHE_TTL: int = 300

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def alembic_url(self) -> str:
        return self.DATABASE_DIRECT_URL or self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
