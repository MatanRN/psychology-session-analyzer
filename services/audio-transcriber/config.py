"""Application configuration loaded from environment variables."""

import os

from pydantic import BaseModel


class MinioConfig(BaseModel, frozen=True):
    """MinIO connection configuration."""

    endpoint: str
    user: str
    password: str
    bucket_name: str = "sessions"


class QueueConfig(BaseModel, frozen=True):
    """RabbitMQ queue configuration."""

    name: str
    queue_type: str
    max_delivery_count: int
    expected_routing_key: str
    success_routing_key: str
    dlq_name: str
    dlq_exchange_name: str
    dlq_routing_key: str


class RabbitMQConfig(BaseModel, frozen=True):
    """RabbitMQ connection configuration."""

    host: str
    user: str
    password: str
    exchange_name: str = "events"
    queue_config: QueueConfig = QueueConfig(
        name="audio_transcription_queue",
        queue_type="quorum",
        max_delivery_count=3,
        expected_routing_key="audio.extraction.completed",
        success_routing_key="audio.transcription.completed",
        dlq_name="dlq_audio_transcriber",
        dlq_exchange_name="dead_letter_exchange",
        dlq_routing_key="audio.transcription.failed",
    )


class AssemblyAIConfig(BaseModel, frozen=True):
    """AssemblyAI API configuration."""

    api_key: str
    speaker_labels: bool = True


class AppConfig(BaseModel, frozen=True):
    """Root application configuration."""

    minio: MinioConfig
    rabbitmq: RabbitMQConfig
    assemblyai: AssemblyAIConfig


def load_config() -> AppConfig:
    """Loads configuration from environment variables."""
    return AppConfig(
        minio=MinioConfig(
            endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            user=os.getenv("MINIO_USER", ""),
            password=os.getenv("MINIO_PASSWORD", ""),
        ),
        rabbitmq=RabbitMQConfig(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            user=os.getenv("RABBITMQ_USER", ""),
            password=os.getenv("RABBITMQ_PASSWORD", ""),
        ),
        assemblyai=AssemblyAIConfig(
            api_key=os.getenv("ASSEMBLYAI_API_KEY", ""),
        ),
    )
