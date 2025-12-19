"""Repository for session data access."""

from typing import List
from uuid import UUID

from psychology_common.db_models import Patient, SessionInsights
from psychology_common.db_models import Session as SessionEntity
from sqlmodel import Session as DBSession
from sqlmodel import select

from exceptions import NoSessionsFoundError, SessionNotFoundError
from response_models import SessionDetailResponse, SessionWithPatient


class SessionRepository:
    """
    Handles all database operations for sessions.

    Encapsulates SQL queries and returns domain objects,
    keeping the HTTP layer free of database concerns.
    """

    def __init__(self, db_session: DBSession):
        self._db = db_session

    def list_all(self) -> List[SessionWithPatient]:
        """
        Retrieves all sessions with patient information.

        Raises:
            NoSessionsFoundError: If no sessions exist.
        """
        statement = select(SessionEntity, Patient).join(
            Patient, SessionEntity.patient_id == Patient.id
        )
        results = self._db.exec(statement).all()

        if not results:
            raise NoSessionsFoundError()

        return [
            SessionWithPatient(
                session_id=session.id,
                patient_first_name=patient.first_name,
                patient_last_name=patient.last_name,
                session_date=session.session_date,
            )
            for session, patient in results
        ]

    def get_by_id(self, session_id: UUID) -> SessionDetailResponse:
        """
        Retrieves a single session with full details.

        Args:
            session_id: The UUID of the session to retrieve.

        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        statement = (
            select(SessionEntity, Patient, SessionInsights)
            .join(Patient, SessionEntity.patient_id == Patient.id)
            .join(SessionInsights, SessionEntity.id == SessionInsights.session_id)
            .where(SessionEntity.id == session_id)
        )
        result = self._db.exec(statement).first()

        if not result:
            raise SessionNotFoundError(session_id)

        session, patient, insights = result

        return SessionDetailResponse(
            session_id=session.id,
            patient_first_name=patient.first_name,
            patient_last_name=patient.last_name,
            session_date=session.session_date,
            insights=insights,
        )
