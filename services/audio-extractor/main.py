"""
Audio Extractor Service.

This module provides a service for extracting audio from video files.
It handles:
- Extracting audio from video files.
- Storing audio files in MinIO object storage.
- Publishing 'video.audio.extracted' events to a RabbitMQ exchange.
- Distributed tracing with Datadog.
- Structured JSON logging.
"""

import json
import logging
import os
import sys
import tempfile

import moviepy
import pika
from ddtrace import patch_all
from minio import Minio
from pythonjsonlogger import jsonlogger


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
    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
    except RuntimeError:
        logger.exception(
            "RabbitMQ Connection Failed, retrying...",
            extra={"host": host, "port": port, "username": username},
        )
        raise
    logger.info(
        "RabbitMQ Connection Established",
        extra={"host": host, "port": port, "username": username},
    )
    # Set up dead letter hanlding
    channel.exchange_declare(
        exchange="dead_letter_exchange", exchange_type="direct", durable=True
    )
    channel.queue_declare(queue="dlq_audio_extraction", durable=True)
    channel.queue_bind(
        queue="dlq_audio_extraction",
        exchange="dead_letter_exchange",
        routing_key="audio.extraction.failed",
    )
    # Ensure exchanges exists - idempotent
    channel.exchange_declare(
        exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
    )
    # Ensure queue exists - idempotent
    channel.queue_declare(queue="audio_extraction_queue", durable=True)
    # Bind queue to exchange with routing key - idempotent
    args = {
        "x-queue-type": "quorum",
        "x-delivery-limit": MAX_DELIVERY_COUNT,
        "x-dead-letter-exchange": "dead_letter_exchange",
        "x-dead-letter-routing-key": "audio.extraction.failed",
    }
    channel.queue_bind(
        queue="audio_extraction_queue",
        exchange=EXCHANGE_NAME,
        routing_key="video.upload.completed",
        arguments=args,
    )
    return connection, channel


# Service setup and configuration
patch_all()
logger = setup_logging()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
BUCKET_NAME = "audio-files"
EXCHANGE_NAME = "events"
MAX_DELIVERY_COUNT = 3

try:
    minio_client = Minio(
        endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_USER"),
        secret_key=os.getenv("MINIO_PASSWORD"),
        secure=False,
    )
    logger.info(
        "Minio client initialized with user", extra={"user": os.getenv("MINIO_USER")}
    )
except Exception:
    logger.exception(
        "MinIO Client Initialization Failed",
        extra={
            "endpoint": os.getenv("MINIO_ENDPOINT", "minio:9000"),
            "user": os.getenv("MINIO_USER"),
        },
    )


def process_video(ch, method, properties, body):
    """
    Processes a video file by extracting audio and storing it in MinIO.
    """
    delivery_count = 1
    if properties.headers and "x-delivery-count" in properties.headers:
        delivery_count = properties.headers["x-delivery-count"]
    logger.info(
        "Processing video (Attempt %s/%s)",
        delivery_count,
        MAX_DELIVERY_COUNT,
    )
    data = json.loads(body)
    file_name = data["file_name"]
    bucket_name = data["bucket_name"]

    try:
        with minio_client.get_object(
            bucket_name=bucket_name,
            object_name=file_name,
        ) as response:
            data = response.data
    except Exception:
        logger.exception(
            "MinIO Object Retrieval Failed",
            extra={"file_name": file_name, "bucket_name": bucket_name},
        )
        ch.basic_nack(delivery_tag=method.delivery_tag)
        return
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, file_name)
            with open(temp_file_path, "wb") as f:
                f.write(data)
            logger.info(
                "Video file saved to temporary directory",
                extra={"file_name": file_name, "temp_file_path": temp_file_path},
            )
            video = moviepy.VideoFileClip(temp_file_path)
            audio = video.audio
            audio_file_path = temp_file_path.replace(".mp4", ".wav")
            audio.write_audiofile(audio_file_path, logger=None)
            audio_file_name = audio_file_path.split("/")[-1]
            logger.info(
                "Audio file extracted and saved to temporary directory",
                extra={
                    "audio_file_name": audio_file_name,
                    "audio_file_path": audio_file_path,
                },
            )
            audio.close()
            video.close()
            with open(audio_file_path, "rb") as audio_file:
                minio_client.put_object(
                    bucket_name=BUCKET_NAME,
                    object_name=audio_file_name,
                    content_type="audio/wav",
                    length=os.path.getsize(audio_file_path),
                    data=audio_file,
                )
            logger.info(
                "Audio file successfully saved to MinIO",
                extra={"file_name": audio_file_name, "bucket_name": BUCKET_NAME},
            )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        # event_data = {
        #     "file_name": audio_file_name,
        #     "bucket_name": bucket_name,
        #     "content_type": "audio/wav",
        # }
        # ch.basic_publish(
        #     exchange=EXCHANGE_NAME,
        #     routing_key="audio.extraction.completed",
        #     body=json.dumps(event_data),
        # )
        # logger.info(
        #     "Event published to RabbitMQ",
        #     extra={
        #         "file_name": file_name,
        #         "exchange": EXCHANGE_NAME,
        #         "routing_key": "audio.extraction.completed",
        #     },
        # )
        return
    except Exception:
        logger.exception(
            "Audio Extraction Failed. Retrying...",
            extra={"file_name": file_name, "bucket_name": bucket_name},
        )
        ch.basic_nack(delivery_tag=method.delivery_tag)
        return


def main():
    connection, channel = get_rabbit_channel()
    channel.basic_consume(
        queue="audio_extraction_queue", on_message_callback=process_video
    )
    channel.start_consuming()


if __name__ == "__main__":
    main()
