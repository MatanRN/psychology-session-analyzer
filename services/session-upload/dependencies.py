"""FastAPI dependency injection configuration."""

import pika
from minio import Minio
from psychology_common.logging import setup_logging

from config import load_config
from infrastructure import MinioStorage, RabbitMQPublisher
from interfaces import EventPublisher, StorageClient

logger = setup_logging()

_config = load_config()

_minio_client = Minio(
    endpoint=_config.minio.endpoint,
    access_key=_config.minio.user,
    secret_key=_config.minio.password,
    secure=False,
)

if not _minio_client.bucket_exists(_config.minio.bucket_name):
    _minio_client.make_bucket(_config.minio.bucket_name)
    logger.info("Bucket created", extra={"bucket_name": _config.minio.bucket_name})

_credentials = pika.PlainCredentials(_config.rabbitmq.user, _config.rabbitmq.password)
_parameters = pika.ConnectionParameters(
    host=_config.rabbitmq.host,
    credentials=_credentials,
    heartbeat=0,
)
_rabbit_connection = pika.BlockingConnection(_parameters)
_rabbit_channel = _rabbit_connection.channel()
_rabbit_channel.exchange_declare(
    exchange=_config.rabbitmq.exchange_name,
    exchange_type="topic",
    durable=True,
)


def get_storage() -> StorageClient:
    """Returns the configured storage client."""
    return MinioStorage(_minio_client, _config.minio.bucket_name)


def get_publisher() -> EventPublisher:
    """Returns the configured event publisher."""
    return RabbitMQPublisher(_rabbit_channel, _config.rabbitmq.exchange_name)
