from datetime import date
from uuid import UUID

from sqlmodel import Session, SQLModel, create_engine, select

from models import Insights, Patient, SessionInsights
from models import Session as SessionEntity


def get_engine(host: str, user: str, password: str, port: int, database: str):
    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url)


def init_db(engine):
    SQLModel.metadata.create_all(engine)


def get_or_create_patient(
    db_session: Session, first_name: str, last_name: str
) -> Patient:
    statement = select(Patient).where(
        Patient.first_name == first_name, Patient.last_name == last_name
    )
    patient = db_session.exec(statement).first()
    if patient:
        return patient

    patient = Patient(first_name=first_name, last_name=last_name)
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


def create_session(
    db_session: Session,
    session_id: str,
    session_date: str,
    patient: Patient,
) -> SessionEntity:
    session_entity = SessionEntity(
        id=UUID(session_id),
        session_date=date.fromisoformat(session_date),
        patient_id=patient.id,
    )
    db_session.merge(session_entity)
    db_session.commit()
    return session_entity


def save_insights(
    db_session: Session,
    session_id: str,
    insights: Insights,
):
    session_insights = SessionInsights(
        session=SessionEntity(id=UUID(session_id)),
        positive_topics=insights.positive_topics,
        negative_topics=insights.negative_topics,
        sentiment_scores=insights.sentiment_scores,
        patient_relationships=[r.model_dump() for r in insights.patient_relationships],
    )
    db_session.merge(session_insights)
    db_session.commit()
