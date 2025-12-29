"""
FastAPI Authentication Dependencies

Provides reusable dependencies for authenticating requests using AINative Studio
authentication system with custom exceptions and structured logging.
Supports both JWT tokens and API keys.
"""

import logging
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from integrations.ainative.auth_client import AINativeAuthClient
from integrations.ainative.exceptions import (
    AINativeAuthError,
    InvalidTokenError,
    InvalidAPIKeyError,
    TokenExpiredError,
    AINativeConnectionError,
    AINativeTimeoutError,
    format_error_response
)

# Configure structured logging
logger = logging.getLogger(__name__)

# Initialize HTTP Bearer security scheme
security = HTTPBearer()

# Initialize AINative authentication client
# Uses production URL by default, can be overridden with environment variable
auth_client = AINativeAuthClient()


async def get_current_user(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict[str, Any]:
    """
    Get current authenticated user from AINative

    This dependency verifies the authentication credentials and returns the user
    information. It supports two authentication methods (checked in order):

    1. API Key (X-API-Key header) - Takes precedence
    2. JWT Token (Authorization: Bearer header)

    Args:
        request: FastAPI request object (for accessing headers)
        credentials: HTTP authorization credentials (Bearer token)

    Returns:
        User dictionary containing:
            - id: User UUID
            - email: User email address
            - name: User display name
            - email_verified: Email verification status

    Raises:
        HTTPException: 401/503/504 with consistent error format

    Example:
        >>> @app.get("/protected")
        >>> async def protected_route(user: dict = Depends(get_current_user)):
        ...     return {"user_id": user["id"]}
    """
    # Check for API key in X-API-Key header (case-insensitive)
    api_key = request.headers.get("x-api-key")

    try:
        if api_key:
            # Verify API key
            logger.info(
                "Attempting authentication with API key",
                extra={
                    "event": "auth_attempt",
                    "method": "api_key",
                    "path": request.url.path
                }
            )
            user = await auth_client.verify_api_key(api_key)
            logger.info(
                "API key authentication successful",
                extra={
                    "event": "auth_success",
                    "method": "api_key",
                    "user_id": user.get("id")
                }
            )
            return user

        # Verify JWT token (from Authorization: Bearer header)
        token = credentials.credentials
        logger.info(
            "Attempting authentication with JWT token",
            extra={
                "event": "auth_attempt",
                "method": "jwt",
                "path": request.url.path
            }
        )
        user = await auth_client.verify_token(token)
        logger.info(
            "JWT token authentication successful",
            extra={
                "event": "auth_success",
                "method": "jwt",
                "user_id": user.get("id")
            }
        )
        return user

    except InvalidAPIKeyError as e:
        logger.warning(
            "Invalid API key",
            extra={
                "event": "auth_failed",
                "method": "api_key",
                "error_code": e.error_code
            }
        )
        error_response = format_error_response(e)
        raise HTTPException(
            status_code=e.status_code,
            detail=error_response,
            headers={"WWW-Authenticate": "Bearer"}
        )

    except (InvalidTokenError, TokenExpiredError) as e:
        logger.warning(
            f"Token authentication failed: {e.error_code}",
            extra={
                "event": "auth_failed",
                "method": "jwt",
                "error_code": e.error_code
            }
        )
        error_response = format_error_response(e)
        raise HTTPException(
            status_code=e.status_code,
            detail=error_response,
            headers={"WWW-Authenticate": "Bearer"}
        )

    except (AINativeConnectionError, AINativeTimeoutError) as e:
        logger.error(
            f"AINative API error: {e.error_code}",
            extra={
                "event": "auth_error",
                "error_code": e.error_code,
                "status_code": e.status_code
            }
        )
        error_response = format_error_response(e)
        raise HTTPException(
            status_code=e.status_code,
            detail=error_response
        )

    except AINativeAuthError as e:
        # Catch-all for any other auth errors
        logger.error(
            f"Authentication error: {e.error_code}",
            extra={
                "event": "auth_error",
                "error_code": e.error_code,
                "status_code": e.status_code
            }
        )
        error_response = format_error_response(e)
        raise HTTPException(
            status_code=e.status_code,
            detail=error_response
        )


async def get_current_user_optional(request: Request) -> Optional[dict[str, Any]]:
    """
    Optional authentication dependency

    Returns user information if authenticated, None otherwise.
    This is useful for endpoints that have different behavior for authenticated
    vs unauthenticated users but don't require authentication.

    Args:
        request: FastAPI request object

    Returns:
        User dictionary if authenticated, None otherwise

    Example:
        >>> @app.get("/hackathons/{id}")
        >>> async def get_hackathon(
        ...     id: str,
        ...     user: Optional[dict] = Depends(get_current_user_optional)
        ... ):
        ...     # Public endpoint with optional auth
        ...     if user:
        ...         # Show user-specific data
        ...         pass
        ...     else:
        ...         # Show public data only
        ...         pass
    """
    try:
        # Try to get user using regular authentication
        # Need to extract credentials manually for optional auth
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None

        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer":
            return None

        credentials = HTTPAuthorizationCredentials(scheme=scheme, credentials=token)
        return await get_current_user(request, credentials)

    except HTTPException:
        # Authentication failed - return None instead of raising
        logger.debug(
            "Optional authentication failed, returning None",
            extra={"event": "optional_auth_failed"}
        )
        return None


async def get_api_key(request: Request) -> str:
    """
    Extract and validate API key from request

    Extracts API key from X-API-Key header. This is a simpler dependency
    that just returns the raw API key without verification (useful for
    custom verification logic).

    Args:
        request: FastAPI request object

    Returns:
        API key string from X-API-Key header

    Raises:
        HTTPException: 401 if X-API-Key header is missing

    Example:
        >>> @app.get("/api/data")
        >>> async def get_data(api_key: str = Depends(get_api_key)):
        ...     # Custom API key validation logic
        ...     if not is_valid_key(api_key):
        ...         raise HTTPException(401)
        ...     return {"data": "..."}
    """
    api_key = request.headers.get("x-api-key")

    if not api_key:
        logger.warning(
            "Missing X-API-Key header",
            extra={"event": "auth_failed", "reason": "missing_api_key"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key header required"
        )

    return api_key
