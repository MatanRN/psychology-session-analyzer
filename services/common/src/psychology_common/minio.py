import logging

from minio import Minio

logger = logging.getLogger(__name__)


def get_minio_client(endpoint, access_key, secret_key):
    """
    Initialize and return a MinIO client using environment variables.

    Env Vars:
        MINIO_ENDPOINT: defaults to 'minio:9000'
        MINIO_USER: access key
        MINIO_PASSWORD: secret key

    Returns:
        Minio: Configured MinIO client
    """
    try:
        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )
        return client
    except Exception as e:
        logger.exception(
            "MinIO Client Initialization Failed",
            extra={
                "endpoint": endpoint,
                "user": access_key,
            },
        )
        raise e
