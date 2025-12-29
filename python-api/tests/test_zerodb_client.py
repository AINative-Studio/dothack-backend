"""
Tests for ZeroDB Client

Following TDD methodology - tests written before implementation.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from integrations.zerodb.client import ZeroDBClient
from integrations.zerodb.exceptions import (
    ZeroDBAuthError,
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBRateLimitError,
    ZeroDBTimeoutError,
)


class TestZeroDBClientInitialization:
    """Test client initialization and configuration"""

    def test_client_initialization_with_api_key(self):
        """Should initialize client with API key"""
        client = ZeroDBClient(
            api_key="test-api-key",
            project_id="test-project-id",
        )
        assert client.api_key == "test-api-key"
        assert client.project_id == "test-project-id"
        assert client.base_url == "https://api.ainative.studio"

    def test_client_initialization_with_custom_base_url(self):
        """Should allow custom base URL"""
        client = ZeroDBClient(
            api_key="test-api-key",
            project_id="test-project-id",
            base_url="https://custom.api.com",
        )
        assert client.base_url == "https://custom.api.com"

    def test_client_initialization_with_custom_timeout(self):
        """Should allow custom timeout"""
        client = ZeroDBClient(
            api_key="test-api-key",
            project_id="test-project-id",
            timeout=60.0,
        )
        assert client.timeout == 60.0

    def test_client_initialization_missing_api_key(self):
        """Should raise error when API key is missing"""
        with pytest.raises(ValueError, match="api_key is required"):
            ZeroDBClient(api_key=None, project_id="test-project")

    def test_client_initialization_missing_project_id(self):
        """Should raise error when project_id is missing"""
        with pytest.raises(ValueError, match="project_id is required"):
            ZeroDBClient(api_key="test-key", project_id=None)


class TestZeroDBClientAuthentication:
    """Test authentication header handling"""

    @pytest.mark.asyncio
    async def test_request_includes_auth_header(self):
        """Should include Authorization header in requests"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = Mock(
                status_code=200,
                json=Mock(return_value={"success": True}),
            )

            await client._request("GET", "/test")

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]
            assert "headers" in call_kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_handles_401_unauthorized(self):
        """Should raise ZeroDBAuthError on 401"""
        client = ZeroDBClient(api_key="invalid-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = Mock(
                status_code=401,
                json=Mock(return_value={"error": "Unauthorized"}),
            )

            with pytest.raises(ZeroDBAuthError, match="Authentication failed"):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_handles_403_forbidden(self):
        """Should raise ZeroDBAuthError on 403"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = Mock(
                status_code=403,
                json=Mock(return_value={"error": "Forbidden"}),
            )

            with pytest.raises(ZeroDBAuthError, match="Permission denied"):
                await client._request("GET", "/test")


class TestZeroDBClientErrorHandling:
    """Test error handling for different HTTP status codes"""

    @pytest.mark.asyncio
    async def test_handles_404_not_found(self):
        """Should raise ZeroDBNotFound on 404"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = Mock(
                status_code=404,
                json=Mock(return_value={"error": "Not found"}),
            )

            with pytest.raises(ZeroDBNotFound):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_handles_429_rate_limit(self):
        """Should raise ZeroDBRateLimitError on 429"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = Mock(
                status_code=429,
                json=Mock(return_value={"error": "Rate limit exceeded"}),
            )

            with pytest.raises(ZeroDBRateLimitError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_handles_timeout(self):
        """Should raise ZeroDBTimeoutError on timeout"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(ZeroDBTimeoutError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_handles_network_error(self):
        """Should raise ZeroDBError on network failure"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.NetworkError("Connection failed")

            with pytest.raises(ZeroDBError, match="Network error"):
                await client._request("GET", "/test")


class TestZeroDBClientRetryLogic:
    """Test retry logic with exponential backoff"""

    @pytest.mark.asyncio
    async def test_retries_on_network_failure(self):
        """Should retry up to 3 times on network failure"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            # Fail twice, then succeed
            mock_request.side_effect = [
                httpx.NetworkError("Connection failed"),
                httpx.NetworkError("Connection failed"),
                Mock(status_code=200, json=Mock(return_value={"success": True})),
            ]

            result = await client._request("GET", "/test")
            assert result == {"success": True}
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_gives_up_after_max_retries(self):
        """Should give up after 3 failed retry attempts"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.NetworkError("Connection failed")

            with pytest.raises(ZeroDBError):
                await client._request("GET", "/test")

            assert mock_request.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_does_not_retry_on_client_errors(self):
        """Should NOT retry on 4xx client errors"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = Mock(
                status_code=400,
                json=Mock(return_value={"error": "Bad request"}),
            )

            with pytest.raises(ZeroDBError):
                await client._request("GET", "/test")

            assert mock_request.call_count == 1  # No retries


class TestZeroDBClientGetProjectInfo:
    """Test get_project_info() method"""

    @pytest.mark.asyncio
    async def test_get_project_info_success(self):
        """Should fetch project info successfully"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project-123")

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "project_id": "test-project-123",
                "name": "Test Project",
                "database_enabled": True,
            }

            result = await client.get_project_info()

            assert result["project_id"] == "test-project-123"
            assert result["name"] == "Test Project"
            mock_request.assert_called_once_with("GET", "/v1/public/projects/test-project-123")


class TestZeroDBClientContextManager:
    """Test async context manager support"""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Should support async context manager"""
        async with ZeroDBClient(api_key="test-key", project_id="test-project") as client:
            assert client is not None
            assert client._http_client is not None

    @pytest.mark.asyncio
    async def test_closes_client_on_exit(self):
        """Should close HTTP client on context manager exit"""
        client = ZeroDBClient(api_key="test-key", project_id="test-project")

        with patch.object(client._http_client, "aclose", new_callable=AsyncMock) as mock_close:
            async with client:
                pass

            mock_close.assert_called_once()
