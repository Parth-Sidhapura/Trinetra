"""Health + keep-warm.

IMPORTANT: this endpoint deliberately touches Neo4j too. Neo4j AuraDB Free
auto-pauses after 72 hours of inactivity - pinging only the web service
would let the graph database pause right before judging.
"""
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter()


@router.get("/health")
def health():
    status = {"api": "ok", "postgres": "unknown", "neo4j": "disabled"}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        status["postgres"] = f"error: {type(exc).__name__}"

    if settings.NEO4J_ENABLED and settings.NEO4J_URI:
        try:
            from app.services.graph_sync import ping_neo4j
            ping_neo4j()
            status["neo4j"] = "ok"
        except Exception as exc:  # noqa: BLE001
            status["neo4j"] = f"error: {type(exc).__name__}"

    status["healthy"] = status["postgres"] == "ok"
    return status
