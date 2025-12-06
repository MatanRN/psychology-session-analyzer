from typing import List, Literal, Optional

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlmodel import Field


class Utterance(BaseModel):
    id: int
    speaker: str
    role: Literal["therapist", "patient"]
    text: str
    topic: List[str]
    emotion: List[str]
    sentiment_score: float = PydanticField(ge=-1.0, le=1.0)


class SpeakerRoles(BaseModel):
    speaker_a: Literal["therapist", "patient"]
    speaker_b: Literal["therapist", "patient"]


class PatientRelationship(BaseModel):
    name: str
    relationship: str
    sentiment_score: float = PydanticField(ge=-1.0, le=1.0)
    mentions: int


class TranscriptAnalysis(BaseModel):
    speaker_roles: Optional[SpeakerRoles] = None
    utterances: Optional[List[Utterance]] = None
    relationships: Optional[List[PatientRelationship]] = None
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    error: Optional[str] = None


class Insights(BaseModel):
    positive_topics: List[str]
    negative_topics: List[str]
    sentiment_scores: List[float]
    patient_relationships: List[PatientRelationship]
