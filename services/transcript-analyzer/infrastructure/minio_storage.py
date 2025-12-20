"""MinIO storage client implementation."""

from minio import Minio
from psychology_common.logging import setup_logging

from exceptions import StorageDownloadError
from infrastructure.interfaces import StorageClient

logger = setup_logging()


class MinioStorageClient(StorageClient):
    """Storage client implementation using MinIO."""

    def __init__(self, client: Minio):
        self._client = client

    def download_text(self, bucket_name: str, object_name: str) -> str:
        """
        Downloads a text file from MinIO.

        Args:
            bucket_name: The storage bucket name.
            object_name: The object path/name in storage.

        Returns:
            The file contents as a string (UTF-8 decoded).

        Raises:
            StorageDownloadError: If the download fails.
        """
        try:
            response = self._client.get_object(bucket_name, object_name)
            try:
                data = response.data.decode("utf-8")
                logger.info(
                    "File downloaded",
                    extra={"bucket": bucket_name, "object": object_name},
                )
                return data
            finally:
                response.close()
                response.release_conn()
        except Exception as e:
            logger.exception(
                "Download failed",
                extra={"bucket": bucket_name, "object": object_name},
            )
            raise StorageDownloadError(object_name, cause=e) from e

    def ensure_bucket_exists(self, bucket_name: str) -> None:
        """
        Ensures a bucket exists in MinIO, creating it if necessary.

        Args:
            bucket_name: The bucket name to ensure exists.
        """
        if not self._client.bucket_exists(bucket_name):
            self._client.make_bucket(bucket_name)
            logger.info("Bucket created", extra={"bucket": bucket_name})
        else:
            logger.info("Bucket exists", extra={"bucket": bucket_name})
