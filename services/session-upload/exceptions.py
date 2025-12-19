"""Custom exceptions for the session-upload service."""


class StorageUploadError(Exception):
    """Raised when file upload to storage fails."""

    def __init__(self, object_name: str, cause: Exception | None = None):
        self.object_name = object_name
        self.cause = cause
        super().__init__(f"Failed to upload '{object_name}' to storage")


class EventPublishError(Exception):
    """Raised when publishing an event to the message broker fails."""

    def __init__(self, routing_key: str, cause: Exception | None = None):
        self.routing_key = routing_key
        self.cause = cause
        super().__init__(f"Failed to publish event with routing key '{routing_key}'")
