"""Tests for JWT authentication middleware and dependencies."""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.dependencies import (
    CurrentUser,
    get_current_user,
    require_admin,
    require_applicant,
    require_officer,
)
from app.middleware.auth import ALGORITHM, decode_jwt

# Test secret — override settings for tests
TEST_JWT_SECRET = "test-jwt-secret-for-unit-tests"


def _make_token(payload: dict, secret: str = TEST_JWT_SECRET) -> str:
    """Helper to create a JWT token for testing."""
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Unit tests for decode_jwt
# ---------------------------------------------------------------------------


class TestDecodeJwt:
    """Tests for the low-level decode_jwt function."""

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    def test_valid_token(self):
        payload = {"sub": "user-123", "email": "test@example.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)
        decoded = decode_jwt(token)
        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "test@example.com"

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    def test_expired_token(self):
        payload = {"sub": "user-123", "exp": int(time.time()) - 100}
        token = _make_token(payload)
        from jose import ExpiredSignatureError

        with pytest.raises(ExpiredSignatureError):
            decode_jwt(token)

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    def test_invalid_signature(self):
        payload = {"sub": "user-123", "exp": int(time.time()) + 3600}
        token = _make_token(payload, secret="wrong-secret")
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_jwt(token)

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    def test_malformed_token(self):
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_jwt("not-a-valid-jwt")


# ---------------------------------------------------------------------------
# Integration tests for FastAPI dependencies
# ---------------------------------------------------------------------------


def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app with auth-protected routes for testing."""
    app = FastAPI()

    @app.get("/me")
    async def me(user: CurrentUser = Depends(get_current_user)):
        return {"id": user.id, "email": user.email, "role": user.role}

    @app.get("/applicant-only")
    async def applicant_route(user: CurrentUser = Depends(require_applicant)):
        return {"role": user.role}

    @app.get("/officer-only")
    async def officer_route(user: CurrentUser = Depends(require_officer)):
        return {"role": user.role}

    @app.get("/admin-only")
    async def admin_route(user: CurrentUser = Depends(require_admin)):
        return {"role": user.role}

    return app


@pytest.fixture
def client():
    app = _create_test_app()
    return TestClient(app)


def _mock_profile_response(role: str):
    """Create a mock Supabase response with the given role."""
    mock_response = MagicMock()
    mock_response.data = [{"role": role}]
    return mock_response


def _mock_empty_profile_response():
    """Create a mock Supabase response with no profile found."""
    mock_response = MagicMock()
    mock_response.data = []
    return mock_response


class TestGetCurrentUser:
    """Tests for the get_current_user dependency."""

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    @patch("app.dependencies.create_client")
    def test_valid_token_returns_user(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _mock_profile_response("Applicant")
        )
        mock_create_client.return_value = mock_supabase

        payload = {"sub": "user-abc", "email": "user@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user-abc"
        assert data["email"] == "user@test.com"
        assert data["role"] == "Applicant"

    def test_missing_auth_header_returns_401(self, client):
        response = client.get("/me")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    def test_expired_token_returns_401(self, client):
        payload = {"sub": "user-abc", "exp": int(time.time()) - 100}
        token = _make_token(payload)

        response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Token has expired"

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    def test_invalid_token_returns_401(self, client):
        token = _make_token(
            {"sub": "user-abc", "exp": int(time.time()) + 3600}, secret="wrong-secret"
        )

        response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid token"

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    @patch("app.dependencies.create_client")
    def test_profile_not_found_returns_401(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _mock_empty_profile_response()
        )
        mock_create_client.return_value = mock_supabase

        payload = {"sub": "user-no-profile", "email": "x@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "User profile not found"

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    def test_token_without_sub_returns_401(self, client):
        payload = {"email": "no-sub@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication credentials"


class TestRoleAuthorization:
    """Tests for role-checking dependencies."""

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    @patch("app.dependencies.create_client")
    def test_applicant_can_access_applicant_route(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _mock_profile_response("Applicant")
        )
        mock_create_client.return_value = mock_supabase

        payload = {"sub": "user-1", "email": "a@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        response = client.get("/applicant-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    @patch("app.dependencies.create_client")
    def test_applicant_cannot_access_officer_route(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _mock_profile_response("Applicant")
        )
        mock_create_client.return_value = mock_supabase

        payload = {"sub": "user-1", "email": "a@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        response = client.get("/officer-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    @patch("app.dependencies.create_client")
    def test_applicant_cannot_access_admin_route(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _mock_profile_response("Applicant")
        )
        mock_create_client.return_value = mock_supabase

        payload = {"sub": "user-1", "email": "a@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    @patch("app.dependencies.create_client")
    def test_officer_can_access_officer_route(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _mock_profile_response("Bank_Officer")
        )
        mock_create_client.return_value = mock_supabase

        payload = {"sub": "user-2", "email": "o@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        response = client.get("/officer-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    @patch("app.dependencies.create_client")
    def test_officer_cannot_access_admin_route(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _mock_profile_response("Bank_Officer")
        )
        mock_create_client.return_value = mock_supabase

        payload = {"sub": "user-2", "email": "o@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        response = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    @patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    @patch("app.dependencies.create_client")
    def test_admin_can_access_all_routes(self, mock_create_client, client):
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            _mock_profile_response("Admin")
        )
        mock_create_client.return_value = mock_supabase

        payload = {"sub": "user-3", "email": "admin@test.com", "exp": int(time.time()) + 3600}
        token = _make_token(payload)

        for route in ["/applicant-only", "/officer-only", "/admin-only"]:
            response = client.get(route, headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200, f"Admin should access {route}"
