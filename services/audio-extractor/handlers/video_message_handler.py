"""Handler for processing video files."""

from psychology_common.logging import setup_logging

from domain import AudioExtractionResult, AudioExtractor, VideoMessage
from infrastructure.interfaces import StorageClient

logger = setup_logging()


class VideoMessageHandler:
    """Handles video-to-audio extraction operations."""

    def __init__(self, storage: StorageClient, extractor: AudioExtractor):
        self._storage = storage
        self._extractor = extractor

    def process(self, message: VideoMessage) -> AudioExtractionResult:
        """
        Processes a video file by extracting and storing its audio.

        Args:
            message: The video message containing file location.

        Returns:
            AudioExtractionResult with the uploaded audio details.

        Raises:
            StorageDownloadError: If video download fails.
            AudioExtractionError: If audio extraction fails.
            StorageUploadError: If audio upload fails.
        """
        logger.info(
            "Processing video",
            extra={"file_name": message.file_name, "bucket_name": message.bucket_name},
        )

        video_data = self._storage.download(message.bucket_name, message.file_name)

        audio_bytes, audio_object_name = self._extractor.extract(
            video_data, message.file_name
        )

        result = AudioExtractionResult(
            audio_object_name=audio_object_name,
            bucket_name=message.bucket_name,
        )

        self._storage.upload(
            bucket_name=result.bucket_name,
            object_name=result.audio_object_name,
            data=audio_bytes,
            content_type=result.content_type,
        )

        logger.info(
            "Video processed",
            extra={
                "video_file": message.file_name,
                "audio_file": result.audio_object_name,
            },
        )

        return result
