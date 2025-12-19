"""RabbitMQ implementation of the MessageBroker interface."""

import json
from collections.abc import Callable
from typing import Any

from pika.adapters.blocking_connection import BlockingChannel
from psychology_common.logging import setup_logging

from config import RabbitMQConfig
from domain.exceptions import EventPublishError

from .interfaces import MessageBroker

logger = setup_logging()


class RabbitMQBroker(MessageBroker):
    """Handles message broker operations using RabbitMQ."""

    def __init__(self, channel: BlockingChannel, config: RabbitMQConfig):
        self._channel = channel
        self._config = config

    def publish(self, routing_key: str, payload: dict) -> None:
        try:
            self._channel.basic_publish(
                exchange=self._config.exchange_name,
                routing_key=routing_key,
                body=json.dumps(payload),
            )
            logger.info(
                "Event published to RabbitMQ",
                extra={
                    "exchange": self._config.exchange_name,
                    "routing_key": routing_key,
                },
            )
        except Exception as e:
            logger.exception(
                "RabbitMQ publish failed",
                extra={"routing_key": routing_key},
            )
            raise EventPublishError(routing_key, e) from e

    def acknowledge(self, delivery_tag: int) -> None:
        self._channel.basic_ack(delivery_tag=delivery_tag)

    def reject(self, delivery_tag: int) -> None:
        self._channel.basic_nack(delivery_tag=delivery_tag)

    def consume(
        self, callback: Callable[[bytes, int, dict[str, Any] | None], None]
    ) -> None:
        def on_message(ch, method, properties, body):
            headers = properties.headers if properties else None
            callback(body, method.delivery_tag, headers)

        self._channel.basic_consume(
            queue=self._config.queue_config.name,
            on_message_callback=on_message,
        )
        logger.info(
            "Message consumption started",
            extra={"queue": self._config.queue_config.name},
        )
        self._channel.start_consuming()

    def setup_queue_infrastructure(self) -> None:
        """Sets up dead-letter exchange, main exchange, queue, and bindings."""
        # Dead letter infrastructure
        self._channel.exchange_declare(
            exchange=self._config.queue_config.dlq_exchange_name,
            exchange_type="direct",
            durable=True,
        )
        self._channel.queue_declare(
            queue=self._config.queue_config.dlq_name, durable=True
        )
        self._channel.queue_bind(
            queue=self._config.queue_config.dlq_name,
            exchange=self._config.queue_config.dlq_exchange_name,
            routing_key=self._config.queue_config.dlq_routing_key,
        )

        # Main exchange
        self._channel.exchange_declare(
            exchange=self._config.exchange_name,
            exchange_type="topic",
            durable=True,
        )

        # Main queue with dead-letter configuration
        queue_args = {
            "x-queue-type": self._config.queue_config.queue_type,
            "x-delivery-limit": self._config.queue_config.max_delivery_count,
            "x-dead-letter-exchange": self._config.queue_config.dlq_exchange_name,
            "x-dead-letter-routing-key": self._config.queue_config.dlq_routing_key,
        }
        self._channel.queue_declare(
            queue=self._config.queue_config.name,
            durable=True,
            arguments=queue_args,
        )
        self._channel.queue_bind(
            queue=self._config.queue_config.name,
            exchange=self._config.exchange_name,
            routing_key=self._config.queue_config.expected_routing_key,
        )

        logger.info(
            "RabbitMQ infrastructure setup complete",
            extra={
                "queue": self._config.queue_config.name,
                "exchange": self._config.exchange_name,
            },
        )
