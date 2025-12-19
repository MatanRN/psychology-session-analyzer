"""Session-related API endpoints."""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psychology_common.logging import setup_logging
from sqlmodel import Session as DBSession

from dependencies import get_db_session, get_session_repository
from exceptions import NoSessionsFoundError, SessionNotFoundError
from repositories import SessionRepository
from response_models import SessionDetailResponse, SessionWithPatient

logger = setup_logging()

router = APIRouter(prefix="/sessions", tags=["sessions"])

DBSessionDep = Annotated[DBSession, Depends(get_db_session)]


def _get_repository(db_session: DBSessionDep) -> SessionRepository:
    """Dependency that creates a repository with an injected DB session."""
    return get_session_repository(db_session)


RepositoryDep = Annotated[SessionRepository, Depends(_get_repository)]


@router.get("", response_model=List[SessionWithPatient])
def list_sessions(repo: RepositoryDep):
    """Returns all analyzed sessions with basic info."""
    try:
        return repo.list_all()
    except NoSessionsFoundError:
        raise HTTPException(status_code=404, detail="No sessions found")
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: UUID, repo: RepositoryDep):
    """Returns full analysis for a specific session."""
    try:
        return repo.get_by_id(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
