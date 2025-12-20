"""Dependency injection configuration for the transcript-analyzer service."""

from contextlib import contextmanager
from pathlib import Path

import pika
import redis
from google import genai
from minio import Minio
from psychology_common.logging import setup_logging
from sqlmodel import Session, SQLModel, create_engine

from config import load_config
from domain.transcript_analyzer import TranscriptAnalyzer
from handlers import TranscriptMessageHandler
from infrastructure import (
    GeminiLLMService,
    MinioStorageClient,
    RabbitMQBroker,
    RedisCacheService,
)
from repositories import SessionRepository
from worker import Worker

logger = setup_logging()

_config = load_config()

# MinIO storage
_minio_client = Minio(
    endpoint=_config.minio.endpoint,
    access_key=_config.minio.user,
    secret_key=_config.minio.password,
    secure=False,
)
_storage = MinioStorageClient(_minio_client)
_storage.ensure_bucket_exists(_config.minio.bucket_name)

# Redis cache
_redis_client = redis.Redis(
    host=_config.redis.host,
    decode_responses=True,
)
if not _redis_client.ping():
    logger.error("Redis connection failed", extra={"host": _config.redis.host})
    raise ConnectionError("Redis connection failed")
_cache = RedisCacheService(_redis_client, _config.redis.cache_ttl_seconds)

# Gemini LLM
_gemini_client = genai.Client(api_key=_config.gemini.api_key)
_system_prompt_path = Path(__file__).parent / _config.gemini.system_prompt_path
_system_prompt = _system_prompt_path.read_text(encoding="utf-8")
_llm = GeminiLLMService(_gemini_client, _config.gemini.model_name, _system_prompt)

# PostgreSQL database
_db_url = (
    f"postgresql+psycopg://{_config.postgres.user}:{_config.postgres.password}"
    f"@{_config.postgres.host}:{_config.postgres.port}/{_config.postgres.database}"
)
_db_engine = create_engine(_db_url)
SQLModel.metadata.create_all(_db_engine)
logger.info("Database initialized", extra={"host": _config.postgres.host})


@contextmanager
def _session_factory():
    """Creates a database session context manager."""
    with Session(_db_engine) as session:
        yield session


_repository = SessionRepository(_session_factory)

# RabbitMQ broker
_credentials = pika.PlainCredentials(_config.rabbitmq.user, _config.rabbitmq.password)
_parameters = pika.ConnectionParameters(
    host=_config.rabbitmq.host,
    credentials=_credentials,
    heartbeat=0,
)
_rabbit_connection = pika.BlockingConnection(_parameters)
_rabbit_channel = _rabbit_connection.channel()
_broker = RabbitMQBroker(_rabbit_channel, _config.rabbitmq)
_broker.setup_queue_infrastructure()

# Service composition
_analyzer = TranscriptAnalyzer(_llm, _cache)
_handler = TranscriptMessageHandler(_storage, _analyzer, _repository)


def get_worker() -> Worker:
    """Returns the configured worker instance."""
    return Worker(_broker, _handler, _config.rabbitmq)
