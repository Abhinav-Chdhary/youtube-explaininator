import hashlib
import json
import redis.asyncio as redis
from app.config import settings


class Cache:
    """Redis-based exact-match cache for query results.

    Crucial with Claude's 5 req/min rate limit — avoids
    burning API calls on repeated questions.
    """

    def __init__(self):
        self._redis: redis.Redis | None = None

    async def connect(self):
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self):
        if self._redis:
            await self._redis.close()

    def _make_key(self, video_id: str, question: str, language: str) -> str:
        """Deterministic cache key from query parameters."""
        raw = f"{video_id}:{question.strip().lower()}:{language}"
        return f"yt_cache:{hashlib.sha256(raw.encode()).hexdigest()}"

    async def get(self, video_id: str, question: str, language: str) -> str | None:
        """Return cached answer or None."""
        if not self._redis:
            return None
        key = self._make_key(video_id, question, language)
        return await self._redis.get(key)

    async def set(self, video_id: str, question: str, language: str, answer: str):
        """Cache an answer with TTL."""
        if not self._redis:
            return
        key = self._make_key(video_id, question, language)
        await self._redis.set(key, answer, ex=settings.cache_ttl)


cache = Cache()
