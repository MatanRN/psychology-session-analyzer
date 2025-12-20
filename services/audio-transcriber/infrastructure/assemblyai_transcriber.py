"""AssemblyAI implementation of the TranscriptionService interface."""

import tempfile

import assemblyai as aai
from psychology_common.logging import setup_logging

from domain.models import Utterance
from exceptions import TranscriptionError

from .interfaces import TranscriptionService

logger = setup_logging()


class AssemblyAITranscriber(TranscriptionService):
    """Handles audio transcription using AssemblyAI."""

    def __init__(self, transcriber: aai.Transcriber):
        self._transcriber = transcriber

    def transcribe(self, audio_data: bytes) -> list[Utterance]:
        """
        Transcribes audio data using AssemblyAI.

        Writes audio to a temp file (required by AssemblyAI SDK),
        performs transcription, and returns speaker-labeled utterances.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()

                transcription = self._transcriber.transcribe(temp_file.name)

                if transcription.status == aai.TranscriptStatus.error:
                    raise TranscriptionError(
                        temp_file.name,
                        Exception(transcription.error),
                    )

                if transcription.text is None:
                    raise TranscriptionError(
                        temp_file.name,
                        Exception("Transcription returned no text"),
                    )

            utterances = [
                Utterance(speaker=u.speaker, text=u.text)
                for u in transcription.utterances
            ]

            logger.info(
                "Audio transcription successful",
                extra={"utterance_count": len(utterances)},
            )
            return utterances

        except TranscriptionError:
            raise
        except Exception as e:
            logger.exception("AssemblyAI transcription failed")
            raise TranscriptionError("audio_file", e) from e
