"""Custom exceptions for the session-api service."""

from uuid import UUID


class SessionNotFoundError(Exception):
    """Raised when a requested session does not exist."""

    def __init__(self, session_id: UUID):
        self.session_id = session_id
        super().__init__(f"Session {session_id} not found")


class NoSessionsFoundError(Exception):
    """Raised when no sessions exist in the database."""

    def __init__(self):
        super().__init__("No sessions found")
