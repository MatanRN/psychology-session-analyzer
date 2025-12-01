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

from ddtrace import patch_all
from fastapi import FastAPI, UploadFile
from fastapi.exceptions import HTTPException
from psychology_common import get_minio_client, get_rabbit_channel, setup_logging

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
BUCKET_NAME = "session-videos"
EXCHANGE_NAME = "events"

logger = setup_logging()
patch_all()
app = FastAPI()
rabbit_connection, rabbit_channel = get_rabbit_channel(
    RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST
)
rabbit_channel.exchange_declare(
    exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
)
minio_client = get_minio_client(MINIO_ENDPOINT, MINIO_USER, MINIO_PASSWORD)
if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)
    logger.info("Bucket created", extra={"bucket_name": BUCKET_NAME})
else:
    logger.info("Bucket already exists", extra={"bucket_name": BUCKET_NAME})


@app.post("/upload")
def upload_session(file: UploadFile):
    """
    Handles the upload of a session video file.

    This endpoint performs the following actions:
    1. Receives a video file via multipart/form-data.
    2. Uploads the file to the configured MinIO bucket.
    3. Publishes a 'session.uploaded' event to RabbitMQ with file metadata.

    Args:
        file (UploadFile): The uploaded video file.

    Returns:
        dict: A dictionary containing a success message upon completion.

    Raises:
        HTTPException: If there is an error uploading to MinIO or publishing to RabbitMQ.
    """
    logger.info("Received upload request", extra={"file_name": file.filename})
    try:
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=file.filename,
            content_type=file.content_type,
            length=file.size,
            data=file.file,
        )
        logger.info(
            "Saved to MinIO",
            extra={
                "file_name": file.filename,
                "size": file.size,
                "bucket": BUCKET_NAME,
            },
        )
    except Exception as e:
        logger.exception(
            "MinIO Upload Failed",
            extra={"file_name": file.filename},
        )
        raise HTTPException(status_code=500, detail="File Upload Failed") from e
    try:
        event_data = {
            "file_name": file.filename,
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
                "file_name": file.filename,
                "exchange": EXCHANGE_NAME,
                "routing_key": "video.upload.completed",
            },
        )
    except Exception as e:
        logger.exception(
            "RabbitMQ Publish Failed",
            extra={"file_name": file.filename},
        )
        raise HTTPException(status_code=500, detail="RabbitMQ Publish Failed") from e
    return {"message": "Session uploaded successfully, processing started"}
