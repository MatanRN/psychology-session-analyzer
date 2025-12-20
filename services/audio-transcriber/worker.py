"""Worker that handles queue message consumption and orchestration."""

import json
from typing import Any

from psychology_common import setup_logging
from psychology_common.infrastructure import MessageBroker
from pydantic import ValidationError

from config import RabbitMQConfig
from domain import AudioMessage
from handlers import AudioMessageHandler

logger = setup_logging()


class Worker:
    """Consumes messages from the queue and orchestrates processing."""

    def __init__(
        self,
        broker: MessageBroker,
        handler: AudioMessageHandler,
        config: RabbitMQConfig,
    ):
        self._broker = broker
        self._handler = handler
        self._config = config

    def start(self) -> None:
        """Starts consuming messages from the queue."""
        logger.info("Worker initialized, starting message consumption")
        self._broker.consume(self._on_message)

    def _on_message(
        self, body: bytes, delivery_tag: int, headers: dict[str, Any] | None
    ) -> None:
        """Callback for each received message."""
        delivery_count = headers.get("x-delivery-count", 1) if headers else 1

        logger.info(
            "Message received",
            extra={
                "attempt": delivery_count,
                "max_attempts": self._config.queue_config.max_delivery_count,
            },
        )

        try:
            message = AudioMessage.model_validate(json.loads(body))
        except ValidationError as e:
            logger.exception("Invalid message format", extra={"error": str(e)})
            self._broker.reject(delivery_tag)
            return

        try:
            result = self._handler.process(message)

            self._broker.acknowledge(delivery_tag)

            self._broker.publish(
                routing_key=self._config.queue_config.success_routing_key,
                payload={
                    "file_name": result.transcription_object_name,
                    "bucket_name": result.bucket_name,
                    "content_type": result.content_type,
                },
            )

            logger.info(
                "Message processed successfully",
                extra={
                    "audio_file": message.file_name,
                    "transcription_file": result.transcription_object_name,
                },
            )

        except Exception:
            logger.exception(
                "Message processing failed",
                extra={"file_name": message.file_name},
            )
            self._broker.reject(delivery_tag)
