import asyncio
import time
from collections import deque


class RateLimiter:
    """Sliding window rate limiter for Claude API (5 req/min, 4K tokens/min)."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until a request slot is available."""
        async with self._lock:
            now = time.monotonic()

            # Evict expired timestamps
            while self._timestamps and self._timestamps[0] < now - self.window_seconds:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_requests:
                wait_time = self._timestamps[0] + self.window_seconds - now
                await asyncio.sleep(wait_time)
                return await self._acquire_inner()

            self._timestamps.append(now)

    async def _acquire_inner(self):
        """Re-check after waiting (called without the outer lock)."""
        now = time.monotonic()
        while self._timestamps and self._timestamps[0] < now - self.window_seconds:
            self._timestamps.popleft()
        self._timestamps.append(now)
