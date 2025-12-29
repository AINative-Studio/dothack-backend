"""
ZeroDB Client Wrapper

Provides HTTP client for ZeroDB API with authentication, retry logic, and error handling.
"""

import os
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import (
    ZeroDBAuthError,
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBRateLimitError,
    ZeroDBTimeoutError,
)


class ZeroDBClient:
    """
    ZeroDB API Client with retry logic and comprehensive error handling.

    Features:
    - X-API-Key authentication via Authorization header
    - Exponential backoff retry (3 attempts)
    - Custom exceptions for different error types
    - Async context manager support
    - Configurable timeout (default 30s)

    Example:
        async with ZeroDBClient(api_key="...", project_id="...") as client:
            project = await client.get_project_info()
            print(project)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        base_url: str = "https://api.ainative.studio",
        timeout: float = 30.0,
    ):
        """
        Initialize ZeroDB client.

        Args:
            api_key: ZeroDB API key (required, or set ZERODB_API_KEY env var)
            project_id: ZeroDB project ID (required, or set ZERODB_PROJECT_ID env var)
            base_url: API base URL (default: https://api.ainative.studio)
            timeout: Request timeout in seconds (default: 30.0)

        Raises:
            ValueError: If api_key or project_id is not provided
        """
        # Load from environment if not provided
        self.api_key = api_key or os.getenv("ZERODB_API_KEY")
        self.project_id = project_id or os.getenv("ZERODB_PROJECT_ID")
        self.base_url = base_url or os.getenv("ZERODB_BASE_URL", "https://api.ainative.studio")
        self.timeout = timeout

        # Validate required parameters
        if not self.api_key:
            raise ValueError("api_key is required (set via parameter or ZERODB_API_KEY env var)")
        if not self.project_id:
            raise ValueError(
                "project_id is required (set via parameter or ZERODB_PROJECT_ID env var)"
            )

        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        # Initialize API wrappers (lazy loading)
        self._tables = None
        self._vectors = None
        self._embeddings = None
        self._events = None
        self._rlhf = None
        self._memory = None
        self._files = None

    @property
    def tables(self):
        """Access Tables API operations"""
        if self._tables is None:
            from .tables import TablesAPI

            self._tables = TablesAPI(self)
        return self._tables

    @property
    def vectors(self):
        """Access Vectors API operations"""
        if self._vectors is None:
            from .vectors import VectorsAPI

            self._vectors = VectorsAPI(self)
        return self._vectors

    @property
    def embeddings(self):
        """Access Embeddings API operations"""
        if self._embeddings is None:
            from .embeddings import EmbeddingsAPI

            self._embeddings = EmbeddingsAPI(self)
        return self._embeddings

    @property
    def events(self):
        """Access Events API operations"""
        if self._events is None:
            from .events import EventsAPI

            self._events = EventsAPI(self)
        return self._events

    @property
    def embeddings(self):
        """Access Embeddings API operations"""
        if self._embeddings is None:
            from .embeddings import EmbeddingsAPI

            self._embeddings = EmbeddingsAPI(self)
        return self._embeddings

    @property
    def rlhf(self):
        """Access RLHF API operations"""
        if self._rlhf is None:
            from .rlhf import RLHFAPI

            self._rlhf = RLHFAPI(self)
        return self._rlhf

    @property
    def memory(self):
        """Access Memory API operations"""
        if self._memory is None:
            from .memory import MemoryAPI

            self._memory = MemoryAPI(self)
        return self._memory

    @property
    def files(self):
        """Access Files API operations"""
        if self._files is None:
            from .files import FilesAPI

            self._files = FilesAPI(self)
        return self._files

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        reraise=True,
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
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., "/v1/public/projects/{id}")
            **kwargs: Additional arguments passed to httpx.request

        Returns:
            Dict: JSON response from API

        Raises:
            ZeroDBAuthError: Authentication failed (401, 403)
            ZeroDBNotFound: Resource not found (404)
            ZeroDBRateLimitError: Rate limit exceeded (429)
            ZeroDBTimeoutError: Request timed out
            ZeroDBError: Other API errors
        """
        try:
            # Make request
            response = await self._http_client.request(method, path, **kwargs)

            # Handle error status codes
            if response.status_code == 401:
                raise ZeroDBAuthError(
                    "Authentication failed - invalid API key",
                    status_code=401,
                    response=response.json() if response.content else None,
                )
            elif response.status_code == 403:
                raise ZeroDBAuthError(
                    "Permission denied - insufficient privileges",
                    status_code=403,
                    response=response.json() if response.content else None,
                )
            elif response.status_code == 404:
                raise ZeroDBNotFound(
                    "Resource not found",
                    status_code=404,
                    response=response.json() if response.content else None,
                )
            elif response.status_code == 429:
                raise ZeroDBRateLimitError(
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
                raise ZeroDBError(
                    error_msg,
                    status_code=response.status_code,
                    response=response.json() if response.content else None,
                )

            # Return successful response
            return response.json()

        except httpx.TimeoutException as e:
            raise ZeroDBTimeoutError(f"Request timed out after {self.timeout}s") from e
        except httpx.NetworkError as e:
            raise ZeroDBError(f"Network error: {str(e)}") from e
        except (ZeroDBAuthError, ZeroDBNotFound, ZeroDBRateLimitError, ZeroDBTimeoutError):
            # Re-raise ZeroDB exceptions as-is
            raise
        except Exception as e:
            raise ZeroDBError(f"Unexpected error: {str(e)}") from e

    async def get_project_info(self) -> dict[str, Any]:
        """
        Get project information.

        Returns:
            Dict containing project details (project_id, name, database_enabled, etc.)

        Raises:
            ZeroDBAuthError: If authentication fails
            ZeroDBNotFound: If project doesn't exist
            ZeroDBError: For other errors
        """
        path = f"/v1/public/projects/{self.project_id}"
        return await self._request("GET", path)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client"""
        await self._http_client.aclose()

    async def close(self):
        """Close the HTTP client connection"""
        await self._http_client.aclose()
