"""MinIO implementation of the StorageClient interface."""

from typing import BinaryIO

from minio import Minio
from psychology_common.logging import setup_logging

from exceptions import StorageUploadError
from interfaces import StorageClient

logger = setup_logging()


class MinioStorage(StorageClient):
    """Handles file storage operations using MinIO."""

    def __init__(self, client: Minio, bucket_name: str):
        self._client = client
        self._bucket_name = bucket_name

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
    ) -> None:
        try:
            self._client.put_object(
                bucket_name=self._bucket_name,
                object_name=object_name,
                data=data,
                length=size,
                content_type=content_type,
            )
            logger.info(
                "File uploaded to MinIO",
                extra={
                    "object_name": object_name,
                    "size": size,
                    "bucket": self._bucket_name,
                },
            )
        except Exception as e:
            logger.exception(
                "MinIO upload failed",
                extra={"object_name": object_name},
            )
            raise StorageUploadError(object_name, e) from e
