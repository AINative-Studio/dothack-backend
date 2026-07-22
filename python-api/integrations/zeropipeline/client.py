"""
ZeroPipeline API Client

Provides HTTP client for ZeroPipeline CRM API with authentication, retry logic, and error handling.
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
    ZeroPipelineAuthError,
    ZeroPipelineError,
    ZeroPipelineNotFound,
    ZeroPipelineRateLimitError,
    ZeroPipelineTimeoutError,
)


class ZeroPipelineClient:
    """
    ZeroPipeline CRM API Client with retry logic and error handling.

    Instantiated per-request with the caller's API key (not a singleton).

    Example:
        async with ZeroPipelineClient(api_key="zpk-...") as client:
            pipelines = await client.list_pipelines()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://pipeline.ainative.studio/api/v1",
        timeout: float = 30.0,
    ):
        """
        Initialize ZeroPipeline client.

        Args:
            api_key: ZeroPipeline API key (required).
            base_url: API base URL.
            timeout: Request timeout in seconds.
        """
        if not api_key:
            raise ValueError("api_key is required for ZeroPipelineClient")

        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
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
            ZeroPipelineAuthError: Authentication failed (401, 403).
            ZeroPipelineNotFound: Resource not found (404).
            ZeroPipelineRateLimitError: Rate limit exceeded (429).
            ZeroPipelineTimeoutError: Request timed out.
            ZeroPipelineError: Other API errors.
        """
        try:
            return await self._request_with_retry(method, path, **kwargs)
        except httpx.TimeoutException as e:
            raise ZeroPipelineTimeoutError(f"Request timed out after {self.timeout}s") from e
        except httpx.NetworkError as e:
            raise ZeroPipelineError(f"Network error: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(
            (httpx.NetworkError, httpx.TimeoutException, ZeroPipelineRateLimitError)
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
            raise ZeroPipelineAuthError(
                "Authentication failed - invalid API key",
                status_code=401,
                response=response.json() if response.content else None,
            )
        elif response.status_code == 403:
            raise ZeroPipelineAuthError(
                "Permission denied - insufficient privileges",
                status_code=403,
                response=response.json() if response.content else None,
            )
        elif response.status_code == 404:
            raise ZeroPipelineNotFound(
                "Resource not found",
                status_code=404,
                response=response.json() if response.content else None,
            )
        elif response.status_code == 429:
            raise ZeroPipelineRateLimitError(
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
            raise ZeroPipelineError(
                error_msg,
                status_code=response.status_code,
                response=response.json() if response.content else None,
            )

        return response.json()

    async def verify_key(self) -> dict:
        """Verify the API key by fetching the authenticated user profile."""
        return await self._request("GET", "/me")

    async def list_pipelines(self, limit: int = 25, offset: int = 0) -> dict:
        """List pipelines, with pagination."""
        params = {"limit": limit, "offset": offset}
        return await self._request("GET", "/pipelines", params=params)

    async def get_pipeline(self, pipeline_id: str) -> dict:
        """Get a single pipeline by ID."""
        return await self._request("GET", f"/pipelines/{pipeline_id}")

    async def list_deals(
        self, pipeline_id: str | None = None, limit: int = 25, offset: int = 0
    ) -> dict:
        """List deals, optionally filtered by pipeline, with pagination."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if pipeline_id:
            params["pipeline_id"] = pipeline_id
        return await self._request("GET", "/deals", params=params)

    async def get_deal(self, deal_id: str) -> dict:
        """Get a single deal by ID."""
        return await self._request("GET", f"/deals/{deal_id}")

    async def list_customers(self, limit: int = 25, offset: int = 0) -> dict:
        """List customers, with pagination."""
        params = {"limit": limit, "offset": offset}
        return await self._request("GET", "/customers", params=params)

    async def get_customer(self, customer_id: str) -> dict:
        """Get a single customer by ID."""
        return await self._request("GET", f"/customers/{customer_id}")

    async def list_tasks(self, limit: int = 25, offset: int = 0) -> dict:
        """List tasks, with pagination."""
        params = {"limit": limit, "offset": offset}
        return await self._request("GET", "/tasks", params=params)

    async def get_analytics_dashboard(self) -> dict:
        """Get the analytics dashboard data."""
        return await self._request("GET", "/analytics/dashboard")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self._http_client.aclose()

    async def close(self):
        """Close the HTTP client connection."""
        await self._http_client.aclose()
