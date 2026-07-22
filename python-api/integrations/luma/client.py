"""
Luma API Client

Provides HTTP client for Luma public API with authentication, retry logic, and error handling.
"""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import (
    LumaAuthError,
    LumaError,
    LumaNotFound,
    LumaRateLimitError,
    LumaTimeoutError,
)


class LumaClient:
    """
    Luma Public API Client with retry logic and error handling.

    Instantiated per-request with the caller's API key (not a singleton).

    Example:
        async with LumaClient(api_key="luma-...") as client:
            events = await client.list_events()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://public-api.luma.com",
        timeout: float = 30.0,
    ):
        """
        Initialize Luma client.

        Args:
            api_key: Luma API key (required).
            base_url: API base URL.
            timeout: Request timeout in seconds.
        """
        if not api_key:
            raise ValueError("api_key is required for LumaClient")

        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "x-luma-api-key": self.api_key,
                "Content-Type": "application/json",
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: API path.
            **kwargs: Additional arguments passed to httpx.request.

        Returns:
            JSON response dict.

        Raises:
            LumaAuthError: Authentication failed (401, 403).
            LumaNotFound: Resource not found (404).
            LumaRateLimitError: Rate limit exceeded (429).
            LumaTimeoutError: Request timed out.
            LumaError: Other API errors.
        """
        try:
            return await self._request_with_retry(method, path, **kwargs)
        except httpx.TimeoutException as e:
            raise LumaTimeoutError(f"Request timed out after {self.timeout}s") from e
        except httpx.NetworkError as e:
            raise LumaError(f"Network error: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(
            (httpx.NetworkError, httpx.TimeoutException, LumaRateLimitError)
        ),
        reraise=True,
    )
    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Internal method with retry logic. Retries on network errors, timeouts, and 429."""
        response = await self._http_client.request(method, path, **kwargs)

        if response.status_code == 401:
            raise LumaAuthError(
                "Authentication failed - invalid API key",
                status_code=401,
                response=response.json() if response.content else None,
            )
        elif response.status_code == 403:
            raise LumaAuthError(
                "Permission denied - insufficient privileges",
                status_code=403,
                response=response.json() if response.content else None,
            )
        elif response.status_code == 404:
            raise LumaNotFound(
                "Resource not found",
                status_code=404,
                response=response.json() if response.content else None,
            )
        elif response.status_code == 429:
            raise LumaRateLimitError(
                "Rate limit exceeded - please retry later",
                status_code=429,
                response=response.json() if response.content else None,
            )
        elif response.status_code >= 400:
            error_msg = f"API error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", error_msg)
            except Exception:
                pass
            raise LumaError(
                error_msg,
                status_code=response.status_code,
                response=response.json() if response.content else None,
            )

        return response.json()

    async def verify_key(self) -> dict:
        """Verify the API key by fetching the authenticated user profile."""
        return await self._request("GET", "/v1/users/get-self")

    async def list_events(self, cursor: str | None = None) -> dict:
        """List calendar events, optionally paginated via cursor."""
        params = {}
        if cursor:
            params["next_cursor"] = cursor
        return await self._request("GET", "/v1/calendars/events/list", params=params)

    async def get_event(self, event_id: str) -> dict:
        """Get a single event by ID."""
        return await self._request("GET", "/v1/events/get", params={"event_id": event_id})

    async def list_guests(self, event_id: str, cursor: str | None = None) -> dict:
        """List guests for an event, optionally paginated via cursor."""
        params = {"event_id": event_id}
        if cursor:
            params["next_cursor"] = cursor
        return await self._request("GET", "/v1/events/guests/list", params=params)

    async def list_contacts(self, cursor: str | None = None) -> dict:
        """List calendar contacts, optionally paginated via cursor."""
        params = {}
        if cursor:
            params["next_cursor"] = cursor
        return await self._request("GET", "/v1/calendars/contacts/list", params=params)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self._http_client.aclose()

    async def close(self):
        """Close the HTTP client connection."""
        await self._http_client.aclose()
