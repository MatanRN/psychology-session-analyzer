"""Domain models for the audio extraction service."""

from pydantic import BaseModel


class VideoMessage(BaseModel, frozen=True):
    """Represents an incoming video upload event message."""

    file_name: str
    bucket_name: str


class AudioExtractionResult(BaseModel, frozen=True):
    """Result of an audio extraction operation."""

    audio_object_name: str
    bucket_name: str
    content_type: str = "audio/wav"
