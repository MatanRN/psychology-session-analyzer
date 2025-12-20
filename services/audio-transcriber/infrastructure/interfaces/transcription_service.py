"""Abstract interface for transcription service operations."""

from abc import ABC, abstractmethod

from domain.models import Utterance


class TranscriptionService(ABC):
    """Abstract base class for audio transcription backends."""

    @abstractmethod
    def transcribe(self, audio_data: bytes) -> list[Utterance]:
        """
        Transcribes audio data and returns speaker-labeled utterances.

        Args:
            audio_data: Raw audio file bytes.

        Returns:
            List of utterances with speaker labels.

        Raises:
            TranscriptionError: If transcription fails.
        """
        pass
