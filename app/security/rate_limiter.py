"""Rate limiting middleware for API endpoints."""

import time
from collections import defaultdict

import structlog
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings

logger = structlog.get_logger()


class RateLimiter:
    """Sliding window rate limiter."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window.
            window_seconds: Window duration in seconds.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed.

        Args:
            client_id: Client identifier (IP or API key).

        Returns:
            True if request is allowed.
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        self._requests[client_id] = [ts for ts in self._requests[client_id] if ts > window_start]

        if len(self._requests[client_id]) >= self.max_requests:
            return False

        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client.

        Args:
            client_id: Client identifier.

        Returns:
            Number of remaining requests.
        """
        now = time.time()
        window_start = now - self.window_seconds
        current_count = len([ts for ts in self._requests[client_id] if ts > window_start])
        return max(0, self.max_requests - current_count)


# Global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_per_minute,
    window_seconds=60,
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request with rate limiting.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with rate limit headers.
        """
        # Skip rate limiting for health check and metrics
        if request.url.path in ("/api/health", "/api/metrics"):
            return await call_next(request)

        client_id = self._get_client_id(request)

        if not rate_limiter.is_allowed(client_id):
            logger.warning("Rate limit exceeded", client_id=client_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": str(rate_limiter.window_seconds),
                    "X-RateLimit-Limit": str(rate_limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        remaining = rate_limiter.get_remaining(client_id)
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(rate_limiter.window_seconds)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting.

        Args:
            request: Incoming request.

        Returns:
            Client identifier string.
        """
        # Use API key if available, otherwise use IP
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:8]}"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        return f"ip:{request.client.host if request.client else 'unknown'}"
