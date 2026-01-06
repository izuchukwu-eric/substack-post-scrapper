"""Token bucket rate limiter for request throttling."""

import asyncio
from collections import deque
from datetime import datetime, timedelta

import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Token bucket rate limiter for controlling request frequency."""

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
    ):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per time window
            window_seconds: Time window duration in seconds
        """
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests: deque[datetime] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request is allowed.

        This method will block if the rate limit has been reached,
        waiting until a slot becomes available.
        """
        async with self._lock:
            now = datetime.utcnow()

            # Remove requests outside the time window
            while self.requests and self.requests[0] < now - self.window:
                self.requests.popleft()

            # Check if we've hit the limit
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest = self.requests[0]
                wait_until = oldest + self.window
                wait_seconds = (wait_until - now).total_seconds()

                if wait_seconds > 0:
                    logger.info(
                        "rate_limit_wait",
                        wait_seconds=round(wait_seconds, 2),
                        current_requests=len(self.requests),
                    )
                    await asyncio.sleep(wait_seconds)

                    # Remove old request after waiting
                    if self.requests:
                        self.requests.popleft()

            # Record this request
            self.requests.append(datetime.utcnow())

    async def try_acquire(self) -> bool:
        """Try to acquire a slot without waiting.

        Returns:
            True if acquired, False if rate limited
        """
        async with self._lock:
            now = datetime.utcnow()

            # Remove requests outside the time window
            while self.requests and self.requests[0] < now - self.window:
                self.requests.popleft()

            # Check if we can proceed
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            return False

    def get_remaining(self) -> int:
        """Get the number of remaining requests allowed.

        Returns:
            Number of requests that can be made before rate limiting
        """
        now = datetime.utcnow()

        # Count requests within the window
        active_requests = sum(
            1 for r in self.requests
            if r >= now - self.window
        )

        return max(0, self.max_requests - active_requests)

    def reset(self) -> None:
        """Reset the rate limiter, clearing all tracked requests."""
        self.requests.clear()
