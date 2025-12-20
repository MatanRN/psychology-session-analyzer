"""Core business logic for transcript building."""

import os

from .models import Utterance


class TranscriptBuilder:
    """Builds formatted transcripts from utterances."""

    def build(
        self, utterances: list[Utterance], audio_file_name: str
    ) -> tuple[str, str]:
        """
        Builds a formatted transcript and derives the output path.

        Args:
            utterances: Speaker-labeled utterances from transcription.
            audio_file_name: Original audio file path.

        Returns:
            Tuple of (transcript_text, transcription_object_name).
        """
        transcript_text = self._format(utterances)
        object_name = self._derive_path(audio_file_name)
        return transcript_text, object_name

    def _format(self, utterances: list[Utterance]) -> str:
        """Formats utterances into a readable transcript."""
        return "\n".join(f"Speaker {u.speaker}: {u.text}" for u in utterances)

    def _derive_path(self, audio_file_name: str) -> str:
        """Converts audio path to transcription path."""
        name = audio_file_name.replace("/audio/", "/transcription/")
        return os.path.splitext(name)[0] + ".txt"
