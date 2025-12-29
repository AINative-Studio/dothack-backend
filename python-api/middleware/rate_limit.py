"""
Rate Limiting Middleware

Implements per-IP rate limiting for authentication endpoints to prevent abuse.
Limit: 100 requests per minute per IP address.
"""
import logging
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from integrations.ainative.exceptions import AuthRateLimitError, format_error_response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for authentication endpoints

    Tracks requests per IP address and enforces a limit of 100 requests
    per 60-second window. When limit is exceeded, returns 429 status code
    with consistent error format.

    Features:
    - Per-IP rate limiting
    - 60-second sliding window
    - Automatic cleanup of expired entries
    - Structured logging of rate limit events
    """

    def __init__(self, app, limit: int = 100, window: int = 60):
        """
        Initialize rate limiting middleware

        Args:
            app: FastAPI application instance
            limit: Maximum requests per window (default: 100)
            window: Time window in seconds (default: 60)
        """
        super().__init__(app)
        self.limit = limit
        self.window = window

        # Store: IP -> (timestamp, count)
        self.requests: dict[str, tuple[float, int]] = defaultdict(lambda: (time.time(), 0))

        # Last cleanup time
        self.last_cleanup = time.time()

    def _cleanup_old_entries(self):
        """Remove entries older than the time window"""
        current_time = time.time()

        # Only cleanup every 60 seconds
        if current_time - self.last_cleanup < self.window:
            return

        expired_ips = [
            ip for ip, (timestamp, _) in self.requests.items()
            if current_time - timestamp > self.window
        ]

        for ip in expired_ips:
            del self.requests[ip]

        self.last_cleanup = current_time

        if expired_ips:
            logger.debug(
                f"Cleaned up rate limit entries for {len(expired_ips)} IPs",
                extra={
                    "event": "rate_limit_cleanup",
                    "expired_count": len(expired_ips)
                }
            )

    def _check_rate_limit(self, ip: str) -> tuple[bool, int]:
        """
        Check if IP has exceeded rate limit

        Args:
            ip: Client IP address

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        current_time = time.time()
        timestamp, count = self.requests[ip]

        # Check if we're in a new window
        if current_time - timestamp >= self.window:
            # Reset counter for new window
            self.requests[ip] = (current_time, 1)
            return True, self.limit - 1

        # Check if limit exceeded in current window
        if count >= self.limit:
            remaining = 0
            return False, remaining

        # Increment counter
        self.requests[ip] = (timestamp, count + 1)
        remaining = self.limit - (count + 1)
        return True, remaining

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response object (normal response or 429 if rate limited)
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Periodic cleanup
        self._cleanup_old_entries()

        # Check rate limit
        allowed, remaining = self._check_rate_limit(client_ip)

        if not allowed:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}",
                extra={
                    "event": "rate_limit_exceeded",
                    "ip": client_ip,
                    "path": request.url.path,
                    "limit": self.limit,
                    "window": self.window
                }
            )

            # Calculate retry-after (seconds until window resets)
            timestamp, _ = self.requests[client_ip]
            retry_after = int(self.window - (time.time() - timestamp)) + 1

            # Create error response
            error = AuthRateLimitError(retry_after=retry_after)
            error_response = format_error_response(error)

            return JSONResponse(
                status_code=429,
                content=error_response,
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(timestamp + self.window)),
                    "Retry-After": str(retry_after)
                }
            )

        # Request allowed - add rate limit headers to response
        response = await call_next(request)

        # Add rate limit info headers
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        timestamp, _ = self.requests[client_ip]
        response.headers["X-RateLimit-Reset"] = str(int(timestamp + self.window))

        return response


def rate_limit_middleware(app, limit: int = 100, window: int = 60):
    """
    Convenience function to add rate limiting middleware to FastAPI app

    Args:
        app: FastAPI application instance
        limit: Maximum requests per window (default: 100)
        window: Time window in seconds (default: 60)

    Example:
        >>> from fastapi import FastAPI
        >>> from middleware.rate_limit import rate_limit_middleware
        >>>
        >>> app = FastAPI()
        >>> rate_limit_middleware(app, limit=100, window=60)
    """
    app.add_middleware(RateLimitMiddleware, limit=limit, window=window)
