"""Abstract interface for LLM service operations."""

from abc import ABC, abstractmethod

from domain.models import TranscriptAnalysis


class LLMService(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def analyze(self, transcript: str) -> TranscriptAnalysis:
        """
        Analyzes a transcript and returns structured analysis.

        Args:
            transcript: The transcript text to analyze.

        Returns:
            TranscriptAnalysis with speaker roles, utterances, and relationships.

        Raises:
            LLMServiceError: If the LLM call fails.
        """
        pass
