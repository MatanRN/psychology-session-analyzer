"""Handler for processing transcript messages."""

from psychology_common.logging import setup_logging

from domain import (
    AnalysisResult,
    SessionMetadata,
    TranscriptAnalyzer,
    TranscriptMessage,
)
from infrastructure.interfaces import StorageClient
from repositories import SessionRepository

logger = setup_logging()


class TranscriptMessageHandler:
    """Handles transcript analysis operations."""

    def __init__(
        self,
        storage: StorageClient,
        analyzer: TranscriptAnalyzer,
        repository: SessionRepository,
    ):
        self._storage = storage
        self._analyzer = analyzer
        self._repository = repository

    def process(self, message: TranscriptMessage) -> AnalysisResult:
        """
        Processes a transcript message by analyzing and persisting insights.

        Args:
            message: The transcript message containing file location.

        Returns:
            AnalysisResult with processing details.

        Raises:
            InvalidSessionMetadataError: If file path cannot be parsed.
            StorageDownloadError: If transcript download fails.
            LLMServiceError: If analysis fails.
            SessionPersistenceError: If database save fails.
        """
        logger.info(
            "Processing transcript",
            extra={"file_name": message.file_name, "bucket_name": message.bucket_name},
        )

        metadata = SessionMetadata.from_file_path(message.file_name)

        transcript = self._storage.download_text(message.bucket_name, message.file_name)

        analysis = self._analyzer.analyze(transcript, metadata.session_id)

        insights = self._analyzer.generate_insights(analysis)

        self._repository.save_session_insights(metadata, insights)

        logger.info(
            "Transcript processed",
            extra={
                "session_id": metadata.session_id,
                "patient": f"{metadata.patient_first_name} {metadata.patient_last_name}",
            },
        )

        return AnalysisResult(
            file_name=message.file_name,
            bucket_name=message.bucket_name,
            session_id=metadata.session_id,
        )
