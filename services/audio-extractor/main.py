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
import os
import tempfile

import moviepy
from ddtrace import patch_all
from psychology_common import get_minio_client, get_rabbit_channel, setup_logging


def setup_rabbit_entities(channel):
    """
    Sets up the RabbitMQ entities for the audio extraction service.
    """
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


# Service setup and configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
BUCKET_NAME = "audio-files"
EXCHANGE_NAME = "events"
MAX_DELIVERY_COUNT = 3

patch_all()
logger = setup_logging()
minio_client = get_minio_client(MINIO_ENDPOINT, MINIO_USER, MINIO_PASSWORD)
if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)
    logger.info("Bucket created", extra={"bucket_name": BUCKET_NAME})
else:
    logger.info("Bucket already exists", extra={"bucket_name": BUCKET_NAME})


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
        event_data = {
            "file_name": audio_file_name,
            "content_type": "audio/wav",
            "bucket_name": BUCKET_NAME,
        }
        ch.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="audio.extraction.completed",
            body=json.dumps(event_data),
        )
        logger.info(
            "Event published to RabbitMQ",
            extra={
                "file_name": file_name,
                "exchange": EXCHANGE_NAME,
                "routing_key": "audio.extraction.completed",
            },
        )
    except Exception:
        logger.exception(
            "Audio Extraction Failed. Retrying...",
            extra={"file_name": file_name, "bucket_name": bucket_name},
        )
        ch.basic_nack(delivery_tag=method.delivery_tag)


def main():
    rabbit_connection, rabbit_channel = get_rabbit_channel(
        RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST
    )
    setup_rabbit_entities(rabbit_channel)
    rabbit_channel.basic_consume(
        queue="audio_extraction_queue", on_message_callback=process_video
    )
    rabbit_channel.start_consuming()


if __name__ == "__main__":
    main()
