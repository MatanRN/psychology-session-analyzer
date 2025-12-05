from typing import List, Literal, Optional

from pydantic import BaseModel


class Utterance(BaseModel):
    id: int
    speaker: str
    role: Literal["therapist", "patient"]
    text: str
    topic: List[str]
    emotion: List[str]


class SpeakerRoles(BaseModel):
    speaker_a: Literal["therapist", "patient"]
    speaker_b: Literal["therapist", "patient"]


class TranscriptAnalysis(BaseModel):
    speaker_roles: Optional[SpeakerRoles] = None
    utterances: Optional[List[Utterance]] = None
    error: Optional[str] = None
