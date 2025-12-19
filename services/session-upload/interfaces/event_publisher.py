"""Abstract interface for event publishing."""

from abc import ABC, abstractmethod


class EventPublisher(ABC):
    """Abstract base class for event publishers."""

    @abstractmethod
    def publish(self, routing_key: str, payload: dict) -> None:
        """
        Publishes an event to the message broker.

        Args:
            routing_key: The routing key for message routing.
            payload: The event data as a dictionary.

        Raises:
            EventPublishError: If publishing fails.
        """
        pass
