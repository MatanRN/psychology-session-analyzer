"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from psychology_common import MinioConfig, QueueConfig, RabbitMQConfig
from pydantic import BaseModel


class RedisConfig(BaseModel, frozen=True):
    """Redis connection configuration."""

    host: str
    cache_ttl_seconds: int = 86400  # 24 hours default


class GeminiConfig(BaseModel, frozen=True):
    """Gemini LLM configuration."""

    api_key: str
    model_name: str = "gemini-2.5-flash-lite"
    system_prompt_path: Path = Path("system.txt")


class PostgresConfig(BaseModel, frozen=True):
    """PostgreSQL connection configuration."""

    host: str
    user: str
    password: str
    port: int
    database: str


class AppConfig(BaseModel, frozen=True):
    """Root application configuration."""

    minio: MinioConfig
    redis: RedisConfig
    gemini: GeminiConfig
    rabbitmq: RabbitMQConfig
    postgres: PostgresConfig


def load_config() -> AppConfig:
    """Loads configuration from environment variables."""
    return AppConfig(
        minio=MinioConfig(
            endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            user=os.getenv("MINIO_USER", ""),
            password=os.getenv("MINIO_PASSWORD", ""),
        ),
        redis=RedisConfig(
            host=os.getenv("REDIS_HOST", "redis"),
            cache_ttl_seconds=int(os.getenv("REDIS_CACHE_TTL_SECONDS", "86400")),
        ),
        gemini=GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY", ""),
        ),
        rabbitmq=RabbitMQConfig(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            user=os.getenv("RABBITMQ_USER", ""),
            password=os.getenv("RABBITMQ_PASSWORD", ""),
            queue_config=QueueConfig(
                name="transcript_analysis_queue",
                queue_type="quorum",
                max_delivery_count=3,
                expected_routing_key="audio.transcription.completed",
                success_routing_key="transcript.analysis.completed",
                dlq_name="dlq_transcript_analyzer",
                dlq_exchange_name="dead_letter_exchange",
                dlq_routing_key="transcript.analysis.failed",
            ),
        ),
        postgres=PostgresConfig(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            user=os.getenv("POSTGRES_USER", ""),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            port=int(os.getenv("POSTGRES_PORT", "5433")),
            database=os.getenv("POSTGRES_DB", ""),
        ),
    )
