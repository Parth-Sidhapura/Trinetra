"""Celery app. Upstash Redis needs explicit TLS options or connections fail."""
import ssl

from celery import Celery

from app.core.config import settings

_ssl = None
if settings.REDIS_URL.startswith("rediss://"):
    _ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

celery_app = Celery(
    "trinetra",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    broker_use_ssl=_ssl,
    redis_backend_use_ssl=_ssl,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,
    beat_schedule={
        "drain-outbox": {
            "task": "trinetra.drain_outbox",
            "schedule": 10.0,
        },
        "backup-manifest": {
            "task": "trinetra.export_backup_manifest",
            "schedule": 3600.0,
        },
    },
)

import app.workers.tasks  # noqa: E402,F401
