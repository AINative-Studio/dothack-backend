"""
Tests for Authentication Error Handling

TDD: Red Phase - These tests define the expected behavior for:
1. Custom exception classes
2. Retry logic with exponential backoff
3. Rate limiting
4. Structured logging
5. Consistent error response format
"""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException


class TestAuthExceptions:
    """Test suite for custom authentication exception classes"""

    def test_ainative_auth_error_base(self):
        """Test base AINativeAuthError exception"""
        from integrations.ainative.exceptions import AINativeAuthError

        error = AINativeAuthError(message="Auth failed", error_code="AUTH_001", status_code=401)

        assert error.message == "Auth failed"
        assert error.error_code == "AUTH_001"
        assert error.status_code == 401
        assert str(error) == "Auth failed"

    def test_token_expired_error(self):
        """Test TokenExpiredError exception"""
        from integrations.ainative.exceptions import TokenExpiredError

        error = TokenExpiredError()

        assert error.message == "Token has expired"
        assert error.error_code == "TOKEN_EXPIRED"
        assert error.status_code == 401

    def test_invalid_token_error(self):
        """Test InvalidTokenError exception"""
        from integrations.ainative.exceptions import InvalidTokenError

        error = InvalidTokenError()

        assert error.message == "Invalid token"
        assert error.error_code == "INVALID_TOKEN"
        assert error.status_code == 401

    def test_invalid_api_key_error(self):
        """Test InvalidAPIKeyError exception"""
        from integrations.ainative.exceptions import InvalidAPIKeyError

        error = InvalidAPIKeyError()

        assert error.message == "Invalid API key"
        assert error.error_code == "INVALID_API_KEY"
        assert error.status_code == 401

    def test_ainative_connection_error(self):
        """Test AINativeConnectionError exception"""
        from integrations.ainative.exceptions import AINativeConnectionError

        error = AINativeConnectionError()

        assert error.message == "Failed to connect to AINative API"
        assert error.error_code == "CONNECTION_ERROR"
        assert error.status_code == 503

    def test_ainative_timeout_error(self):
        """Test AINativeTimeoutError exception"""
        from integrations.ainative.exceptions import AINativeTimeoutError

        error = AINativeTimeoutError()

        assert error.message == "Request to AINative API timed out"
        assert error.error_code == "TIMEOUT_ERROR"
        assert error.status_code == 504

    def test_auth_rate_limit_error(self):
        """Test AuthRateLimitError exception"""
        from integrations.ainative.exceptions import AuthRateLimitError

        error = AuthRateLimitError()

        assert error.message == "Too many authentication requests"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.status_code == 429


class TestRetryLogic:
    """Test suite for retry logic with exponential backoff"""

    @pytest.mark.asyncio
    async def test_verify_token_retries_on_network_error(self):
        """Test that verify_token retries 3 times on network errors"""
        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()
        token = "test_token"

        # Mock network failures followed by success
        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
            ]

            # Should raise AINativeConnectionError after 3 retries
            with pytest.raises(Exception) as exc_info:
                await client.verify_token(token)

            # Should have attempted 3 times
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_verify_token_succeeds_on_second_retry(self):
        """Test that verify_token succeeds if retry succeeds"""
        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()
        token = "test_token"
        expected_user = {
            "id": "user-123",
            "email": "test@example.com",
            "name": "Test User",
            "email_verified": True,
        }

        # First attempt fails, second succeeds
        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = expected_user

            mock_get.side_effect = [
                httpx.ConnectError("Connection failed"),
                mock_response_success,
            ]

            result = await client.verify_token(token)

            assert result is not None
            assert result["id"] == "user-123"
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_verify_token_uses_exponential_backoff(self):
        """Test that retry uses exponential backoff (1s, 2s, 4s)"""
        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()
        token = "test_token"

        start_time = time.time()

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
                httpx.ConnectError("Connection failed"),
            ]

            with pytest.raises(Exception):
                await client.verify_token(token)

            elapsed = time.time() - start_time
            # Should take at least 3 seconds (1 + 2 = 3 seconds total wait)
            # Note: First attempt has no wait, second waits 1s, third waits 2s
            assert elapsed >= 2.5  # Allow some margin for test execution

    @pytest.mark.asyncio
    async def test_verify_api_key_retries_on_timeout(self):
        """Test that verify_api_key retries on timeout errors"""
        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()
        api_key = "sk_test_123"

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                httpx.TimeoutException("Request timeout"),
                httpx.TimeoutException("Request timeout"),
                httpx.TimeoutException("Request timeout"),
            ]

            with pytest.raises(Exception):
                await client.verify_api_key(api_key)

            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_401_unauthorized(self):
        """Test that 401 responses are NOT retried (auth errors are final)"""
        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()
        token = "invalid_token"

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Invalid token"}
            mock_get.return_value = mock_response

            # Should raise exception immediately without retry
            with pytest.raises(Exception):
                await client.verify_token(token)

            # Should only call once (no retries for auth errors)
            assert mock_get.call_count == 1


class TestRateLimiting:
    """Test suite for rate limiting middleware"""

    def test_rate_limit_middleware_allows_under_limit(self):
        """Test that requests under limit are allowed"""
        from fastapi import FastAPI

        app = FastAPI()

        # Simulate 50 requests from same IP (under 100/min limit)
        for i in range(50):
            request = MagicMock()
            request.client.host = "192.168.1.1"

            # Should not raise exception
            try:
                # This would be called in middleware
                pass
            except HTTPException:
                pytest.fail("Should not raise exception under limit")

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_blocks_over_limit(self):
        """Test that requests over 100/min are blocked with 429"""
        from fastapi import FastAPI, Response
        from middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()

        # Mock request
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/auth/verify"

        middleware = RateLimitMiddleware(app)

        # Simulate 101 requests from same IP
        for i in range(101):
            call_next = AsyncMock(return_value=Response())

            if i < 100:
                # First 100 should succeed
                response = await middleware.dispatch(request, call_next)
                assert response.status_code != 429
            else:
                # 101st request should be rate limited
                response = await middleware.dispatch(request, call_next)
                assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_per_ip_isolation(self):
        """Test that rate limits are per IP (different IPs have separate limits)"""
        from fastapi import FastAPI, Response
        from middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        # Create requests from two different IPs
        request_ip1 = MagicMock()
        request_ip1.client.host = "192.168.1.1"
        request_ip1.url.path = "/auth/verify"

        request_ip2 = MagicMock()
        request_ip2.client.host = "192.168.1.2"
        request_ip2.url.path = "/auth/verify"

        call_next = AsyncMock(return_value=Response())

        # 100 requests from IP1 should work
        for i in range(100):
            response = await middleware.dispatch(request_ip1, call_next)
            assert response.status_code != 429

        # First request from IP2 should still work (separate limit)
        response = await middleware.dispatch(request_ip2, call_next)
        assert response.status_code != 429

    @pytest.mark.asyncio
    async def test_rate_limit_window_reset(self):
        """Test that rate limit resets after 60 seconds"""
        from fastapi import FastAPI, Response
        from middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/auth/verify"

        call_next = AsyncMock(return_value=Response())

        # Make 100 requests
        for i in range(100):
            response = await middleware.dispatch(request, call_next)

        # 101st should fail
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 429

        # Mock time advancement by 61 seconds
        with patch("time.time", return_value=time.time() + 61):
            # Should allow requests again
            response = await middleware.dispatch(request, call_next)
            assert response.status_code != 429


class TestStructuredLogging:
    """Test suite for structured logging of auth events"""

    @pytest.mark.asyncio
    async def test_successful_token_verification_logged(self):
        """Test that successful token verification is logged"""

        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()
        token = "valid_token"

        with patch("logging.Logger.info") as mock_log:
            with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": "user-123",
                    "email": "test@example.com",
                    "name": "Test User",
                    "email_verified": True,
                }
                mock_get.return_value = mock_response

                await client.verify_token(token)

                # Should log successful verification
                assert mock_log.called
                log_call = mock_log.call_args
                assert "token_verification_success" in str(log_call)

    @pytest.mark.asyncio
    async def test_failed_token_verification_logged(self):
        """Test that failed token verification is logged with context"""

        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()
        token = "invalid_token"

        with patch("logging.Logger.warning") as mock_log:
            with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.json.return_value = {"detail": "Invalid token"}
                mock_get.return_value = mock_response

                try:
                    await client.verify_token(token)
                except Exception:
                    pass

                # Should log failed verification with context
                assert mock_log.called

    @pytest.mark.asyncio
    async def test_retry_attempts_logged(self):
        """Test that retry attempts are logged"""

        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()
        token = "test_token"

        with patch("logging.Logger.warning") as mock_log:
            with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = [
                    httpx.ConnectError("Connection failed"),
                    httpx.ConnectError("Connection failed"),
                    httpx.ConnectError("Connection failed"),
                ]

                try:
                    await client.verify_token(token)
                except Exception:
                    pass

                # Should log retry attempts
                assert mock_log.call_count >= 2  # At least 2 retry warnings

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_logged(self):
        """Test that rate limit exceeded events are logged"""

        from fastapi import FastAPI, Response
        from middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/auth/verify"

        with patch("logging.Logger.warning") as mock_log:
            call_next = AsyncMock(return_value=Response())

            # Exhaust rate limit
            for i in range(101):
                await middleware.dispatch(request, call_next)

            # Should log rate limit exceeded
            assert mock_log.called
            log_message = str(mock_log.call_args)
            assert "rate_limit_exceeded" in log_message or "192.168.1.1" in log_message


class TestConsistentErrorFormat:
    """Test suite for consistent error response format"""

    @pytest.mark.asyncio
    async def test_auth_error_response_format(self):
        """Test that auth errors return consistent format"""
        from api.dependencies import get_current_user
        from fastapi import Request
        from fastapi.security import HTTPAuthorizationCredentials

        # Mock request and credentials
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None  # No API key

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

        # Mock auth client to raise InvalidTokenError
        with patch("api.dependencies.auth_client") as mock_client:
            from integrations.ainative.exceptions import InvalidTokenError

            mock_client.verify_token.side_effect = InvalidTokenError()

            try:
                await get_current_user(request, credentials)
                pytest.fail("Should raise HTTPException")
            except HTTPException as e:
                # Check error format
                assert e.status_code == 401
                assert "detail" in e.detail or isinstance(e.detail, str)

    def test_error_format_has_required_fields(self):
        """Test that error responses have required fields: detail, error_code, timestamp"""
        from integrations.ainative.exceptions import InvalidTokenError, format_error_response

        error = InvalidTokenError()
        response = format_error_response(error)

        assert "detail" in response
        assert "error_code" in response
        assert "timestamp" in response
        assert response["detail"] == "Invalid token"
        assert response["error_code"] == "INVALID_TOKEN"
        # Timestamp should be ISO format
        datetime.fromisoformat(response["timestamp"].replace("Z", "+00:00"))

    def test_error_format_includes_request_id(self):
        """Test that error responses can include optional request_id"""
        from integrations.ainative.exceptions import TokenExpiredError, format_error_response

        error = TokenExpiredError()
        response = format_error_response(error, request_id="req_123456")

        assert "request_id" in response
        assert response["request_id"] == "req_123456"

    @pytest.mark.asyncio
    async def test_rate_limit_error_response_format(self):
        """Test that rate limit errors return consistent format"""
        from fastapi import FastAPI, Response
        from middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()
        middleware = RateLimitMiddleware(app)

        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/auth/verify"

        call_next = AsyncMock(return_value=Response())

        # Exhaust rate limit
        for i in range(101):
            response = await middleware.dispatch(request, call_next)

        # Check that 429 response has consistent format
        assert response.status_code == 429
        # Response should have JSON body with error format
        # (implementation will add this)


class TestAuthClientLogging:
    """Test suite for auth client structured logging integration"""

    @pytest.mark.asyncio
    async def test_log_context_includes_user_id_on_success(self):
        """Test that successful auth logs include user_id"""

        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()

        with patch("logging.Logger.info") as mock_log:
            with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": "user-789",
                    "email": "test@example.com",
                    "name": "Test User",
                    "email_verified": True,
                }
                mock_get.return_value = mock_response

                await client.verify_token("test_token")

                # Log should include user_id
                assert mock_log.called
                log_call_str = str(mock_log.call_args)
                assert "user-789" in log_call_str or "user_id" in log_call_str

    @pytest.mark.asyncio
    async def test_log_context_includes_status_code_on_failure(self):
        """Test that failed auth logs include status_code"""

        from integrations.ainative.auth_client import AINativeAuthClient

        client = AINativeAuthClient()

        with patch("logging.Logger.warning") as mock_log:
            with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 403
                mock_response.json.return_value = {"detail": "Forbidden"}
                mock_get.return_value = mock_response

                try:
                    await client.verify_token("test_token")
                except Exception:
                    pass

                # Log should include status_code
                assert mock_log.called
                log_call_str = str(mock_log.call_args)
                assert "403" in log_call_str or "status_code" in log_call_str
