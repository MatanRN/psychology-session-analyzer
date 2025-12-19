"""Core business logic for audio extraction."""

import os
import tempfile

import moviepy
from psychology_common.logging import setup_logging

from exceptions import AudioExtractionError

logger = setup_logging()


class AudioExtractor:
    """Extracts audio tracks from video files."""

    def extract(self, video_data: bytes, video_file_name: str) -> tuple[bytes, str]:
        """
        Extracts audio from video data.

        Args:
            video_data: Raw video file bytes.
            video_file_name: Original video file path (used to derive audio path).

        Returns:
            Tuple of (audio_bytes, audio_object_name).

        Raises:
            AudioExtractionError: If extraction fails.
        """
        audio_object_name = self._derive_audio_object_name(video_file_name)

        try:
            audio_bytes = self._extract_audio_bytes(video_data, video_file_name)
        except Exception as e:
            logger.exception(
                "Audio extraction failed", extra={"file_name": video_file_name}
            )
            raise AudioExtractionError(video_file_name, e) from e

        logger.info(
            "Audio extracted successfully",
            extra={"video_file": video_file_name, "audio_file": audio_object_name},
        )
        return audio_bytes, audio_object_name

    def _derive_audio_object_name(self, video_file_name: str) -> str:
        """Converts video path to audio path (e.g., /video/file.mp4 -> /audio/file.wav)."""
        audio_name = video_file_name.replace("/video/", "/audio/")
        return os.path.splitext(audio_name)[0] + ".wav"

    def _extract_audio_bytes(self, video_data: bytes, video_file_name: str) -> bytes:
        """Performs the actual audio extraction using moviepy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_video_path = os.path.join(temp_dir, os.path.basename(video_file_name))
            temp_audio_path = os.path.splitext(temp_video_path)[0] + ".wav"

            with open(temp_video_path, "wb") as f:
                f.write(video_data)

            video = moviepy.VideoFileClip(temp_video_path)
            try:
                video.audio.write_audiofile(temp_audio_path, logger=None)
            finally:
                video.audio.close()
                video.close()

            with open(temp_audio_path, "rb") as f:
                return f.read()
