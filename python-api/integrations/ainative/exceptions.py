"""
AINative Authentication Custom Exceptions

Provides specific error types for different authentication failure scenarios.
All exceptions include structured error codes and consistent error messaging.
"""

from datetime import datetime
from typing import Any, Optional


class AINativeAuthError(Exception):
    """Base exception for all AINative authentication errors"""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 401,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize authentication error

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (e.g., "INVALID_TOKEN")
            status_code: HTTP status code (default: 401)
            details: Optional additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class TokenExpiredError(AINativeAuthError):
    """Raised when JWT token has expired"""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message, error_code="TOKEN_EXPIRED", status_code=401)


class InvalidTokenError(AINativeAuthError):
    """Raised when JWT token is malformed or invalid"""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message, error_code="INVALID_TOKEN", status_code=401)


class InvalidAPIKeyError(AINativeAuthError):
    """Raised when API key is invalid or revoked"""

    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message=message, error_code="INVALID_API_KEY", status_code=401)


class AINativeConnectionError(AINativeAuthError):
    """Raised when unable to connect to AINative API"""

    def __init__(self, message: str = "Failed to connect to AINative API"):
        super().__init__(message=message, error_code="CONNECTION_ERROR", status_code=503)


class AINativeTimeoutError(AINativeAuthError):
    """Raised when request to AINative API times out"""

    def __init__(self, message: str = "Request to AINative API timed out"):
        super().__init__(message=message, error_code="TIMEOUT_ERROR", status_code=504)


class AuthRateLimitError(AINativeAuthError):
    """Raised when authentication rate limit is exceeded"""

    def __init__(
        self, message: str = "Too many authentication requests", retry_after: Optional[int] = None
    ):
        super().__init__(message=message, error_code="RATE_LIMIT_EXCEEDED", status_code=429)
        if retry_after:
            self.details["retry_after"] = retry_after


def format_error_response(
    error: AINativeAuthError, request_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Format authentication error as consistent JSON response

    Args:
        error: AINativeAuthError instance
        request_id: Optional request ID for tracing

    Returns:
        Dictionary with consistent error format:
        {
            "detail": "Human-readable error message",
            "error_code": "MACHINE_READABLE_CODE",
            "timestamp": "2025-12-28T12:34:56.789Z",
            "request_id": "req_123456" (optional)
        }

    Example:
        >>> error = InvalidTokenError()
        >>> response = format_error_response(error, request_id="req_abc123")
        >>> response
        {
            "detail": "Invalid token",
            "error_code": "INVALID_TOKEN",
            "timestamp": "2025-12-28T12:34:56.789Z",
            "request_id": "req_abc123"
        }
    """
    response = {
        "detail": error.message,
        "error_code": error.error_code,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if request_id:
        response["request_id"] = request_id

    # Include additional details if present
    if error.details:
        response.update(error.details)

    return response
