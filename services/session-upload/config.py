"""Application configuration loaded from environment variables."""

import os

from psychology_common import MinioConfig
from pydantic import BaseModel


class RabbitMQPublisherConfig(BaseModel, frozen=True):
    """RabbitMQ publisher configuration (no queue config needed)."""

    host: str
    user: str
    password: str
    exchange_name: str = "events"


class AppConfig(BaseModel, frozen=True):
    """Root application configuration."""

    minio: MinioConfig
    rabbitmq: RabbitMQPublisherConfig


def load_config() -> AppConfig:
    """Loads configuration from environment variables."""
    return AppConfig(
        minio=MinioConfig(
            endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            user=os.getenv("MINIO_USER", ""),
            password=os.getenv("MINIO_PASSWORD", ""),
        ),
        rabbitmq=RabbitMQPublisherConfig(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            user=os.getenv("RABBITMQ_USER", ""),
            password=os.getenv("RABBITMQ_PASSWORD", ""),
        ),
    )
