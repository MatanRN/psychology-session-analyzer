"""Dependency injection configuration for the audio-transcriber service."""

import assemblyai as aai
import pika
from minio import Minio
from psychology_common import setup_logging
from psychology_common.infrastructure import MessageBroker, StorageClient

from config import load_config
from domain import TranscriptBuilder
from handlers import AudioMessageHandler
from infrastructure import AssemblyAITranscriber, MinioStorageClient, RabbitMQBroker
from infrastructure.interfaces import TranscriptionService
from worker import Worker

logger = setup_logging()

_config = load_config()

# MinIO setup
_minio_client = Minio(
    endpoint=_config.minio.endpoint,
    access_key=_config.minio.user,
    secret_key=_config.minio.password,
    secure=False,
)

_storage = MinioStorageClient(_minio_client)
_storage.ensure_bucket_exists(_config.minio.bucket_name)

# RabbitMQ setup
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

# AssemblyAI setup
aai.settings.api_key = _config.assemblyai.api_key
_aai_config = aai.TranscriptionConfig(speaker_labels=_config.assemblyai.speaker_labels)
_aai_transcriber = aai.Transcriber(config=_aai_config)

_transcription_service = AssemblyAITranscriber(_aai_transcriber)


def get_storage() -> StorageClient:
    """Returns the configured storage client."""
    return _storage


def get_broker() -> MessageBroker:
    """Returns the configured message broker."""
    return _broker


def get_transcription_service() -> TranscriptionService:
    """Returns the configured transcription service."""
    return _transcription_service


def get_handler() -> AudioMessageHandler:
    """Returns the configured audio message handler."""
    return AudioMessageHandler(_storage, _transcription_service, TranscriptBuilder())


def get_worker() -> Worker:
    """Returns the configured worker."""
    return Worker(_broker, get_handler(), _config.rabbitmq)
