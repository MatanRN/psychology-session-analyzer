"""Custom exceptions for the audio-extractor service."""


class AudioExtractionError(Exception):
    """Raised when audio extraction from video fails."""

    def __init__(self, file_name: str, cause: Exception | None = None):
        self.file_name = file_name
        self.cause = cause
        super().__init__(f"Failed to extract audio from '{file_name}'")
