"""Repository for session data persistence."""

from datetime import date
from uuid import UUID

from psychology_common.db_models import Patient, SessionInsights
from psychology_common.db_models import Session as SessionEntity
from psychology_common.logging import setup_logging
from sqlmodel import Session, select

from domain.models import Insights, SessionMetadata
from exceptions import SessionPersistenceError

logger = setup_logging()


class SessionRepository:
    """
    Handles database operations for session insights.

    Encapsulates SQL queries and transaction management,
    keeping the handler layer free of database concerns.
    """

    def __init__(self, session_factory):
        """
        Initializes the repository.

        Args:
            session_factory: Callable that returns a SQLModel Session context manager.
        """
        self._session_factory = session_factory

    def save_session_insights(
        self, metadata: SessionMetadata, insights: Insights
    ) -> None:
        """
        Persists session insights to the database.

        Creates patient record if needed, creates/updates session,
        and saves associated insights.

        Args:
            metadata: Session metadata including patient info and dates.
            insights: The analyzed insights to persist.

        Raises:
            SessionPersistenceError: If persistence fails.
        """
        try:
            with self._session_factory() as db_session:
                patient = self._get_or_create_patient(
                    db_session,
                    metadata.patient_first_name,
                    metadata.patient_last_name,
                )

                self._create_session(
                    db_session,
                    metadata.session_id,
                    metadata.session_date,
                    patient,
                )

                self._save_insights(db_session, metadata.session_id, insights)

                logger.info(
                    "Session insights persisted",
                    extra={
                        "session_id": metadata.session_id,
                        "patient": f"{metadata.patient_first_name} {metadata.patient_last_name}",
                    },
                )

        except Exception as e:
            logger.exception(
                "Failed to persist session",
                extra={"session_id": metadata.session_id},
            )
            raise SessionPersistenceError(metadata.session_id, cause=e) from e

    def _get_or_create_patient(
        self, db_session: Session, first_name: str, last_name: str
    ) -> Patient:
        """Gets existing patient or creates new one."""
        statement = select(Patient).where(
            Patient.first_name == first_name,
            Patient.last_name == last_name,
        )
        patient = db_session.exec(statement).first()

        if patient:
            return patient

        patient = Patient(first_name=first_name, last_name=last_name)
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)
        return patient

    def _create_session(
        self,
        db_session: Session,
        session_id: str,
        session_date: date,
        patient: Patient,
    ) -> SessionEntity:
        """Creates or updates a session entity."""
        session_entity = SessionEntity(
            id=UUID(session_id),
            session_date=session_date,
            patient_id=patient.id,
        )
        db_session.merge(session_entity)
        db_session.commit()
        return session_entity

    def _save_insights(
        self,
        db_session: Session,
        session_id: str,
        insights: Insights,
    ) -> None:
        """Saves session insights."""
        session_insights = SessionInsights(
            session=SessionEntity(id=UUID(session_id)),
            positive_topics=insights.positive_topics,
            negative_topics=insights.negative_topics,
            sentiment_scores=insights.sentiment_scores,
            patient_relationships=[
                r.model_dump() for r in insights.patient_relationships
            ],
        )
        db_session.merge(session_insights)
        db_session.commit()
