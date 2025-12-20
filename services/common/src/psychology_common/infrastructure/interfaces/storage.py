"""Abstract interface for file storage operations."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageClient(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    def download(self, bucket_name: str, object_name: str) -> bytes:
        """
        Downloads a file from storage.

        Args:
            bucket_name: The storage bucket name.
            object_name: The object path/name in storage.

        Returns:
            The file contents as bytes.

        Raises:
            StorageDownloadError: If the download fails.
        """

    @abstractmethod
    def upload(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
    ) -> None:
        """
        Uploads a file to storage.

        Args:
            bucket_name: The storage bucket name.
            object_name: The destination path/name in storage.
            data: File-like object containing the data.
            size: Size of the file in bytes.
            content_type: MIME type of the file.

        Raises:
            StorageUploadError: If the upload fails.
        """

    @abstractmethod
    def ensure_bucket_exists(self, bucket_name: str) -> None:
        """
        Ensures a bucket exists, creating it if necessary.

        Args:
            bucket_name: The bucket name to ensure exists.
        """
