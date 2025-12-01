import functools
import json
import os
import tempfile

import assemblyai as aai
import pika
from ddtrace import patch_all
from minio import Minio
from psychology_common import setup_logging


def setup_rabbit_entities(channel):
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

    # Set up dead letter hanlding
    channel.exchange_declare(
        exchange="dead_letter_exchange", exchange_type="direct", durable=True
    )
    channel.queue_declare(queue="dlq_audio_transcriber", durable=True)
    channel.queue_bind(
        queue="dlq_audio_transcriber",
        exchange="dead_letter_exchange",
        routing_key="audio.transcription.failed",
    )
    # Ensure exchanges exists - idempotent
    channel.exchange_declare(
        exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
    )
    # Ensure queue exists - idempotent
    arguments = {
        "x-queue-type": "quorum",
        "x-delivery-limit": MAX_DELIVERY_COUNT,
        "x-dead-letter-exchange": "dead_letter_exchange",
        "x-dead-letter-routing-key": "audio.transcription.failed",
    }
    channel.queue_declare(
        queue="audio_transcription_queue",
        durable=True,
        arguments=arguments,
    )
    channel.queue_bind(
        queue="audio_transcription_queue",
        exchange=EXCHANGE_NAME,
        routing_key="audio.extraction.completed",
    )


def transcribe_audio(
    transcriber: aai.Transcriber, minio_client: Minio, ch, method, properties, body
):
    """
    Transcribes an audio file using AssemblyAI.
    """
    try:
        delivery_count = 1
        if properties.headers and "x-delivery-count" in properties.headers:
            delivery_count = properties.headers["x-delivery-count"]
        logger.info(
            "Transcribing audio (Attempt %s/%s)",
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
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, file_name)
            with open(temp_file_path, "wb") as audio_file:
                audio_file.write(data)
            logger.info(
                "Audio file saved to temporary directory",
                extra={"file_name": file_name, "temp_file_path": temp_file_path},
            )
        try:
            transcription = transcriber.transcribe(temp_file_path)
        except Exception:
            logger.exception(
                "Audio Transcription Failed",
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return
        logger.info(
            "Audio file successfully transcribed",
        )
        transcription_file_name = file_name.split(".")[0] + ".txt"
        transcription_file_path = os.path.join(temp_dir, transcription_file_name)
        with tempfile.TemporaryDirectory() as temp_dir:
            transcription_file_path = os.path.join(temp_dir, transcription_file_name)
            with open(transcription_file_path, "w") as f:
                f.write(transcription.text.encode("utf-8"))
            logger.info(
                "Transcription saved to temporary directory",
                extra={
                    "file_name": file_name,
                    "temp_file_path": transcription_file_path,
                },
            )
            with open(transcription_file_path, "rb") as transcription_file:
                minio_client.put_object(
                    bucket_name=BUCKET_NAME,
                    object_name=transcription_file_name,
                    content_type="text/plain",
                    length=os.path.getsize(transcription_file_path),
                    data=transcription_file,
                )
            logger.info(
                "Transcription saved to MinIO",
                extra={
                    "file_name": transcription_file_name,
                    "bucket_name": BUCKET_NAME,
                },
            )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        event_data = {
            "file_name": transcription_file_name,
            "content_type": "text/plain",
            "bucket_name": BUCKET_NAME,
        }
        ch.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="audio.transcription.completed",
            body=json.dumps(event_data),
        )
        logger.info(
            "Event published to RabbitMQ",
            extra={
                "file_name": transcription_file_name,
                "exchange": EXCHANGE_NAME,
                "routing_key": "audio.transcription.completed",
            },
        )
    except Exception:
        logger.exception(
            "Audio Transcription Failed",
        )
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return


# Service setup and configuration
patch_all()
logger = setup_logging()
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
BUCKET_NAME = "audio-transcriptions"
EXCHANGE_NAME = "events"
MAX_DELIVERY_COUNT = 3


def main():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    rabbit_connection = pika.BlockingConnection(parameters)
    rabbit_channel = rabbit_connection.channel()
    setup_rabbit_entities(rabbit_channel)
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

    aai.settings.api_key = ASSEMBLYAI_API_KEY
    config = aai.TranscriptionConfig(
        speaker_labels=True,
    )
    transcriber = aai.Transcriber(config=config)
    # Inject the transcriber and minio client into the callback function
    callback = functools.partial(transcribe_audio, transcriber, minio_client)
    rabbit_channel.basic_consume(
        queue="audio_transcription_queue", on_message_callback=callback
    )
    rabbit_channel.start_consuming()


if __name__ == "__main__":
    main()
