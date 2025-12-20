"""Domain models for transcript analysis."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from exceptions import InvalidSessionMetadataError


class Utterance(BaseModel):
    """A single utterance from the transcript with analysis metadata."""

    id: int
    speaker: str
    role: Literal["therapist", "patient"]
    text: str
    topic: list[str]
    emotion: list[str]
    sentiment_score: float = Field(ge=-1.0, le=1.0)


class SpeakerRoles(BaseModel):
    """Mapping of speaker labels to their roles."""

    speaker_a: Literal["therapist", "patient"]
    speaker_b: Literal["therapist", "patient"]


class PatientRelationship(BaseModel):
    """A relationship mentioned by the patient during the session."""

    name: str
    relationship: str
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    mentions: int


class TranscriptAnalysis(BaseModel):
    """Complete LLM analysis result for a transcript."""

    speaker_roles: SpeakerRoles | None = None
    utterances: list[Utterance] | None = None
    relationships: list[PatientRelationship] | None = None
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    error: str | None = None


class Insights(BaseModel):
    """Processed insights derived from transcript analysis."""

    positive_topics: list[str]
    negative_topics: list[str]
    sentiment_scores: list[float]
    patient_relationships: list[PatientRelationship]


class TranscriptMessage(BaseModel):
    """Incoming message from the queue containing transcript location."""

    file_name: str
    bucket_name: str


class SessionMetadata(BaseModel, frozen=True):
    """
    Session information extracted from transcript file path.

    Expected path format: {year}/{month}/{day}/{session_id}/{subdir}/{firstname-lastname}.ext
    Example: 2025/01/15/abc123-uuid/transcripts/john-doe.txt
    """

    session_id: str
    session_date: date
    patient_first_name: str
    patient_last_name: str

    @classmethod
    def from_file_path(cls, file_path: str) -> "SessionMetadata":
        """
        Parses session metadata from a transcript file path.

        Args:
            file_path: The object path in storage.

        Returns:
            SessionMetadata with extracted values.

        Raises:
            InvalidSessionMetadataError: If the path doesn't match expected format.
        """
        parts = file_path.split("/")

        if len(parts) < 6:
            raise InvalidSessionMetadataError(
                file_path,
                f"Expected at least 6 path segments, got {len(parts)}",
            )

        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            session_date = date(year, month, day)
        except ValueError as e:
            raise InvalidSessionMetadataError(
                file_path,
                f"Invalid date components: {parts[0]}/{parts[1]}/{parts[2]}",
            ) from e

        session_id = parts[3]
        if not session_id:
            raise InvalidSessionMetadataError(file_path, "Empty session ID")

        filename = parts[5].split(".")[0]
        name_parts = filename.split("-")

        if len(name_parts) < 2:
            raise InvalidSessionMetadataError(
                file_path,
                f"Expected firstname-lastname format, got '{filename}'",
            )

        patient_first_name = name_parts[0]
        patient_last_name = name_parts[1]

        if not patient_first_name or not patient_last_name:
            raise InvalidSessionMetadataError(
                file_path,
                "Patient first name or last name is empty",
            )

        return cls(
            session_id=session_id,
            session_date=session_date,
            patient_first_name=patient_first_name,
            patient_last_name=patient_last_name,
        )


class AnalysisResult(BaseModel):
    """Result of transcript analysis processing."""

    file_name: str
    bucket_name: str
    session_id: str
