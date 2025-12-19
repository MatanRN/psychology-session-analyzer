"""Abstract interface for file storage operations."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageClient(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
    ) -> None:
        """
        Uploads a file to storage.

        Args:
            object_name: The destination path/name in storage.
            data: File-like object containing the data.
            size: Size of the file in bytes.
            content_type: MIME type of the file.

        Raises:
            StorageUploadError: If the upload fails.
        """
        pass
