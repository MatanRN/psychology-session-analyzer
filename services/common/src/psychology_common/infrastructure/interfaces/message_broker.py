"""Abstract interfaces for message broker operations."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class MessagePublisher(ABC):
    """Abstract base class for publishing messages to a broker."""

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


class MessageBroker(MessagePublisher, ABC):
    """Abstract base class for full message broker operations (publish + consume)."""

    @abstractmethod
    def acknowledge(self, delivery_tag: int) -> None:
        """
        Acknowledges successful processing of a message.

        Args:
            delivery_tag: The message delivery tag.
        """

    @abstractmethod
    def reject(self, delivery_tag: int) -> None:
        """
        Rejects a message, triggering redelivery or dead-lettering.

        Args:
            delivery_tag: The message delivery tag.
        """

    @abstractmethod
    def consume(
        self, callback: Callable[[bytes, int, dict[str, Any] | None], None]
    ) -> None:
        """
        Starts consuming messages from the configured queue.

        Args:
            callback: Function called for each message with (body, delivery_tag, headers).
        """

    @abstractmethod
    def setup(self) -> None:
        """Sets up the required infrastructure (exchanges, queues, bindings)."""
