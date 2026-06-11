import logging
import time

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Service providing caching functionality, falling back to in-memory cache if Redis is offline."""

    def __init__(self):
        """Initializes CacheService by attempting to connect to Redis.
        
        If Redis connection fails and the application is not in production,
        falls back to a standard in-memory dictionary-based local cache.
        """
        self.client = None
        self.backend = "none"
        self._memory_cache: dict[str, tuple[str, float]] = {}
        try:
            if settings.REDIS_URL:
                self.client = redis.Redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_timeout=2
                )
            else:
                # Connect to Redis using config values
                self.client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_timeout=2
                )
            self.client.ping()
            self.backend = "redis"
            logger.info(
                "Connected to Redis cache",
                extra={
                    "url": settings.REDIS_URL,
                    "host": settings.REDIS_HOST,
                    "port": settings.REDIS_PORT,
                },
            )
        except Exception as exc:
            self.client = None
            if settings.is_production:
                logger.warning("Redis cache unavailable in production", extra={"error": exc.__class__.__name__})
            else:
                self.backend = "memory"
                logger.warning(
                    "Redis cache unavailable; using in-memory development cache",
                    extra={"error": exc.__class__.__name__},
                )

    def get(self, key: str) -> str | None:
        """Retrieves a value from the active cache backend by its key.

        Args:
            key: The unique string lookup key.

        Returns:
            The cached string value, or None if the key is missing or expired.
        """
        if self.backend == "memory":
            cached = self._memory_cache.get(key)
            if not cached:
                return None
            value, expires_at = cached
            if expires_at < time.time():
                self._memory_cache.pop(key, None)
                return None
            return value

        if not self.client:
            return None
        try:
            return self.client.get(key)
        except Exception as exc:
            logger.warning("Cache get failed", extra={"backend": self.backend, "error": exc.__class__.__name__})
            return None

    def set(self, key: str, value: str, expire_seconds: int = 3600):
        """Stores a key-value pair in the active cache backend with an expiration time.

        Args:
            key: The unique key to identify the cached value.
            value: The string content to cache.
            expire_seconds: The TTL expiration timer in seconds (defaults to 3600).
        """
        if self.backend == "memory":
            self._memory_cache[key] = (value, time.time() + expire_seconds)
            return

        if not self.client:
            return
        try:
            self.client.set(key, value, ex=expire_seconds)
        except Exception as exc:
            logger.warning("Cache set failed", extra={"backend": self.backend, "error": exc.__class__.__name__})

    def ping(self) -> bool:
        """Pings the cache backend to check status.

        Returns:
            True if the cache is responsive, False otherwise.
        """
        if self.backend == "memory":
            return True
        if not self.client:
            raise RuntimeError("Redis client is not configured")
        return bool(self.client.ping())

cache_service = CacheService()
