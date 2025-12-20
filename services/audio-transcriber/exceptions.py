"""Custom exceptions for the audio-transcriber service."""


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""

    def __init__(self, file_name: str, cause: Exception | None = None):
        self.file_name = file_name
        self.cause = cause
        super().__init__(f"Failed to transcribe audio file '{file_name}'")
