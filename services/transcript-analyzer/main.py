import functools
import json
import os

import pika
import redis
from ddtrace import patch_all
from google import genai
from minio import Minio
from psychology_common import setup_logging
from pydantic import ValidationError

from models import TranscriptAnalysis
from utils import EXCHANGE_NAME, MAX_DELIVERY_COUNT, setup_rabbit_entities


def get_transcript(minio_client: Minio, bucket_name: str, object_name: str):
    with minio_client.get_object(
        bucket_name=bucket_name, object_name=object_name
    ) as response:
        data = response.data.decode("utf-8")
        return data


def call_llm(gemini_client: genai.Client, contents: str, system_prompt: str):
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=contents,
        config={
            "response_mime_type": "application/json",
            "response_schema": TranscriptAnalysis,
            "system_instruction": system_prompt,
        },
    )
    return response.text


def cache_llm_analysis(
    redis_client: redis.Redis, cache_key: str, analysis: TranscriptAnalysis
):
    redis_client.set(cache_key, analysis.model_dump_json())
    logger.info("Cached response", extra={"cache_key": cache_key})


def analyze_transcript(
    gemini_client: genai.Client,
    minio_client: Minio,
    redis_client: redis.Redis,
    ch,
    method,
    properties,
    body,
):
    try:
        delivery_count = 1
        if properties.headers and "x-delivery-count" in properties.headers:
            delivery_count = properties.headers["x-delivery-count"]
        logger.info(
            "Analyzing transcript (Attempt %s/%s)",
            delivery_count,
            MAX_DELIVERY_COUNT,
        )
        data = json.loads(body)
        file_name = data["file_name"]
        bucket_name = data["bucket_name"]
        transcript = get_transcript(minio_client, bucket_name, file_name)
        with open("system.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        response = call_llm(gemini_client, transcript, system_prompt)
        analysis = TranscriptAnalysis.model_validate_json(response)
        split_file_name = file_name.split("/")
        year = split_file_name[0]
        month = split_file_name[1]
        day = split_file_name[2]
        lastname = split_file_name[3]
        firstname = split_file_name[4]
        cache_key = f"analysis:{year}:{month}:{day}:{lastname}:{firstname}"
        cache_llm_analysis(redis_client, cache_key, analysis)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        ch.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="transcript.analysis.completed",
            body=json.dumps(data),
        )
        logger.info(
            "Event published to RabbitMQ",
            extra={
                "exchange": EXCHANGE_NAME,
                "routing_key": "transcript.analysis.completed",
            },
        )

    except Exception as e:
        logger.exception("Error analyzing transcript", extra={"error": e})
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return
    except ValidationError as e:
        logger.exception(
            "Error validating response from Gemini",
            extra={"error": e},
        )
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return


logger = setup_logging()
patch_all()
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")
BUCKET_NAME = "sessions"


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
    redis_client = redis.Redis(
        host=REDIS_HOST,
        decode_responses=True,
    )
    if not redis_client.ping():
        logger.error("Redis connection failed", extra={"host": REDIS_HOST})
        raise ConnectionError("Redis connection failed")
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

    callback = functools.partial(
        analyze_transcript, gemini_client, minio_client, redis_client
    )
    rabbit_channel.basic_consume(
        queue="transcript_analysis_queue", on_message_callback=callback
    )
    rabbit_channel.start_consuming()


if __name__ == "__main__":
    main()
