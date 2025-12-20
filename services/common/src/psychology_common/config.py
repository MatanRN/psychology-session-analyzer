"""Shared configuration models for infrastructure components."""

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
    queue_type: str = "quorum"
    max_delivery_count: int = 3
    expected_routing_key: str
    success_routing_key: str
    dlq_name: str
    dlq_exchange_name: str = "dead_letter_exchange"
    dlq_routing_key: str


class RabbitMQConfig(BaseModel, frozen=True):
    """RabbitMQ connection configuration."""

    host: str
    user: str
    password: str
    exchange_name: str = "events"
    queue_config: QueueConfig | None = None
