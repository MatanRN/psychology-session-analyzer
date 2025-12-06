import functools
import json
import os
import tempfile

import assemblyai as aai
import pika
from ddtrace import patch_all
from minio import Minio
from psychology_common.logging import setup_logging

from utils import BUCKET_NAME, EXCHANGE_NAME, MAX_DELIVERY_COUNT, setup_rabbit_entities


def get_audio(minio_client: Minio, bucket_name: str, object_name: str):
    with minio_client.get_object(
        bucket_name=bucket_name,
        object_name=object_name,
    ) as response:
        data = response.data
    return data


def save_audio_to_temp(temp_dir: str, file_name: str, data: bytes) -> str:
    """Saves the downloaded audio bytes to a temporary file."""
    temp_file_name = os.path.basename(file_name)
    temp_file_path = os.path.join(temp_dir, temp_file_name)
    with open(temp_file_path, "wb") as audio_file:
        audio_file.write(data)

    logger.info(
        "Audio file saved to temporary directory",
        extra={"file_name": file_name, "temp_file_path": temp_file_path},
    )
    return temp_file_path


def transcribe_audio_file(transcriber: aai.Transcriber, audio_file_path: str):
    """Performs the actual transcription using the AssemblyAI client."""
    with open(audio_file_path, "rb") as audio_file:
        transcription = transcriber.transcribe(audio_file)
        if transcription.text is None:
            raise ValueError("Transcription text is None")
    logger.info(
        "Audio transcription successful",
    )
    return transcription


def save_transcription_to_temp(
    temp_dir: str, original_file_name: str, transcription
) -> tuple[str, str]:
    """
    Formats the transcription and saves it to a temporary text file.
    Returns the path to the temp file and the target object name for storage.
    """
    # Expected structure: year/month/day/session_uuid/audio/firstname-lastname-date.wav
    # Becomes: year/month/day/session_uuid/transcription/firstname-lastname-date.txt
    transcription_object_name = original_file_name.replace("/audio/", "/transcription/")
    transcription_object_name = os.path.splitext(transcription_object_name)[0] + ".txt"

    transcription_temp_file_name = os.path.basename(transcription_object_name)
    transcription_file_path = os.path.join(temp_dir, transcription_temp_file_name)

    with open(transcription_file_path, "w", encoding="utf-8") as f:
        for utterance in transcription.utterances:
            f.write(f"Speaker {utterance.speaker}: {utterance.text}\n")
            # TODO: READ ABOUT DATADOG LOGGING IN THE LINK - https://docs.datadoghq.com/tracing/other_telemetry/connect_logs_and_traces/python/

    logger.info(
        "Transcription saved to temporary file",
        extra={
            "file_name": transcription_temp_file_name,
            "temp_file_path": transcription_file_path,
        },
    )
    return transcription_file_path, transcription_object_name


def upload_transcription_to_minio(
    minio_client: Minio, bucket_name: str, object_name: str, file_path: str
):
    """Uploads the local transcription file to MinIO."""
    with open(file_path, "rb") as transcription_file:
        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            content_type="text/plain",
            length=os.path.getsize(file_path),
            data=transcription_file,
        )
    logger.info(
        "Transcription saved to MinIO",
        extra={
            "file_name": object_name,
            "bucket_name": bucket_name,
        },
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

        data = get_audio(minio_client, bucket_name, file_name)
        logger.info(
            "Audio file successfully retrieved from MinIO",
            extra={"file_name": file_name, "bucket_name": bucket_name},
        )

        # Transcribe audio file and save results to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = save_audio_to_temp(temp_dir, file_name, data)
            transcription = transcribe_audio_file(transcriber, temp_file_path)
            transcription_file_path, transcription_object_name = (
                save_transcription_to_temp(temp_dir, file_name, transcription)
            )
            upload_transcription_to_minio(
                minio_client,
                bucket_name,
                transcription_object_name,
                transcription_file_path,
            )

        ch.basic_ack(delivery_tag=method.delivery_tag)
        event_data = {
            "file_name": transcription_object_name,
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
                "file_name": transcription_object_name,
                "exchange": EXCHANGE_NAME,
                "routing_key": "audio.transcription.completed",
            },
        )
    except Exception as e:
        logger.exception(
            "Audio Transcription Failed",
            extra={"error": e},
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
    logger.info("Service successfully initialized. Message consumption started.")
    rabbit_channel.start_consuming()


if __name__ == "__main__":
    main()
