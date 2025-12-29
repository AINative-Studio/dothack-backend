"""
ZeroDB Integration Package

Provides client wrappers for ZeroDB API with retry logic and error handling.
"""

from .client import ZeroDBClient
from .exceptions import (
    ZeroDBAuthError,
    ZeroDBError,
    ZeroDBNotFound,
    ZeroDBRateLimitError,
    ZeroDBTimeoutError,
)

__all__ = [
    "ZeroDBClient",
    "ZeroDBError",
    "ZeroDBAuthError",
    "ZeroDBNotFound",
    "ZeroDBRateLimitError",
    "ZeroDBTimeoutError",
]
