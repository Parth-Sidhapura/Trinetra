#!/usr/bin/env python3
"""Scan what git is about to commit for anything that looks like a secret.

Run this BEFORE the first push. It reads the staged file list from git, so it
sees exactly what would go public — not what happens to be lying in the folder.
"""
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    ("Supabase / JWT token",      re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")),
    ("Google / Gemini API key",   re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("Postgres connection URL",   re.compile(r"postgres(?:ql)?://[^\s:]+:[^\s@]+@")),
    ("Neo4j connection URL",      re.compile(r"neo4j\+s?://[^\s]+")),
    ("Private key block",         re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("NEO4J_PASSWORD assignment", re.compile(r"(?i)neo4j_password\s*[=:]\s*['\"]?[^\s'\"]{4,}")),
    ("Generic secret assignment", re.compile(
        r"(?i)\b(api[_-]?key|secret|service[_-]?key|access[_-]?token|db[_-]?password)"
        r"\s*[=:]\s*['\"][^'\"]{8,}['\"]")),
]

SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".xlsx",
               ".ico", ".woff", ".woff2", ".lock"}
# these are templates — placeholders in them are the point
ALLOW = {".env.example", ".env.local.example"}


def staged_files():
    out = subprocess.run(["git", "ls-files", "-c", "-o", "--exclude-standard"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("git failed — are you inside the project folder?")
        print(out.stderr.strip())
        sys.exit(2)
    return [Path(p) for p in out.stdout.splitlines() if p.strip()]


def main() -> int:
    files = staged_files()
    print(f"git would publish {len(files)} file(s). Scanning…\n")

    hits = []
    for f in files:
        if f.name in ALLOW or f.suffix.lower() in SKIP_SUFFIX:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except (OSError, IsADirectoryError):
            continue
        if len(text) > 2_000_000:
            continue
        for label, pat in PATTERNS:
            for m in pat.finditer(text):
                line = text[:m.start()].count("\n") + 1
                shown = m.group(0)
                shown = shown[:22] + "…" if len(shown) > 24 else shown
                hits.append((str(f), line, label, shown))

    # the files that must never be listed at all
    forbidden = [f for f in files
                 if f.name in (".env", ".env.local")
                 or f.name in ("set_neo4j.py", "set_pw.py", "use_neo4j_creds.py")
                 or "node_modules" in f.parts or ".venv" in f.parts]

    if forbidden:
        print("STOP — these should never be published:\n")
        for f in forbidden[:20]:
            print("   ", f)
        if len(forbidden) > 20:
            print(f"    … and {len(forbidden) - 20} more")
        print("\nYour .gitignore is not covering them. Fix that before committing.\n")

    if hits:
        print("Possible secrets found:\n")
        for f, line, label, shown in hits[:40]:
            print(f"  {f}:{line}\n      {label} — {shown}")
        if len(hits) > 40:
            print(f"  … and {len(hits) - 40} more")
        print()

    if not forbidden and not hits:
        print("Clean. Nothing that looks like a secret, and no ignored")
        print("files leaking through. Safe to commit.")
        return 0

    print("Do NOT push until the above is empty.")
    print("A key that reaches a public repo is burned even if you delete the")
    print("commit afterwards — it stays in the history and in GitHub's cache.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
