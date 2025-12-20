"""RabbitMQ implementation of the MessagePublisher interface."""

import json

from pika.adapters.blocking_connection import BlockingChannel
from psychology_common import EventPublishError, setup_logging
from psychology_common.infrastructure import MessagePublisher

logger = setup_logging()


class RabbitMQPublisher(MessagePublisher):
    """Publishes events to a RabbitMQ exchange."""

    def __init__(self, channel: BlockingChannel, exchange_name: str):
        self._channel = channel
        self._exchange_name = exchange_name

    def publish(self, routing_key: str, payload: dict) -> None:
        try:
            self._channel.basic_publish(
                exchange=self._exchange_name,
                routing_key=routing_key,
                body=json.dumps(payload),
            )
            logger.info(
                "Event published to RabbitMQ",
                extra={
                    "exchange": self._exchange_name,
                    "routing_key": routing_key,
                },
            )
        except Exception as e:
            logger.exception(
                "RabbitMQ publish failed",
                extra={"routing_key": routing_key},
            )
            raise EventPublishError(routing_key, e) from e
