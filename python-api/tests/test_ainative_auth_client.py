"""
Tests for AINative Authentication Client

TDD: Red Phase - These tests should fail until implementation is complete
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestAINativeAuthClient:
    """Test suite for AINativeAuthClient"""

    @pytest.fixture
    def auth_client(self):
        """Create AINativeAuthClient instance for testing"""
        from integrations.ainative.auth_client import AINativeAuthClient

        return AINativeAuthClient(base_url="https://api.ainative.studio")

    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_client):
        """Test successful token verification"""
        # Arrange
        token = "valid_jwt_token_123"
        expected_user = {
            "id": "user-uuid-123",
            "email": "test@example.com",
            "name": "Test User",
            "email_verified": True,
        }

        # Mock the HTTP response
        with patch.object(auth_client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_user
            mock_get.return_value = mock_response

            # Act
            result = await auth_client.verify_token(token)

            # Assert
            assert result is not None
            assert result["id"] == "user-uuid-123"
            assert result["email"] == "test@example.com"
            assert result["name"] == "Test User"
            assert result["email_verified"] is True
            mock_get.assert_called_once_with(
                "/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
            )

    @pytest.mark.asyncio
    async def test_verify_token_invalid_returns_none(self, auth_client):
        """Test that invalid token returns None"""
        # Arrange
        token = "invalid_token"

        # Mock 401 response
        with patch.object(auth_client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response

            # Act
            result = await auth_client.verify_token(token)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_expired_returns_none(self, auth_client):
        """Test that expired token returns None"""
        # Arrange
        token = "expired_token"

        # Mock 401 response
        with patch.object(auth_client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Token expired"}
            mock_get.return_value = mock_response

            # Act
            result = await auth_client.verify_token(token)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_network_error_returns_none(self, auth_client):
        """Test that network errors return None gracefully"""
        # Arrange
        token = "some_token"

        # Mock network error
        with patch.object(auth_client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")

            # Act
            result = await auth_client.verify_token(token)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_timeout_returns_none(self, auth_client):
        """Test that timeout errors return None gracefully"""
        # Arrange
        token = "some_token"

        # Mock timeout error
        with patch.object(auth_client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            # Act
            result = await auth_client.verify_token(token)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_api_key_success(self, auth_client):
        """Test successful API key verification"""
        # Arrange
        api_key = "sk_test_1234567890"
        expected_user = {
            "id": "user-uuid-456",
            "email": "api@example.com",
            "name": "API User",
            "email_verified": True,
        }

        # Mock the HTTP response
        with patch.object(auth_client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_user
            mock_get.return_value = mock_response

            # Act
            result = await auth_client.verify_api_key(api_key)

            # Assert
            assert result is not None
            assert result["id"] == "user-uuid-456"
            assert result["email"] == "api@example.com"
            mock_get.assert_called_once_with("/v1/auth/me", headers={"X-API-Key": api_key})

    @pytest.mark.asyncio
    async def test_verify_api_key_invalid_returns_none(self, auth_client):
        """Test that invalid API key returns None"""
        # Arrange
        api_key = "invalid_api_key"

        # Mock 401 response
        with patch.object(auth_client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response

            # Act
            result = await auth_client.verify_api_key(api_key)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_api_key_network_error_returns_none(self, auth_client):
        """Test that network errors return None for API key verification"""
        # Arrange
        api_key = "sk_test_1234567890"

        # Mock network error
        with patch.object(auth_client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Network error")

            # Act
            result = await auth_client.verify_api_key(api_key)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_client_initialization_with_custom_url(self):
        """Test client initialization with custom base URL"""
        # Arrange & Act
        from integrations.ainative.auth_client import AINativeAuthClient

        custom_url = "http://localhost:8000"
        client = AINativeAuthClient(base_url=custom_url)

        # Assert
        assert client.base_url == custom_url

    @pytest.mark.asyncio
    async def test_client_initialization_with_default_url(self):
        """Test client initialization with default base URL"""
        # Arrange & Act
        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()

        # Assert
        assert client.base_url == "https://api.ainative.studio"
