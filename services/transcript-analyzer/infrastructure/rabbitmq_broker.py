"""RabbitMQ message broker implementation."""

import json
from collections.abc import Callable
from typing import Any

from pika.channel import Channel
from psychology_common import (
    EventPublishError,
    QueueConfig,
    RabbitMQConfig,
    setup_logging,
)
from psychology_common.infrastructure import MessageBroker

logger = setup_logging()


class RabbitMQBroker(MessageBroker):
    """Message broker implementation using RabbitMQ."""

    def __init__(self, channel: Channel, config: RabbitMQConfig):
        self._channel = channel
        self._config = config

    def publish(self, routing_key: str, payload: dict) -> None:
        """
        Publishes a message to the configured exchange.

        Args:
            routing_key: The routing key for message routing.
            payload: The message data as a dictionary.

        Raises:
            EventPublishError: If publishing fails.
        """
        try:
            self._channel.basic_publish(
                exchange=self._config.exchange_name,
                routing_key=routing_key,
                body=json.dumps(payload),
            )
            logger.info(
                "Event published",
                extra={
                    "exchange": self._config.exchange_name,
                    "routing_key": routing_key,
                },
            )
        except Exception as e:
            logger.exception(
                "Failed to publish event", extra={"routing_key": routing_key}
            )
            raise EventPublishError(routing_key, cause=e) from e

    def acknowledge(self, delivery_tag: int) -> None:
        """Acknowledges successful processing of a message."""
        self._channel.basic_ack(delivery_tag=delivery_tag)

    def reject(self, delivery_tag: int) -> None:
        """Rejects a message, triggering redelivery."""
        self._channel.basic_nack(delivery_tag=delivery_tag, requeue=True)

    def consume(
        self, callback: Callable[[bytes, int, dict[str, Any] | None], None]
    ) -> None:
        """
        Starts consuming messages from the configured queue.

        Args:
            callback: Function called for each message with (body, delivery_tag, headers).
        """

        def on_message(ch, method, properties, body):
            headers = properties.headers if properties else None
            callback(body, method.delivery_tag, headers)

        self._channel.basic_consume(
            queue=self._config.queue_config.name,
            on_message_callback=on_message,
        )
        logger.info(
            "Started consuming",
            extra={"queue": self._config.queue_config.name},
        )
        self._channel.start_consuming()

    def setup(self) -> None:
        """Sets up exchanges, queues, and bindings for this service."""
        queue_config: QueueConfig = self._config.queue_config

        # Dead letter exchange and queue
        self._channel.exchange_declare(
            exchange=queue_config.dlq_exchange_name,
            exchange_type="direct",
            durable=True,
        )
        self._channel.queue_declare(
            queue=queue_config.dlq_name,
            durable=True,
        )
        self._channel.queue_bind(
            queue=queue_config.dlq_name,
            exchange=queue_config.dlq_exchange_name,
            routing_key=queue_config.dlq_routing_key,
        )

        # Main exchange
        self._channel.exchange_declare(
            exchange=self._config.exchange_name,
            exchange_type="topic",
            durable=True,
        )

        # Main queue with dead letter configuration
        arguments = {
            "x-queue-type": queue_config.queue_type,
            "x-delivery-limit": queue_config.max_delivery_count,
            "x-dead-letter-exchange": queue_config.dlq_exchange_name,
            "x-dead-letter-routing-key": queue_config.dlq_routing_key,
        }
        self._channel.queue_declare(
            queue=queue_config.name,
            durable=True,
            arguments=arguments,
        )
        self._channel.queue_bind(
            queue=queue_config.name,
            exchange=self._config.exchange_name,
            routing_key=queue_config.expected_routing_key,
        )

        logger.info(
            "Queue infrastructure ready",
            extra={"queue": queue_config.name, "exchange": self._config.exchange_name},
        )
