"""Session upload endpoint."""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from psychology_common.logging import setup_logging

from dependencies import get_publisher, get_storage
from exceptions import EventPublishError, StorageUploadError
from interfaces import EventPublisher, StorageClient
from response_models import UploadResponse

logger = setup_logging()

router = APIRouter(prefix="/sessions", tags=["sessions"])

StorageDep = Annotated[StorageClient, Depends(get_storage)]
PublisherDep = Annotated[EventPublisher, Depends(get_publisher)]


@router.post("/upload", response_model=UploadResponse)
def upload_session(
    file: UploadFile,
    storage: StorageDep,
    publisher: PublisherDep,
    date_of_session: str = Form(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Session date in YYYY-MM-DD format",
    ),
    patient_first_name: str = Form(..., min_length=1),
    patient_last_name: str = Form(..., min_length=1),
) -> UploadResponse:
    """
    Uploads a session video file.

    Stores the file in object storage and publishes a processing event.
    """
    if file.content_type != "video/mp4":
        raise HTTPException(status_code=422, detail="File must be a video/mp4 file")

    file_extension = os.path.splitext(file.filename or "")[1]
    year, month, day = date_of_session.split("-")
    session_id = str(uuid.uuid4())

    object_name = (
        f"{year}/{month}/{day}/{session_id}/video/"
        f"{patient_first_name}-{patient_last_name}-{date_of_session}{file_extension}"
    )

    logger.info(
        "Received upload request",
        extra={
            "file_name": file.filename,
            "object_name": object_name,
            "session_id": session_id,
            "patient": f"{patient_first_name} {patient_last_name}",
            "date": date_of_session,
        },
    )

    try:
        storage.upload_file(
            object_name=object_name,
            data=file.file,
            size=file.size,
            content_type=file.content_type,
        )
    except StorageUploadError:
        raise HTTPException(status_code=500, detail="File upload failed")

    try:
        publisher.publish(
            routing_key="video.upload.completed",
            payload={
                "file_name": object_name,
                "content_type": file.content_type,
                "bucket_name": "sessions",
            },
        )
    except EventPublishError:
        raise HTTPException(status_code=500, detail="Event publish failed")

    return UploadResponse(
        message="Session uploaded successfully, processing started",
        session_id=session_id,
    )
