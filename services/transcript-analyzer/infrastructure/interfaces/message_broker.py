"""Abstract interface for message broker operations."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class MessageBroker(ABC):
    """Abstract base class for message broker backends."""

    @abstractmethod
    def publish(self, routing_key: str, payload: dict) -> None:
        """
        Publishes a message to the broker.

        Args:
            routing_key: The routing key for message routing.
            payload: The message data as a dictionary.

        Raises:
            EventPublishError: If publishing fails.
        """
        pass

    @abstractmethod
    def acknowledge(self, delivery_tag: int) -> None:
        """
        Acknowledges successful processing of a message.

        Args:
            delivery_tag: The message delivery tag.
        """
        pass

    @abstractmethod
    def reject(self, delivery_tag: int) -> None:
        """
        Rejects a message, triggering redelivery or dead-lettering.

        Args:
            delivery_tag: The message delivery tag.
        """
        pass

    @abstractmethod
    def consume(
        self, callback: Callable[[bytes, int, dict[str, Any] | None], None]
    ) -> None:
        """
        Starts consuming messages from the configured queue.

        Args:
            callback: Function called for each message with (body, delivery_tag, headers).
        """
        pass

    @abstractmethod
    def setup_queue_infrastructure(self) -> None:
        """Sets up exchanges, queues, and bindings required by this service."""
        pass
