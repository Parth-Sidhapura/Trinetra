#!/usr/bin/env python3
"""List users and assign ranks.

Rank is server-side state. Nobody picks it at sign-in — that is the whole
point of the access model, so this is how it gets set.

    python set_role.py                              list everyone
    python set_role.py viewer@x.com  viewer         read-only
    python set_role.py officer@x.com filer          can file and decide
    python set_role.py boss@x.com    admin          everything

Named presets:
    viewer  ->  CONSTABLE  / restricted          reads cases, nothing else
    filer   ->  INSPECTOR  / highly_restricted   files evidence, decides matches
    admin   ->  ADMIN      / highly_restricted   the above, plus assigning ranks
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal        # noqa: E402
from app.models import UserProfile             # noqa: E402

PRESETS = {
    "viewer":    ("CONSTABLE", "restricted"),
    "constable": ("CONSTABLE", "restricted"),
    "filer":     ("INSPECTOR", "highly_restricted"),
    "inspector": ("INSPECTOR", "highly_restricted"),
    "admin":     ("ADMIN",     "highly_restricted"),
}

WHAT = {
    "CONSTABLE": "reads cases; cannot open a case, upload evidence, "
                 "decide a match, or see the audit log",
    "INSPECTOR": "files evidence, decides identity matches, runs detectors, "
                 "sees the Security Operations Center",
    "ADMIN":     "everything an Inspector can do, plus assigning ranks",
}


def show(db):
    rows = db.query(UserProfile).order_by(UserProfile.email).all()
    if not rows:
        print("No user profiles yet.")
        print("A profile is created the first time an account signs in to the app.")
        return
    print(f"{'email':<34}{'rank':<12}{'clearance':<20}department")
    print("-" * 88)
    for r in rows:
        print(f"{(r.email or '?'):<34}{r.role:<12}{r.clearance:<20}{r.department}")
    print()
    for role, text in WHAT.items():
        print(f"  {role:<11}{text}")


def main() -> int:
    db = SessionLocal()
    try:
        if len(sys.argv) == 1:
            show(db)
            return 0

        if len(sys.argv) != 3:
            print(__doc__)
            return 1

        email, preset = sys.argv[1].strip(), sys.argv[2].strip().lower()
        if preset not in PRESETS:
            print(f"Unknown rank '{preset}'. Use one of: "
                  f"{', '.join(sorted(PRESETS))}")
            return 1

        user = db.query(UserProfile).filter(UserProfile.email == email).first()
        if user is None:
            print(f"No account found for {email}.")
            print("Sign in once with that account in the app, then run this again —")
            print("the profile is created on first sign-in.")
            print()
            show(db)
            return 1

        role, clearance = PRESETS[preset]
        before = f"{user.role} / {user.clearance}"
        user.role, user.clearance = role, clearance
        if not user.department:
            user.department = "CYBER_CELL"
        db.commit()

        print(f"{email}")
        print(f"  was  {before}")
        print(f"  now  {role} / {clearance}")
        print(f"  {WHAT[role]}")
        print()
        print("Sign out and back in on that account to see the change.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
