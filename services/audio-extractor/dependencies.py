"""Dependency injection configuration for the audio-extractor service."""

import pika
from minio import Minio
from psychology_common import setup_logging
from psychology_common.infrastructure import MessageBroker, StorageClient

from config import load_config
from domain import AudioExtractor
from handlers import VideoMessageHandler
from infrastructure import MinioStorageClient, RabbitMQBroker
from worker import Worker

logger = setup_logging()

_config = load_config()

_minio_client = Minio(
    endpoint=_config.minio.endpoint,
    access_key=_config.minio.user,
    secret_key=_config.minio.password,
    secure=False,
)

_storage = MinioStorageClient(_minio_client)
_storage.ensure_bucket_exists(_config.minio.bucket_name)

_credentials = pika.PlainCredentials(_config.rabbitmq.user, _config.rabbitmq.password)
_parameters = pika.ConnectionParameters(
    host=_config.rabbitmq.host,
    credentials=_credentials,
    heartbeat=0,
)
_rabbit_connection = pika.BlockingConnection(_parameters)
_rabbit_channel = _rabbit_connection.channel()

_broker = RabbitMQBroker(_rabbit_channel, _config.rabbitmq)
_broker.setup()


def get_storage() -> StorageClient:
    """Returns the configured storage client."""
    return _storage


def get_broker() -> MessageBroker:
    """Returns the configured message broker."""
    return _broker


def get_extractor() -> AudioExtractor:
    """Returns the audio extractor instance."""
    return AudioExtractor()


def get_handler() -> VideoMessageHandler:
    """Returns the configured video message handler."""
    return VideoMessageHandler(_storage, get_extractor())


def get_worker() -> Worker:
    """Returns the configured worker."""
    return Worker(_broker, get_handler(), _config.rabbitmq)
