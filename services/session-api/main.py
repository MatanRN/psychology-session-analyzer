import os
from typing import List
from uuid import UUID

from ddtrace import patch_all
from fastapi import FastAPI, HTTPException
from psychology_common.db_models import Patient, SessionInsights
from psychology_common.db_models import Session as SessionEntity
from psychology_common.logging import setup_logging
from sqlmodel import Session as DBSession
from sqlmodel import create_engine, select

from response_models import SessionDetailResponse, SessionListItem

logger = setup_logging()
patch_all()

app = FastAPI()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB", "psychology_analyzer")

DATABASE_URL = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)


@app.get("/sessions", response_model=List[SessionListItem])
def list_sessions():
    """Returns all analyzed sessions with basic info."""
    with DBSession(engine) as db:
        statement = select(SessionEntity, Patient).join(
            Patient, SessionEntity.patient_id == Patient.id
        )
        try:
            results = db.exec(statement).all()
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

        if not results:
            raise HTTPException(status_code=404, detail="No sessions found")

        return [
            SessionListItem(
                session_id=session.id,
                patient_first_name=patient.first_name,
                patient_last_name=patient.last_name,
                session_date=session.session_date,
            )
            for session, patient in results
        ]


@app.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: UUID):
    """Returns full analysis for a specific session."""
    with DBSession(engine) as db:
        statement = (
            select(SessionEntity, Patient, SessionInsights)
            .join(Patient, SessionEntity.patient_id == Patient.id)
            .join(SessionInsights, SessionEntity.id == SessionInsights.session_id)
            .where(SessionEntity.id == session_id)
        )
        try:
            result = db.exec(statement).first()
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

        if not result:
            raise HTTPException(status_code=404, detail="Session not found")

        session, patient, insights = result

        return SessionDetailResponse(
            session_id=session.id,
            patient_first_name=patient.first_name,
            patient_last_name=patient.last_name,
            session_date=session.session_date,
            insights=insights,
        )
