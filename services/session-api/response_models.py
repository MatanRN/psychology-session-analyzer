from datetime import date
from uuid import UUID

from psychology_common.db_models import SessionInsights
from pydantic import BaseModel


class SessionWithPatient(BaseModel):
    """Session data combined with patient information."""

    session_id: UUID
    patient_first_name: str
    patient_last_name: str
    session_date: date


class SessionDetailResponse(BaseModel):
    """Full session details including analysis insights."""

    session_id: UUID
    patient_first_name: str
    patient_last_name: str
    session_date: date
    insights: SessionInsights
