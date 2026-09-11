"""Evidence storage. Supabase Storage in the cloud, local disk air-gapped."""
import logging
import os
from pathlib import Path

from app.core.config import settings

log = logging.getLogger("trinetra.storage")
LOCAL_ROOT = Path(os.getenv("LOCAL_STORAGE_DIR", "./uploads"))

_client = None


def _supabase():
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(settings.SUPABASE_URL,
                                settings.SUPABASE_SERVICE_KEY)
    return _client


def _use_supabase() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)


def put(bucket: str, path: str, data: bytes,
        content_type: str = "application/octet-stream") -> str:
    if _use_supabase():
        try:
            _supabase().storage.from_(bucket).upload(
                path, data,
                {"content-type": content_type, "upsert": "false"},
            )
            return f"supabase://{bucket}/{path}"
        except Exception as exc:  # noqa: BLE001
            log.warning("Supabase upload failed (%s), using local disk", exc)

    dest = LOCAL_ROOT / bucket / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return f"file://{dest}"


def get(uri: str) -> bytes:
    if uri.startswith("supabase://"):
        _, _, rest = uri.partition("supabase://")
        bucket, _, path = rest.partition("/")
        return _supabase().storage.from_(bucket).download(path)
    if uri.startswith("file://"):
        return Path(uri[7:]).read_bytes()
    raise ValueError(f"Unknown storage URI: {uri}")
