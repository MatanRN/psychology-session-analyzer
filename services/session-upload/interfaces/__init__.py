"""Abstract interfaces for infrastructure dependencies."""

from .event_publisher import EventPublisher
from .storage import StorageClient

__all__ = ["StorageClient", "EventPublisher"]
