"""MinIO implementation of the StorageClient interface."""

from typing import BinaryIO

from minio import Minio
from psychology_common import StorageDownloadError, StorageUploadError, setup_logging
from psychology_common.infrastructure import StorageClient

logger = setup_logging()


class MinioStorageClient(StorageClient):
    """Handles file storage operations using MinIO."""

    def __init__(self, client: Minio):
        self._client = client

    def download(self, bucket_name: str, object_name: str) -> bytes:
        try:
            response = self._client.get_object(bucket_name, object_name)
            data = response.data
            response.close()
            response.release_conn()
            logger.info(
                "File downloaded from MinIO",
                extra={"bucket_name": bucket_name, "object_name": object_name},
            )
            return data
        except Exception as e:
            logger.exception(
                "MinIO download failed",
                extra={"bucket_name": bucket_name, "object_name": object_name},
            )
            raise StorageDownloadError(object_name, e) from e

    def upload(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
    ) -> None:
        try:
            self._client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data,
                length=size,
                content_type=content_type,
            )
            logger.info(
                "File uploaded to MinIO",
                extra={
                    "bucket_name": bucket_name,
                    "object_name": object_name,
                },
            )
        except Exception as e:
            logger.exception(
                "MinIO upload failed",
                extra={"bucket_name": bucket_name, "object_name": object_name},
            )
            raise StorageUploadError(object_name, e) from e

    def ensure_bucket_exists(self, bucket_name: str) -> None:
        if not self._client.bucket_exists(bucket_name):
            self._client.make_bucket(bucket_name)
            logger.info("Bucket created", extra={"bucket_name": bucket_name})
        else:
            logger.info("Bucket already exists", extra={"bucket_name": bucket_name})
