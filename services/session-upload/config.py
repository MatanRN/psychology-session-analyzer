"""Application configuration loaded from environment variables."""

import os

from pydantic import BaseModel


class MinioConfig(BaseModel, frozen=True):
    """Immutable MinIO connection configuration."""

    endpoint: str
    user: str
    password: str
    bucket_name: str = "sessions"


class RabbitMQConfig(BaseModel, frozen=True):
    """Immutable RabbitMQ connection configuration."""

    host: str
    user: str
    password: str
    exchange_name: str = "events"


class AppConfig(BaseModel, frozen=True):
    """Root application configuration."""

    minio: MinioConfig
    rabbitmq: RabbitMQConfig


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
    )
