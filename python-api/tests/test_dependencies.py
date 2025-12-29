"""
Tests for FastAPI Authentication Dependencies

TDD: Red Phase - These tests should fail until implementation is complete
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials


class TestGetCurrentUser:
    """Test suite for get_current_user dependency"""

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_jwt_token(self):
        """Test get_current_user returns user data for valid JWT token"""
        # Arrange
        from api.dependencies import get_current_user

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None  # No X-API-Key header

        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_jwt_token"
        )

        expected_user = {
            "id": "user-123",
            "email": "user@example.com",
            "name": "Test User",
            "email_verified": True,
        }

        # Mock the auth_client.verify_token
        with patch("api.dependencies.auth_client") as mock_auth_client:
            mock_auth_client.verify_token = AsyncMock(return_value=expected_user)

            # Act
            result = await get_current_user(mock_request, mock_credentials)

            # Assert
            assert result == expected_user
            mock_auth_client.verify_token.assert_called_once_with("valid_jwt_token")

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_jwt_token_raises_401(self):
        """Test get_current_user raises 401 for invalid JWT token"""
        # Arrange
        from api.dependencies import get_current_user

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        # Mock the auth_client.verify_token returning None
        with patch("api.dependencies.auth_client") as mock_auth_client:
            mock_auth_client.verify_token = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_api_key_in_header(self):
        """Test get_current_user returns user data for valid API key in X-API-Key header"""
        # Arrange
        from api.dependencies import get_current_user

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "sk_test_valid_api_key"

        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="ignored_when_api_key_present"
        )

        expected_user = {
            "id": "api-user-456",
            "email": "api@example.com",
            "name": "API User",
            "email_verified": True,
        }

        # Mock the auth_client.verify_api_key
        with patch("api.dependencies.auth_client") as mock_auth_client:
            mock_auth_client.verify_api_key = AsyncMock(return_value=expected_user)

            # Act
            result = await get_current_user(mock_request, mock_credentials)

            # Assert
            assert result == expected_user
            mock_auth_client.verify_api_key.assert_called_once_with("sk_test_valid_api_key")

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_api_key_raises_401(self):
        """Test get_current_user raises 401 for invalid API key"""
        # Arrange
        from api.dependencies import get_current_user

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "invalid_api_key"

        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="ignored")

        # Mock the auth_client.verify_api_key returning None
        with patch("api.dependencies.auth_client") as mock_auth_client:
            mock_auth_client.verify_api_key = AsyncMock(return_value=None)

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_prioritizes_api_key_over_jwt(self):
        """Test that X-API-Key header takes precedence over Bearer token"""
        # Arrange
        from api.dependencies import get_current_user

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "sk_test_api_key"

        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="jwt_token_should_be_ignored"
        )

        api_key_user = {
            "id": "api-user-789",
            "email": "apikey@example.com",
            "name": "API Key User",
            "email_verified": True,
        }

        # Mock only verify_api_key
        with patch("api.dependencies.auth_client") as mock_auth_client:
            mock_auth_client.verify_api_key = AsyncMock(return_value=api_key_user)
            mock_auth_client.verify_token = AsyncMock()  # Should not be called

            # Act
            result = await get_current_user(mock_request, mock_credentials)

            # Assert
            assert result == api_key_user
            mock_auth_client.verify_api_key.assert_called_once()
            mock_auth_client.verify_token.assert_not_called()


class TestGetCurrentUserOptional:
    """Test suite for get_current_user_optional dependency"""

    @pytest.mark.asyncio
    async def test_returns_user_when_authenticated(self):
        """Test get_current_user_optional returns user when token is valid"""
        # Arrange
        from api.dependencies import get_current_user_optional

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        expected_user = {
            "id": "user-123",
            "email": "user@example.com",
            "name": "Test User",
            "email_verified": True,
        }

        # Mock get_current_user to return user
        with patch("api.dependencies.get_current_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = expected_user

            # Act
            result = await get_current_user_optional(mock_request)

            # Assert
            assert result == expected_user

    @pytest.mark.asyncio
    async def test_returns_none_when_not_authenticated(self):
        """Test get_current_user_optional returns None when authentication fails"""
        # Arrange
        from api.dependencies import get_current_user_optional

        mock_request = MagicMock()

        # Mock get_current_user to raise HTTPException
        with patch("api.dependencies.get_current_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

            # Act
            result = await get_current_user_optional(mock_request)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_credentials(self):
        """Test get_current_user_optional returns None when no credentials provided"""
        # Arrange
        from api.dependencies import get_current_user_optional

        mock_request = MagicMock()

        # Mock get_current_user to raise HTTPException for missing credentials
        with patch("api.dependencies.get_current_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )

            # Act
            result = await get_current_user_optional(mock_request)

            # Assert
            assert result is None


class TestGetApiKey:
    """Test suite for get_api_key dependency"""

    @pytest.mark.asyncio
    async def test_get_api_key_from_x_api_key_header(self):
        """Test get_api_key extracts API key from X-API-Key header"""
        # Arrange
        from api.dependencies import get_api_key

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "sk_test_1234567890"

        # Act
        result = await get_api_key(mock_request)

        # Assert
        assert result == "sk_test_1234567890"
        mock_request.headers.get.assert_called_once_with("x-api-key")

    @pytest.mark.asyncio
    async def test_get_api_key_raises_401_when_missing(self):
        """Test get_api_key raises 401 when X-API-Key header is missing"""
        # Arrange
        from api.dependencies import get_api_key

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(mock_request)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "X-API-Key header required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_api_key_case_insensitive_header(self):
        """Test that header lookup is case-insensitive"""
        # Arrange
        from api.dependencies import get_api_key

        mock_request = MagicMock()
        # FastAPI normalizes headers to lowercase
        mock_request.headers.get.return_value = "sk_test_key"

        # Act
        result = await get_api_key(mock_request)

        # Assert
        assert result == "sk_test_key"
