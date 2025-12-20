"""Core business logic for transcript analysis."""

from psychology_common.logging import setup_logging

from domain.models import Insights, PatientRelationship, TranscriptAnalysis
from infrastructure.interfaces import CacheService, LLMService

logger = setup_logging()


class TranscriptAnalyzer:
    """Analyzes transcripts using LLM and generates insights."""

    def __init__(self, llm_service: LLMService, cache_service: CacheService):
        self._llm = llm_service
        self._cache = cache_service

    def analyze(self, transcript: str, session_id: str) -> TranscriptAnalysis:
        """
        Analyzes a transcript, using cache when available.

        Args:
            transcript: The transcript text to analyze.
            session_id: Unique session identifier for caching.

        Returns:
            TranscriptAnalysis with LLM-generated metadata.
        """
        cache_key = f"analysis:{session_id}"

        cached = self._cache.get(cache_key)
        if cached:
            logger.info(
                "Analysis retrieved from cache", extra={"session_id": session_id}
            )
            return TranscriptAnalysis.model_validate_json(cached)

        analysis = self._llm.analyze(transcript)

        self._cache.set(cache_key, analysis.model_dump_json())
        logger.info("Analysis cached", extra={"session_id": session_id})

        return analysis

    def generate_insights(self, analysis: TranscriptAnalysis) -> Insights:
        """
        Extracts actionable insights from transcript analysis.

        Args:
            analysis: The LLM-generated transcript analysis.

        Returns:
            Insights containing topics, sentiment scores, and relationships.
        """
        positive_topics, negative_topics = self._extract_topics(analysis)
        sentiment_scores = self._extract_sentiment_scores(analysis)
        relationships = self._extract_relationships(analysis)

        logger.info("Insights generated from analysis")

        return Insights(
            positive_topics=positive_topics,
            negative_topics=negative_topics,
            sentiment_scores=sentiment_scores,
            patient_relationships=relationships,
        )

    def _extract_topics(
        self, analysis: TranscriptAnalysis
    ) -> tuple[list[str], list[str]]:
        """Extracts positive and negative topics from patient utterances."""
        positive: list[str] = []
        negative: list[str] = []

        if not analysis.utterances:
            return positive, negative

        for utterance in analysis.utterances:
            if utterance.role == "patient":
                if utterance.sentiment_score > 0:
                    positive.extend(utterance.topic)
                elif utterance.sentiment_score < 0:
                    negative.extend(utterance.topic)

        return positive, negative

    def _extract_sentiment_scores(self, analysis: TranscriptAnalysis) -> list[float]:
        """Extracts all sentiment scores from utterances."""
        if not analysis.utterances:
            return []
        return [u.sentiment_score for u in analysis.utterances]

    def _extract_relationships(
        self, analysis: TranscriptAnalysis
    ) -> list[PatientRelationship]:
        """Extracts patient relationships from analysis."""
        if not analysis.relationships:
            return []
        return list(analysis.relationships)
