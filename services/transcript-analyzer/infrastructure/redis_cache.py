"""Redis cache service implementation."""

import redis
from psychology_common.logging import setup_logging

from exceptions import CacheServiceError
from infrastructure.interfaces import CacheService

logger = setup_logging()


class RedisCacheService(CacheService):
    """Cache service implementation using Redis."""

    def __init__(self, client: redis.Redis, ttl_seconds: int):
        self._client = client
        self._ttl_seconds = ttl_seconds

    def get(self, key: str) -> str | None:
        """
        Retrieves a value from Redis cache.

        Args:
            key: The cache key.

        Returns:
            The cached value or None if not found.

        Raises:
            CacheServiceError: If the Redis operation fails.
        """
        try:
            value = self._client.get(key)
            if value:
                logger.info("Cache hit", extra={"key": key})
            return value
        except redis.RedisError as e:
            logger.exception("Redis get failed", extra={"key": key})
            raise CacheServiceError(key, "get", cause=e) from e

    def set(self, key: str, value: str) -> None:
        """
        Stores a value in Redis cache with TTL.

        Args:
            key: The cache key.
            value: The value to cache.

        Raises:
            CacheServiceError: If the Redis operation fails.
        """
        try:
            self._client.set(key, value, ex=self._ttl_seconds)
            logger.info("Cache set", extra={"key": key, "ttl": self._ttl_seconds})
        except redis.RedisError as e:
            logger.exception("Redis set failed", extra={"key": key})
            raise CacheServiceError(key, "set", cause=e) from e
