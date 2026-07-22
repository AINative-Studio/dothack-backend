"""
Luma API Custom Exceptions

Provides specific error types for different failure scenarios.
"""


class LumaError(Exception):
    """Base exception for all Luma API errors."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class LumaAuthError(LumaError):
    """Raised when authentication fails (401, 403)."""

    def __init__(
        self, message: str = "Authentication failed", status_code: int = 401, response: dict = None
    ):
        super().__init__(message, status_code, response)


class LumaNotFound(LumaError):
    """Raised when a resource is not found (404)."""

    def __init__(
        self, message: str = "Resource not found", status_code: int = 404, response: dict = None
    ):
        super().__init__(message, status_code, response)


class LumaRateLimitError(LumaError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self, message: str = "Rate limit exceeded", status_code: int = 429, response: dict = None
    ):
        super().__init__(message, status_code, response)


class LumaTimeoutError(LumaError):
    """Raised when request times out."""

    def __init__(self, message: str = "Request timed out", response: dict = None):
        super().__init__(message, status_code=408, response=response)
