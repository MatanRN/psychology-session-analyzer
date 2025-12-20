"""Handler for processing audio files."""

from psychology_common.logging import setup_logging

from domain import AudioMessage, TranscriptBuilder, TranscriptionResult
from infrastructure.interfaces import StorageClient, TranscriptionService

logger = setup_logging()


class AudioMessageHandler:
    """Orchestrates audio-to-transcription operations."""

    def __init__(
        self,
        storage: StorageClient,
        transcription_service: TranscriptionService,
        transcript_builder: TranscriptBuilder,
    ):
        self._storage = storage
        self._transcription_service = transcription_service
        self._transcript_builder = transcript_builder

    def process(self, message: AudioMessage) -> TranscriptionResult:
        """
        Processes an audio file by transcribing and storing the result.

        Args:
            message: The audio message containing file location.

        Returns:
            TranscriptionResult with the uploaded transcription details.

        Raises:
            StorageDownloadError: If audio download fails.
            TranscriptionError: If transcription fails.
            StorageUploadError: If transcription upload fails.
        """
        logger.info(
            "Processing audio",
            extra={"file_name": message.file_name, "bucket_name": message.bucket_name},
        )

        audio_data = self._storage.download(message.bucket_name, message.file_name)

        utterances = self._transcription_service.transcribe(audio_data)

        transcript_text, transcription_object_name = self._transcript_builder.build(
            utterances, message.file_name
        )

        result = TranscriptionResult(
            transcription_object_name=transcription_object_name,
            bucket_name=message.bucket_name,
        )

        self._storage.upload(
            bucket_name=result.bucket_name,
            object_name=result.transcription_object_name,
            data=transcript_text.encode("utf-8"),
            content_type=result.content_type,
        )

        logger.info(
            "Audio processed",
            extra={
                "audio_file": message.file_name,
                "transcription_file": result.transcription_object_name,
            },
        )

        return result
