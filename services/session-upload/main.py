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
import logging
import os
import sys

import pika
from ddtrace import patch_all
from fastapi import FastAPI, UploadFile
from fastapi.exceptions import HTTPException
from minio import Minio
from pythonjsonlogger import jsonlogger

patch_all()
app = FastAPI()


def setup_logging():
    """
    Configures and sets up structured JSON logging for the application.

    This function initializes a JSON formatter that includes timestamp, level,
    logger name, message, trace_id, and span_id. It replaces default handlers
    for the root logger and Uvicorn loggers with a custom stream handler
    to ensure consistent log formatting across the application.

    Returns:
        logging.Logger: The configured root logger instance.
    """
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s"
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []
    root_logger.addHandler(stream_handler)

    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        u_logger = logging.getLogger(logger_name)
        u_logger.setLevel(logging.INFO)

        u_logger.handlers = []

        u_logger.addHandler(stream_handler)

        u_logger.propagate = False

    return root_logger


logger = setup_logging()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
BUCKET_NAME = "session-videos"
EXCHANGE_NAME = "events"


def get_rabbit_channel():
    """
    Establishes a new blocking connection to RabbitMQ and returns a channel.

    This function creates a fresh connection for each request to ensure thread safety
    and avoid connection closure issues typical with long-lived connections in
    threaded environments. It also ensures the target exchange exists.

    Returns:
        tuple: A tuple containing (connection, channel).
            - connection (pika.BlockingConnection): The active RabbitMQ connection.
            - channel (pika.channel.Channel): The active channel for publishing.
    """
    username = os.getenv("RABBITMQ_USER")
    password = os.getenv("RABBITMQ_PASSWORD")
    host, port = os.getenv("RABBITMQ_HOST").split(":")
    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(
        host=host, port=port, credentials=credentials
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    # Ensure exchange exists (Idempotent - safe to call every time)
    channel.exchange_declare(
        exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
    )
    return connection, channel


try:
    minio_client = Minio(
        endpoint=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_USER"),
        secret_key=os.getenv("MINIO_PASSWORD"),
        secure=False,
    )
    logger.info(f"Minio client initialized with user {os.getenv('MINIO_USER')}")
except Exception as e:
    logger.exception(
        f"Error initializing Minio client. Ensure that the environment variables are set correctly and that the Minio service is running. {e}"
    )
    raise HTTPException(status_code=500, detail=str(e)) from e

if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)
    logger.info(f"Bucket {BUCKET_NAME} created")
else:
    logger.info(f"Bucket {BUCKET_NAME} already exists")


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
            extra={"file_name": file.filename, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail=f"Storage Error: {str(e)}")
    try:
        connection, channel = get_rabbit_channel()
        event_data = {
            "file_name": file.filename,
            "content_type": file.content_type,
            "bucket_name": BUCKET_NAME,
        }
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="video.upload.completed",
            body=json.dumps(event_data),
        )
        connection.close()
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
            extra={"file_name": file.filename, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "Session uploaded successfully, processing started"}
