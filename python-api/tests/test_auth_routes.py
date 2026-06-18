"""
Tests for Authentication Routes

Tests the auth proxy endpoints that forward to AINative Studio:
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET /api/v1/auth/me
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from api.dependencies import get_current_user
from api.routes.auth import router
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Test app with auth router
app = FastAPI()
app.include_router(router)


@app.exception_handler(Exception)
async def exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@pytest.fixture
def client():
    """Unauthenticated test client."""
    yield TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "id": str(uuid.uuid4()),
        "email": "dev@ainative.studio",
        "name": "Dev User",
        "email_verified": True,
    }


@pytest.fixture
def authenticated_client(mock_user):
    """Test client with auth dependency overridden."""
    async def override():
        return mock_user
    app.dependency_overrides[get_current_user] = override
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestLogin:
    """Test POST /api/v1/auth/login"""

    @patch("api.routes.auth.httpx.AsyncClient")
    def test_login_success(self, mock_client_class, client):
        """Should return tokens and user on valid credentials."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "jwt-access-token-123",
            "refresh_token": "jwt-refresh-token-456",
            "token_type": "bearer",
            "user": {
                "id": "user-uuid",
                "email": "dev@ainative.studio",
                "name": "Dev User",
            },
        }

        mock_async_client = AsyncMock()
        mock_async_client.post.return_value = mock_response
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_async_client

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "dev@ainative.studio", "password": "correct-password"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tokens"]["access_token"] == "jwt-access-token-123"
        assert data["tokens"]["refresh_token"] == "jwt-refresh-token-456"
        assert data["user"]["email"] == "dev@ainative.studio"

    @patch("api.routes.auth.httpx.AsyncClient")
    def test_login_invalid_credentials(self, mock_client_class, client):
        """Should return 401 on wrong credentials."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid credentials"}

        mock_async_client = AsyncMock()
        mock_async_client.post.return_value = mock_response
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_async_client

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "dev@ainative.studio", "password": "wrong"},
        )

        assert response.status_code == 401

    def test_login_invalid_email_format(self, client):
        """Should return 422 on invalid email."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "password"},
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client):
        """Should return 422 when password is missing."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "dev@ainative.studio"},
        )
        assert response.status_code == 422

    @patch("api.routes.auth.httpx.AsyncClient")
    def test_login_calls_correct_ainative_endpoint(self, mock_client_class, client):
        """Should proxy to AINative /v1/auth/login (not the old /v1/public/auth/login-json)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "token",
            "user": {},
        }

        mock_async_client = AsyncMock()
        mock_async_client.post.return_value = mock_response
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_async_client

        client.post(
            "/api/v1/auth/login",
            json={"email": "dev@ainative.studio", "password": "pass"},
        )

        call_args = mock_async_client.post.call_args
        url = call_args[0][0]
        assert "/v1/auth/login" in url
        assert "/v1/public/auth/login-json" not in url

    @patch("api.routes.auth.httpx.AsyncClient")
    def test_login_timeout(self, mock_client_class, client):
        """Should return 504 when AINative times out."""
        mock_async_client = AsyncMock()
        mock_async_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_async_client

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "dev@ainative.studio", "password": "pass"},
        )

        assert response.status_code == 504

    @patch("api.routes.auth.httpx.AsyncClient")
    def test_login_service_unavailable(self, mock_client_class, client):
        """Should return 503 when AINative is unreachable."""
        mock_async_client = AsyncMock()
        mock_async_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_async_client

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "dev@ainative.studio", "password": "pass"},
        )

        assert response.status_code == 503


class TestRefreshToken:
    """Test POST /api/v1/auth/refresh"""

    @patch("api.routes.auth.httpx.AsyncClient")
    def test_refresh_success(self, mock_client_class, client):
        """Should return new tokens on valid refresh token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "bearer",
            "user": {"id": "user-uuid", "email": "dev@ainative.studio"},
        }

        mock_async_client = AsyncMock()
        mock_async_client.post.return_value = mock_response
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_async_client

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "old-refresh-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tokens"]["access_token"] == "new-access-token"

    @patch("api.routes.auth.httpx.AsyncClient")
    def test_refresh_expired_token(self, mock_client_class, client):
        """Should return 401 on expired refresh token."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_async_client = AsyncMock()
        mock_async_client.post.return_value = mock_response
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_class.return_value = mock_async_client

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "expired-token"},
        )

        assert response.status_code == 401

    def test_refresh_missing_token(self, client):
        """Should return 422 when refresh_token is missing."""
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 422


class TestGetMe:
    """Test GET /api/v1/auth/me"""

    def test_get_me_authenticated(self, authenticated_client, mock_user):
        """Should return user profile when authenticated."""
        response = authenticated_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user["id"]
        assert data["email"] == mock_user["email"]
        assert data["name"] == mock_user["name"]
        assert data["email_verified"] == mock_user["email_verified"]

    def test_get_me_unauthenticated(self, client):
        """Should return 401/403 when no token provided."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)
