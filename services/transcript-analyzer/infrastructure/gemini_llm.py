"""Gemini LLM service implementation."""

from google import genai
from psychology_common.logging import setup_logging

from domain.models import TranscriptAnalysis
from exceptions import LLMServiceError
from infrastructure.interfaces import LLMService

logger = setup_logging()


class GeminiLLMService(LLMService):
    """LLM service implementation using Google Gemini."""

    def __init__(self, client: genai.Client, model_name: str, system_prompt: str):
        self._client = client
        self._model_name = model_name
        self._system_prompt = system_prompt

    def analyze(self, transcript: str) -> TranscriptAnalysis:
        """
        Analyzes a transcript using Gemini and returns structured analysis.

        Args:
            transcript: The transcript text to analyze.

        Returns:
            TranscriptAnalysis with speaker roles, utterances, and relationships.

        Raises:
            LLMServiceError: If the Gemini API call fails.
        """
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=transcript,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": TranscriptAnalysis,
                    "system_instruction": self._system_prompt,
                },
            )
            if not response.text:
                raise LLMServiceError("Gemini returned empty response")
            logger.info("LLM analysis completed")
            return TranscriptAnalysis.model_validate_json(response.text)
        except Exception as e:
            logger.exception("Gemini API call failed")
            raise LLMServiceError(f"Gemini analysis failed: {e}", cause=e) from e
