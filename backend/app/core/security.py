"""Zero-trust request pipeline.

Supabase ISSUES the JWT. This backend only VERIFIES it - it never signs
a second, separate token. Every request is checked down the chain:
identity -> case authorization -> field authorization -> action authorization.
"""
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import UserProfile, Case, BreakGlassRequest

bearer = HTTPBearer(auto_error=False)

ROLE_RANK = {"CONSTABLE": 1, "INSPECTOR": 2, "ADMIN": 3}
CLEARANCE_RANK = {
    "public": 1, "internal": 2, "confidential": 3,
    "restricted": 4, "highly_restricted": 5,
}


class Principal:
    """Who is asking, and what they're allowed to do."""

    def __init__(self, user_id: str, email: str, role: str,
                 department: str, clearance: str):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.department = department
        self.clearance = clearance

    def outranks(self, required_role: str) -> bool:
        return ROLE_RANK.get(self.role, 0) >= ROLE_RANK.get(required_role, 99)

    def cleared_for(self, classification: str) -> bool:
        return (CLEARANCE_RANK.get(self.clearance, 0)
                >= CLEARANCE_RANK.get(classification, 99))


_JWKS_CLIENT = None


def _jwks():
    """Cached JWKS client. Supabase publishes its public keys here, and the
    library refetches on key rotation by itself."""
    global _JWKS_CLIENT
    if _JWKS_CLIENT is None:
        if not settings.SUPABASE_URL:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "SUPABASE_URL is not configured, so asymmetric tokens "
                "cannot be verified")
        url = settings.SUPABASE_URL.rstrip("/") + "/auth/v1/.well-known/jwks.json"
        _JWKS_CLIENT = jwt.PyJWKClient(url)
    return _JWKS_CLIENT


def _decode(token: str) -> dict:
    """Verify a Supabase-issued JWT.

    Supabase signs with ES256 (asymmetric) on current projects and HS256
    (shared secret) on older ones. The token's own header says which, so read
    it and verify accordingly - never trust an algorithm we picked ourselves,
    and never accept 'none'.
    """
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            f"Malformed token: {exc}")

    options = {"verify_aud": bool(settings.JWT_AUDIENCE)}
    common = {
        "audience": settings.JWT_AUDIENCE or None,
        "issuer": settings.JWT_ISSUER or None,
        "options": options,
    }

    try:
        if alg.startswith(("RS", "ES", "PS")):
            # asymmetric - fetch the matching public key from the project's JWKS
            key = _jwks().get_signing_key_from_jwt(token).key
            return jwt.decode(token, key, algorithms=[alg], **common)

        if alg.startswith("HS"):
            if not settings.SUPABASE_JWT_SECRET:
                # Dev escape hatch ONLY - never reachable when the secret is set.
                if settings.ENV == "dev":
                    return {"sub": "dev-user", "email": "dev@local",
                            "role": "ADMIN"}
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    "SUPABASE_JWT_SECRET not configured")
            return jwt.decode(token, settings.SUPABASE_JWT_SECRET,
                              algorithms=[alg], **common)

        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            f"Unsupported token algorithm: {alg or 'none'}")
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            f"Invalid token: {exc}")


def get_principal(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> Principal:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    claims = _decode(creds.credentials)
    user_id = claims.get("sub")
    email = claims.get("email", "")

    profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if profile is None:
        # First login - create a least-privilege profile.
        #
        # A signed-in page fires several requests at once (the dashboard loads
        # /admin/me and /cases in parallel), so on the very first login two of
        # them can both find no profile and both try to insert it. Losing that
        # race is harmless - the row we wanted now exists - so roll back and
        # read it instead of failing the request.
        profile = UserProfile(id=user_id, email=email, role="CONSTABLE")
        db.add(profile)
        try:
            db.commit()
            db.refresh(profile)
        except IntegrityError:
            db.rollback()
            profile = (db.query(UserProfile)
                         .filter(UserProfile.id == user_id).first())
            if profile is None:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "Could not establish a profile for this account")

    # CONTAIN: a locked account is refused at the identity stage.
    from datetime import datetime, timezone
    if profile.locked_until and profile.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status.HTTP_423_LOCKED,
            f"Account locked until {profile.locked_until.isoformat()} "
            f"following repeated failed sign-in attempts.")

    request.state.principal_email = profile.email
    return Principal(
        user_id=str(profile.id),
        email=profile.email or email,
        role=profile.role,
        department=profile.department,
        clearance=profile.clearance,
    )


CurrentUser = Annotated[Principal, Depends(get_principal)]


def require_role(minimum: str):
    """Action authorization - per route, server-side."""
    def _dep(user: CurrentUser) -> Principal:
        if not user.outranks(minimum):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Requires {minimum} or higher")
        return user
    return _dep


def authorize_case(db: Session, user: Principal, case_id: str) -> Case:
    """Case isolation boundary.

    A shared canonical entity must NEVER leak cross-case visibility.
    Every graph, search, AI and report query goes through here first.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    if user.role == "ADMIN":
        return case

    if case.department != user.department:
        if not _has_break_glass(db, user.user_id, case_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Not authorized on this case")

    if not user.cleared_for(case.data_classification):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Insufficient clearance for this classification")
    return case


def _has_break_glass(db: Session, user_id: str, case_id: str) -> bool:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return db.query(BreakGlassRequest).filter(
        BreakGlassRequest.user_id == user_id,
        BreakGlassRequest.case_id == case_id,
        BreakGlassRequest.expires_at > now,
    ).first() is not None
