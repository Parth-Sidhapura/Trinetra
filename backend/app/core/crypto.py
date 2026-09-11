"""Field-level encryption at rest (Fernet) + display-time redaction."""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet | None:
    global _fernet
    if _fernet is None and settings.ENCRYPTION_KEY:
        _fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return _fernet


def encrypt_field(value: str | None) -> str | None:
    if value is None:
        return None
    f = _get_fernet()
    if f is None:
        return value  # dev fallback - key not configured
    return f.encrypt(value.encode()).decode()


def decrypt_field(value: str | None) -> str | None:
    if value is None:
        return None
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except InvalidToken:
        return value  # was never encrypted


# --- Redaction policy: resource.field -> role -> treatment ---
REDACTION_POLICY: dict[str, dict[str, str]] = {
    "person.aadhaar": {"CONSTABLE": "full", "INSPECTOR": "none", "ADMIN": "none"},
    "person.phone": {"CONSTABLE": "last4", "INSPECTOR": "none", "ADMIN": "none"},
    "bank.account": {"CONSTABLE": "last4", "INSPECTOR": "none", "ADMIN": "none"},
    "person.address": {"CONSTABLE": "locality", "INSPECTOR": "none", "ADMIN": "none"},
}


def redact(field_key: str, value: str | None, role: str) -> str | None:
    """Applied server-side BEFORE serialization. The frontend never receives
    data the role isn't cleared to see."""
    if value is None:
        return None
    treatment = REDACTION_POLICY.get(field_key, {}).get(role.upper(), "none")
    if treatment == "none":
        return value
    if treatment == "full":
        return "[REDACTED]"
    if treatment == "last4":
        return f"XXXX-XXXX-{value[-4:]}" if len(value) >= 4 else "[REDACTED]"
    if treatment == "locality":
        parts = [p.strip() for p in value.split(",")]
        return parts[-1] if parts else "[REDACTED]"
    return value
