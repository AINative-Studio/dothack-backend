"""
AINative Authentication Client

Provides integration with AINative Studio authentication system for user verification.
Supports both JWT tokens and API keys for authentication with retry logic and structured logging.
"""

import httpx
import logging
from typing import Optional, Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .exceptions import (
    InvalidTokenError,
    InvalidAPIKeyError,
    TokenExpiredError,
    AINativeConnectionError,
    AINativeTimeoutError,
)

# Configure structured logging
logger = logging.getLogger(__name__)


class AINativeAuthClient:
    """
    Client for AINative Studio authentication

    This client communicates with the AINative Auth API to verify JWT tokens
    and API keys, enabling centralized authentication across all AINative products.

    Features:
    - Automatic retry with exponential backoff (3 attempts)
    - Structured logging for all auth events
    - Custom exceptions for different failure scenarios
    - Support for both JWT tokens and API keys
    """

    def __init__(self, base_url: str = "https://api.ainative.studio"):
        """
        Initialize AINative authentication client

        Args:
            base_url: Base URL for AINative API (default: production URL)
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=10.0)  # 10 second timeout

    async def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify JWT token and get user info

        Makes a GET request to /v1/auth/me with the provided JWT token.
        Retries up to 3 times on network errors with exponential backoff.

        Args:
            token: JWT access token to verify

        Returns:
            User object with keys: id, email, name, email_verified

        Raises:
            InvalidTokenError: If token is invalid or malformed
            TokenExpiredError: If token has expired
            AINativeConnectionError: If connection fails after retries
            AINativeTimeoutError: If request times out after retries

        Example:
            >>> client = AINativeAuthClient()
            >>> user = await client.verify_token("eyJhbGciOiJIUzI1NiIs...")
            >>> print(f"User: {user['email']}")
        """
        try:
            return await self._verify_token_with_retry(token)
        except httpx.ConnectError as e:
            logger.error(
                "Connection error during token verification",
                extra={
                    "event": "token_verification_error",
                    "error_type": "connection_error",
                    "error": str(e),
                },
            )
            raise AINativeConnectionError() from e
        except httpx.TimeoutException as e:
            logger.error(
                "Timeout during token verification",
                extra={
                    "event": "token_verification_error",
                    "error_type": "timeout",
                    "error": str(e),
                },
            )
            raise AINativeTimeoutError() from e

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s, 2s, 4s
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _verify_token_with_retry(self, token: str) -> dict[str, Any]:
        """Internal method with retry logic for token verification"""
        logger.info(
            "Attempting token verification",
            extra={
                "event": "token_verification_start",
                "token_preview": token[:20] + "..." if len(token) > 20 else token,
            },
        )

        response = await self.client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

        if response.status_code == 200:
            user = response.json()
            logger.info(
                "Token verification successful",
                extra={
                    "event": "token_verification_success",
                    "user_id": user.get("id"),
                    "email": user.get("email"),
                },
            )
            return user

        elif response.status_code == 401:
            error_detail = response.json().get("detail", "Unauthorized")

            # Distinguish between expired and invalid tokens
            if "expired" in error_detail.lower():
                logger.warning(
                    "Token expired",
                    extra={
                        "event": "token_verification_failed",
                        "reason": "expired",
                        "status_code": 401,
                    },
                )
                raise TokenExpiredError()
            else:
                logger.warning(
                    "Invalid token",
                    extra={
                        "event": "token_verification_failed",
                        "reason": "invalid",
                        "status_code": 401,
                    },
                )
                raise InvalidTokenError()

        else:
            # Other status codes (403, 500, etc.)
            logger.warning(
                "Token verification failed with unexpected status",
                extra={
                    "event": "token_verification_failed",
                    "status_code": response.status_code,
                    "detail": response.text,
                },
            )
            raise InvalidTokenError(f"Authentication failed with status {response.status_code}")

    async def verify_api_key(self, api_key: str) -> dict[str, Any]:
        """
        Verify API key and get user info

        Makes a GET request to /v1/auth/me with the provided API key.
        API keys are used for server-to-server authentication.
        Retries up to 3 times on network errors with exponential backoff.

        Args:
            api_key: AINative API key to verify

        Returns:
            User object with keys: id, email, name, email_verified

        Raises:
            InvalidAPIKeyError: If API key is invalid or revoked
            AINativeConnectionError: If connection fails after retries
            AINativeTimeoutError: If request times out after retries

        Example:
            >>> client = AINativeAuthClient()
            >>> user = await client.verify_api_key("sk_test_1234567890")
            >>> print(f"API User: {user['email']}")
        """
        try:
            return await self._verify_api_key_with_retry(api_key)
        except httpx.ConnectError as e:
            logger.error(
                "Connection error during API key verification",
                extra={
                    "event": "api_key_verification_error",
                    "error_type": "connection_error",
                    "error": str(e),
                },
            )
            raise AINativeConnectionError() from e
        except httpx.TimeoutException as e:
            logger.error(
                "Timeout during API key verification",
                extra={
                    "event": "api_key_verification_error",
                    "error_type": "timeout",
                    "error": str(e),
                },
            )
            raise AINativeTimeoutError() from e

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s, 2s, 4s
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _verify_api_key_with_retry(self, api_key: str) -> dict[str, Any]:
        """Internal method with retry logic for API key verification"""
        logger.info(
            "Attempting API key verification",
            extra={
                "event": "api_key_verification_start",
                "key_preview": api_key[:10] + "..." if len(api_key) > 10 else api_key,
            },
        )

        response = await self.client.get("/v1/auth/me", headers={"X-API-Key": api_key})

        if response.status_code == 200:
            user = response.json()
            logger.info(
                "API key verification successful",
                extra={
                    "event": "api_key_verification_success",
                    "user_id": user.get("id"),
                    "email": user.get("email"),
                },
            )
            return user

        elif response.status_code == 401 or response.status_code == 403:
            logger.warning(
                "Invalid API key",
                extra={"event": "api_key_verification_failed", "status_code": response.status_code},
            )
            raise InvalidAPIKeyError()

        else:
            logger.warning(
                "API key verification failed with unexpected status",
                extra={
                    "event": "api_key_verification_failed",
                    "status_code": response.status_code,
                    "detail": response.text,
                },
            )
            raise InvalidAPIKeyError(f"Authentication failed with status {response.status_code}")

    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()
