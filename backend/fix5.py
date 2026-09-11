import io, ast, re
p = "app/core/security.py"
s = io.open(p, encoding="utf-8").read()

start = s.index("def _decode(")
end = s.index("def get_principal(")

new_fn = '''_jwks_client = None


def _decode(token: str) -> dict:
    """Verify a Supabase-issued JWT.

    Supabase issues either legacy HS256 (shared secret) or modern ES256/RS256
    (asymmetric, published via JWKS). Both are accepted; the algorithm is read
    from the token header and the matching verification path is used.
    """
    if not settings.SUPABASE_JWT_SECRET and not settings.SUPABASE_URL:
        if settings.ENV == "dev":
            return {"sub": "dev-user", "email": "dev@local", "role": "ADMIN"}
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "JWT verification is not configured")

    kwargs = dict(
        audience=settings.JWT_AUDIENCE or None,
        issuer=settings.JWT_ISSUER or None,
        options={"verify_aud": bool(settings.JWT_AUDIENCE)},
    )

    try:
        alg = jwt.get_unverified_header(token).get("alg", "HS256")

        if alg == "HS256":
            return jwt.decode(token, settings.SUPABASE_JWT_SECRET,
                              algorithms=["HS256"], **kwargs)

        global _jwks_client
        if _jwks_client is None:
            from jwt import PyJWKClient
            _jwks_client = PyJWKClient(
                f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
        return jwt.decode(token, signing_key, algorithms=[alg], **kwargs)

    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            f"Invalid token: {exc}")


'''

s = s[:start] + new_fn + s[end:]
io.open(p, "w", encoding="utf-8").write(s)
ast.parse(s)
print("PATCHED OK")
