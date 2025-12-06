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
import pika
from ddtrace import patch_all
from minio import Minio
from psychology_common.logging import setup_logging

from utils import BUCKET_NAME, EXCHANGE_NAME, MAX_DELIVERY_COUNT, setup_rabbit_entities

# Service setup and configuration
patch_all()
logger = setup_logging()
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")

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

        logger.info(
            "Video file successfully retrieved from MinIO",
            extra={"file_name": file_name, "bucket_name": bucket_name},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_name = os.path.basename(file_name)
            temp_file_path = os.path.join(temp_dir, temp_file_name)
            with open(temp_file_path, "wb") as f:
                f.write(data)
            logger.info(
                "Video file saved to temporary directory",
                extra={"file_name": file_name, "temp_file_path": temp_file_path},
            )
            video = moviepy.VideoFileClip(temp_file_path)
            audio = video.audio
            audio_temp_file_path = os.path.splitext(temp_file_path)[0] + ".wav"
            audio.write_audiofile(audio_temp_file_path, logger=None)

            # Expected structure: year/month/day/session_uuid/video/firstname-lastname-date.mp4
            audio_object_name = file_name.replace("/video/", "/audio/")
            audio_object_name = os.path.splitext(audio_object_name)[0] + ".wav"

            logger.info(
                "Audio file extracted and saved to temporary directory",
                extra={
                    "audio_file_name": audio_object_name,
                    "audio_file_path": audio_temp_file_path,
                },
            )
            audio.close()
            video.close()
            with open(audio_temp_file_path, "rb") as audio_file:
                minio_client.put_object(
                    bucket_name=BUCKET_NAME,
                    object_name=audio_object_name,
                    content_type="audio/wav",
                    length=os.path.getsize(audio_temp_file_path),
                    data=audio_file,
                )
            logger.info(
                "Audio file successfully saved to MinIO",
                extra={"file_name": audio_object_name, "bucket_name": BUCKET_NAME},
            )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        event_data = {
            "file_name": audio_object_name,
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
                "file_name": audio_object_name,
                "exchange": EXCHANGE_NAME,
                "routing_key": "audio.extraction.completed",
            },
        )
    except Exception as e:
        logger.exception(
            "Audio Extraction Failed.",
            extra={"error": e},
        )
        ch.basic_nack(delivery_tag=method.delivery_tag)
        return


def main():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials,
        heartbeat=0,
    )
    rabbit_connection = pika.BlockingConnection(parameters)
    rabbit_channel = rabbit_connection.channel()
    setup_rabbit_entities(rabbit_channel)
    rabbit_channel.basic_consume(
        queue="audio_extraction_queue", on_message_callback=process_video
    )
    logger.info("Service successfully initialized. Message consumption started.")
    rabbit_channel.start_consuming()


if __name__ == "__main__":
    main()
