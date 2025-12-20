"""Custom exceptions for the transcript-analyzer service."""


class TranscriptAnalysisError(Exception):
    """Raised when transcript analysis fails."""

    def __init__(self, session_id: str, cause: Exception | None = None):
        self.session_id = session_id
        self.cause = cause
        super().__init__(f"Failed to analyze transcript for session '{session_id}'")


class LLMServiceError(Exception):
    """Raised when LLM service call fails."""

    def __init__(self, message: str, cause: Exception | None = None):
        self.cause = cause
        super().__init__(message)


class CacheServiceError(Exception):
    """Raised when cache operations fail."""

    def __init__(self, key: str, operation: str, cause: Exception | None = None):
        self.key = key
        self.operation = operation
        self.cause = cause
        super().__init__(f"Cache {operation} failed for key '{key}'")


class SessionPersistenceError(Exception):
    """Raised when saving session data to database fails."""

    def __init__(self, session_id: str, cause: Exception | None = None):
        self.session_id = session_id
        self.cause = cause
        super().__init__(f"Failed to persist session '{session_id}' to database")


class InvalidSessionMetadataError(Exception):
    """Raised when file path cannot be parsed into valid session metadata."""

    def __init__(self, file_path: str, reason: str):
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Invalid session metadata in path '{file_path}': {reason}")
