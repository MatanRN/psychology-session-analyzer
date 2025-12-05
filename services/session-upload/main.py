"""
Session Upload Service.

This module provides a FastAPI application for uploading psychology session videos.
It handles:
- Storing video files in MinIO object storage.
- Publishing 'video.upload.completed' events to a RabbitMQ exchange.
- Distributed tracing with Datadog.
- Structured JSON logging.
"""

import json
import os
import re
import uuid

import pika
from ddtrace import patch_all
from fastapi import FastAPI, Form, UploadFile
from fastapi.exceptions import HTTPException
from minio import Minio
from psychology_common import setup_logging

logger = setup_logging()
patch_all()
app = FastAPI()
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
BUCKET_NAME = "sessions"
EXCHANGE_NAME = "events"
credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
rabbit_connection = pika.BlockingConnection(parameters)
rabbit_channel = rabbit_connection.channel()
rabbit_channel.exchange_declare(
    exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
)
minio_client = Minio(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_USER,
    secret_key=MINIO_PASSWORD,
    secure=False,
)
if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)
    logger.info("Bucket created", extra={"bucket_name": BUCKET_NAME})
else:
    logger.info("Bucket already exists", extra={"bucket_name": BUCKET_NAME})


@app.post("/upload")
def upload_session(
    file: UploadFile,
    date_of_session: str = Form(...),
    patient_first_name: str = Form(...),
    patient_last_name: str = Form(...),
):
    """
    Handles the upload of a session video file.

    This endpoint performs the following actions:
    1. Receives a video file and metadata via multipart/form-data.
    2. Validates that date_of_session matches YYYY-MM-DD format.
    3. Uploads the file to the configured MinIO bucket with a hierarchical path using year/month/day.
    4. Publishes a 'video.upload.completed' event to RabbitMQ with file metadata.

    Args:
        file (UploadFile): The uploaded video file.
        date_of_session (str): The date of the session (YYYY-MM-DD).
        patient_first_name (str): The first name of the patient.
        patient_last_name (str): The last name of the patient.

    Returns:
        dict: A dictionary containing a success message upon completion.

    Raises:
        HTTPException: If there is an error uploading to MinIO or publishing to RabbitMQ.
        HTTPException: If date_of_session format is invalid.
    """
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_of_session):
        raise HTTPException(
            status_code=400, detail="date_of_session must be in YYYY-MM-DD format"
        )

    file_extension = os.path.splitext(file.filename or "")[1]
    year, month, day = date_of_session.split("-")
    session_id = str(uuid.uuid4())

    object_name = f"{year}/{month}/{day}/{session_id}/video/{patient_first_name}-{patient_last_name}-{date_of_session}{file_extension}"

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
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            content_type=file.content_type,
            length=file.size,
            data=file.file,
        )
        logger.info(
            "Saved to MinIO",
            extra={
                "file_name": file.filename,
                "object_name": object_name,
                "size": file.size,
                "bucket": BUCKET_NAME,
            },
        )
    except Exception as e:
        logger.exception(
            "MinIO Upload Failed",
            extra={"file_name": file.filename, "object_name": object_name},
        )
        raise HTTPException(status_code=500, detail="File Upload Failed") from e
    try:
        event_data = {
            "file_name": object_name,
            "content_type": file.content_type,
            "bucket_name": BUCKET_NAME,
        }
        rabbit_channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="video.upload.completed",
            body=json.dumps(event_data),
        )
        logger.info(
            "Event published to RabbitMQ",
            extra={
                "file_name": object_name,
                "exchange": EXCHANGE_NAME,
                "routing_key": "video.upload.completed",
            },
        )
    except Exception as e:
        logger.exception(
            "RabbitMQ Publish Failed",
            extra={"file_name": object_name},
        )
        raise HTTPException(status_code=500, detail="RabbitMQ Publish Failed") from e
    return {"message": "Session uploaded successfully, processing started"}
