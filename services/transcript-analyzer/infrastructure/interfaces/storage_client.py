"""Abstract interface for file storage operations."""

from abc import ABC, abstractmethod


class StorageClient(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    def download_text(self, bucket_name: str, object_name: str) -> str:
        """
        Downloads a text file from storage.

        Args:
            bucket_name: The storage bucket name.
            object_name: The object path/name in storage.

        Returns:
            The file contents as a string.

        Raises:
            StorageDownloadError: If the download fails.
        """
        pass

    @abstractmethod
    def ensure_bucket_exists(self, bucket_name: str) -> None:
        """
        Ensures a bucket exists, creating it if necessary.

        Args:
            bucket_name: The bucket name to ensure exists.
        """
        pass
