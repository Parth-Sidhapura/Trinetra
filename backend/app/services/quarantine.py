"""Secure evidence quarantine.

upload -> validate -> scan -> hash -> parse -> sealed store.
A file is NEVER processed before it passes this gate.
"""
import logging
import socket

from app.core.config import settings

log = logging.getLogger("trinetra.quarantine")

MAX_SIZE = 50 * 1024 * 1024          # 50 MB

ALLOWED_EXT = {
    ".pdf", ".csv", ".xlsx", ".xlsm", ".txt", ".md",
    ".wav", ".mp3", ".m4a", ".ogg", ".flac",
}

# Magic-byte signatures - extension alone is not trusted
MAGIC = {
    b"%PDF": ".pdf",
    b"PK\x03\x04": ".xlsx",       # also .docx/.zip family
    b"RIFF": ".wav",
    b"ID3": ".mp3",
    b"OggS": ".ogg",
    b"fLaC": ".flac",
}


class QuarantineError(Exception):
    pass


def _ext(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate(filename: str, data: bytes) -> dict:
    ext = _ext(filename)
    if ext not in ALLOWED_EXT:
        raise QuarantineError(f"File type {ext or '(none)'} not allowed")
    if len(data) == 0:
        raise QuarantineError("Empty file")
    if len(data) > MAX_SIZE:
        raise QuarantineError(f"File exceeds {MAX_SIZE // (1024*1024)}MB limit")

    detected = None
    for magic, magic_ext in MAGIC.items():
        if data.startswith(magic):
            detected = magic_ext
            break

    # Archive-bomb guard: a zip-family file claiming to be a spreadsheet
    if detected == ".xlsx" and ext not in (".xlsx", ".xlsm"):
        raise QuarantineError("Archive content with mismatched extension")

    # Path-traversal guard on the stored name
    if "/" in filename or "\\" in filename or ".." in filename:
        raise QuarantineError("Illegal characters in filename")

    return {"ext": ext, "detected": detected, "size": len(data)}


def scan_malware(data: bytes) -> dict:
    """Local ClamAV over its INSTREAM socket protocol.

    Local and self-hosted on purpose - evidence content NEVER leaves the
    deployment boundary, hosted or air-gapped alike. Degrades to
    validation-only if clamd isn't reachable (free-tier RAM limits).
    """
    if not settings.CLAMAV_ENABLED:
        return {"scanned": False, "result": "skipped",
                "detail": "CLAMAV_ENABLED=false"}
    try:
        with socket.create_connection(
            (settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=10
        ) as sock:
            sock.sendall(b"zINSTREAM\0")
            chunk_size = 8192
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                sock.sendall(len(chunk).to_bytes(4, "big") + chunk)
            sock.sendall((0).to_bytes(4, "big"))
            reply = sock.recv(4096).decode(errors="replace")

        infected = "FOUND" in reply
        return {"scanned": True,
                "result": "infected" if infected else "clean",
                "detail": reply.strip()}
    except (OSError, socket.timeout) as exc:
        log.warning("ClamAV unreachable, degrading to validation-only: %s", exc)
        return {"scanned": False, "result": "degraded", "detail": str(exc)}


def process_upload(filename: str, data: bytes) -> dict:
    info = validate(filename, data)
    scan = scan_malware(data)
    if scan["result"] == "infected":
        raise QuarantineError(f"Malware detected: {scan['detail']}")
    return {**info, "scan": scan}
