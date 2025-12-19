"""Abstract interfaces for infrastructure dependencies."""

from .messaging import MessageBroker
from .storage import StorageClient

__all__ = ["MessageBroker", "StorageClient"]
