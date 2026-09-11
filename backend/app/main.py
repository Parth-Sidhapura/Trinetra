"""TRINETRA API entrypoint."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import (admin, anomalies, cases, copilot, entities,
                            evidence, graph, health, reports, resolution,
                            security)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trinetra")

from app.core.config import settings  # noqa: E402

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="TRINETRA API",
    description="AI-Powered Criminal Network Analysis System - SIH 2026 PS 26189",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})


for _r in (health.router, admin.router, cases.router, evidence.router,
           entities.router, resolution.router, graph.router,
           anomalies.router, copilot.router, security.router,
           reports.router):
    app.include_router(_r)


@app.get("/")
def root():
    return {
        "name": "TRINETRA",
        "status": "running",
        "env": settings.ENV,
        "docs": "/docs" if settings.DEBUG else "disabled",
    }
