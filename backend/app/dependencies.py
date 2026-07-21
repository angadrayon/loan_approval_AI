"""Dependency injection for FastAPI routes — JWT auth and role authorization."""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from pydantic import BaseModel
from supabase import create_client

from app.config import settings
from app.middleware.auth import decode_jwt

logger = logging.getLogger(__name__)

# HTTPBearer extracts the token from the Authorization header automatically.
# auto_error=False so we can return a custom 401 message when the header is missing.
_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Represents the authenticated user extracted from the JWT."""

    id: str
    email: str
    role: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency that authenticates the request.
    """
    if credentials is None:
        logger.error("[AUTH] No Authorization header received")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    logger.info("[AUTH] Token received: %s... (length=%d)", token[:20], len(token))

    # Decode and verify the JWT
    try:
        payload = decode_jwt(token)
        logger.info("[AUTH] JWT decoded successfully. Claims: sub=%s, email=%s, iss=%s",
                    payload.get("sub", "MISSING")[:8],
                    payload.get("email", "MISSING"),
                    payload.get("iss", "MISSING"))
    except ExpiredSignatureError:
        logger.error("[AUTH] Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.error("[AUTH] JWT decode failed: %s (type=%s)", str(e), type(e).__name__)
        logger.error("[AUTH] JWT secret used (first 10 chars): %s...", settings.SUPABASE_JWT_SECRET[:10])
        logger.error("[AUTH] Token first 50 chars: %s", token[:50])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID (sub claim) and email from the JWT payload
    user_id: str | None = payload.get("sub")
    email: str | None = payload.get("email")

    if not user_id:
        logger.error("[AUTH] No 'sub' claim in JWT payload: %s", payload)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query the profiles table using the service role key (bypasses RLS)
    logger.info("[AUTH] Querying profiles for user_id=%s", user_id[:8])
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    response = supabase.table("profiles").select("role").eq("user_id", user_id).execute()

    if not response.data:
        logger.error("[AUTH] No profile found for user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User profile not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = response.data[0]["role"]
    logger.info("[AUTH] Authenticated: user_id=%s, role=%s", user_id[:8], role)

    return CurrentUser(id=user_id, email=email or "", role=role)


async def require_applicant(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Dependency that requires the user to have at least Applicant-level access.

    Allowed roles: Applicant, Bank_Officer, Admin.
    """
    if current_user.role not in ("Applicant", "Bank_Officer", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def require_officer(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Dependency that requires Bank Officer or Admin role.

    Allowed roles: Bank_Officer, Admin.
    """
    if current_user.role not in ("Bank_Officer", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Dependency that requires Admin role.

    Allowed roles: Admin only.
    """
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user
