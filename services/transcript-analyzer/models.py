from datetime import date
from typing import List, Literal, Optional, Text
from uuid import UUID, uuid4

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import ARRAY, Float
from sqlmodel import Field, Relationship, SQLModel


# Pydantic models for LLM response parsing
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


# SQLModel database models
class Patient(SQLModel, table=True):
    __tablename__ = "patients"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    first_name: str = Field(max_length=255)
    last_name: str = Field(max_length=255)

    sessions: List["Session"] = Relationship(back_populates="patient")


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: UUID = Field(primary_key=True)
    session_date: date
    patient_id: UUID = Field(foreign_key="patients.id")

    patient: Patient = Relationship(back_populates="sessions")
    insights: Optional["SessionInsights"] = Relationship(back_populates="session")


class SessionInsights(SQLModel, table=True):
    __tablename__ = "session_insights"
    session_id: UUID = Field(foreign_key="sessions.id", primary_key=True)
    positive_topics: List[str] = Field(sa_column=Column(ARRAY[Text], nullable=False))
    negative_topics: List[str] = Field(sa_column=Column(ARRAY[Text], nullable=False))
    sentiment_scores: List[float] = Field(
        sa_column=Column(ARRAY[Float], nullable=False)
    )
    patient_relationships: List[PatientRelationship] = Field(
        sa_column=Column(ARRAY[JSONB], nullable=False)
    )
    session: Session = Relationship(back_populates="insights")
