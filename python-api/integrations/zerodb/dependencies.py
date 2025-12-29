"""
FastAPI Dependencies for ZeroDB Client

Provides reusable dependency for injecting ZeroDB client into route handlers.
"""

from functools import lru_cache

from config import settings
from .client import ZeroDBClient


@lru_cache(maxsize=1)
def get_zerodb_client() -> ZeroDBClient:
    """
    Get ZeroDB client instance (singleton via LRU cache).

    This dependency provides a ZeroDB client configured with credentials from
    the application settings. The client is cached for the lifetime of the
    application to avoid recreating connections.

    Returns:
        ZeroDBClient: Configured ZeroDB client instance

    Raises:
        ValueError: If ZERODB_API_KEY or ZERODB_PROJECT_ID is not configured

    Example:
        >>> from fastapi import Depends
        >>> from integrations.zerodb.dependencies import get_zerodb_client
        >>>
        >>> @router.get("/data")
        >>> async def get_data(zerodb: ZeroDBClient = Depends(get_zerodb_client)):
        ...     async with zerodb:
        ...         project = await zerodb.get_project_info()
        ...         return project
    """
    return ZeroDBClient(
        api_key=settings.ZERODB_API_KEY,
        project_id=settings.ZERODB_PROJECT_ID,
        base_url=settings.ZERODB_BASE_URL,
        timeout=settings.ZERODB_TIMEOUT,
    )
