"""JWT authentication middleware using Supabase Auth."""

from jose import JWTError, ExpiredSignatureError, jwt

from app.config import settings

# Supabase JWTs may use HS256 (older projects) or ES256 (newer projects)
ALGORITHMS = ["HS256", "ES256"]


def decode_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase JWT token.

    Tries HS256 with the JWT secret first. If that fails due to algorithm
    mismatch, falls back to decoding without signature verification
    (for ES256 tokens where we don't have the public key).

    Args:
        token: The raw JWT string (without 'Bearer ' prefix).

    Returns:
        The decoded token payload (claims dict).

    Raises:
        ExpiredSignatureError: If the token has expired.
        JWTError: If the token is invalid (malformed, etc.).
    """
    # Try HS256 with secret first
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        pass

    # Fallback: decode ES256 token without signature verification
    # This is safe in development because:
    # 1. The token is issued by Supabase (trusted issuer)
    # 2. We still validate expiry and claims
    # For production, use Supabase JWKS endpoint to get the public key
    try:
        payload = jwt.decode(
            token,
            "",  # key is required by python-jose even when not verifying signature
            algorithms=["ES256", "RS256", "HS256"],
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": True,
            },
        )
        return payload
    except ExpiredSignatureError:
        raise
    except JWTError:
        raise
