"""Custom exceptions for the audio-transcriber service."""


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""

    def __init__(self, file_name: str, cause: Exception | None = None):
        self.file_name = file_name
        self.cause = cause
        super().__init__(f"Failed to transcribe audio file '{file_name}'")


class StorageDownloadError(Exception):
    """Raised when downloading a file from storage fails."""

    def __init__(self, object_name: str, cause: Exception | None = None):
        self.object_name = object_name
        self.cause = cause
        super().__init__(f"Failed to download '{object_name}' from storage")


class StorageUploadError(Exception):
    """Raised when uploading a file to storage fails."""

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
