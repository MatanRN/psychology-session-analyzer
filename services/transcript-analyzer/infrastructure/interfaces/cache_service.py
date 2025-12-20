"""Abstract interface for cache service operations."""

from abc import ABC, abstractmethod


class CacheService(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> str | None:
        """
        Retrieves a value from cache.

        Args:
            key: The cache key.

        Returns:
            The cached value or None if not found.

        Raises:
            CacheServiceError: If the cache operation fails.
        """
        pass

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """
        Stores a value in cache.

        Args:
            key: The cache key.
            value: The value to cache.

        Raises:
            CacheServiceError: If the cache operation fails.
        """
        pass
