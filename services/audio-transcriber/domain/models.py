"""Domain models for the audio transcription service."""

from pydantic import BaseModel


class AudioMessage(BaseModel, frozen=True):
    """Represents an incoming audio extraction completed event."""

    file_name: str
    bucket_name: str


class Utterance(BaseModel, frozen=True):
    """A single speaker utterance from transcription."""

    speaker: str
    text: str


class TranscriptionResult(BaseModel, frozen=True):
    """Result of a transcription operation."""

    transcription_object_name: str
    bucket_name: str
    content_type: str = "text/plain"
