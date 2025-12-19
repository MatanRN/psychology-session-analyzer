"""Response models for the session-upload API."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response returned after successful session upload."""

    message: str
    session_id: str
