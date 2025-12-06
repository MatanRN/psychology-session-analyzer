import functools
import json
import os

import pika
import redis
from ddtrace import patch_all
from google import genai
from minio import Minio
from psychology_common.logging import setup_logging
from pydantic import ValidationError
from sqlmodel import Session

from analysis import (
    get_patient_relationships,
    get_positive_and_negative_topics,
    get_sentiment_scores,
)
from database import (
    create_session,
    get_engine,
    get_or_create_patient,
    init_db,
    save_insights,
)
from models import Insights, TranscriptAnalysis
from utils import BUCKET_NAME, EXCHANGE_NAME, MAX_DELIVERY_COUNT, setup_rabbit_entities


def get_transcript(minio_client: Minio, bucket_name: str, object_name: str):
    with minio_client.get_object(
        bucket_name=bucket_name, object_name=object_name
    ) as response:
        data = response.data.decode("utf-8")
        logger.info(
            "Transcript successfully retrieved from MinIO",
            extra={"file_name": object_name, "bucket_name": bucket_name},
        )
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
    logger.info(
        "LLM response successfully retrieved",
    )
    return response.text


def cache_llm_response(
    redis_client: redis.Redis, cache_key: str, analysis: TranscriptAnalysis
):
    redis_client.set(cache_key, analysis.model_dump_json())
    logger.info("Cached LLM response in Redis", extra={"cache_key": cache_key})


def generate_insights(analysis: TranscriptAnalysis):
    positive_topics, negative_topics = get_positive_and_negative_topics(analysis)
    sentiment_scores = get_sentiment_scores(analysis)
    patient_relationships = get_patient_relationships(analysis)
    logger.info("Generated insights from transcript")
    return Insights(
        positive_topics=positive_topics,
        negative_topics=negative_topics,
        sentiment_scores=sentiment_scores,
        patient_relationships=patient_relationships,
    )


def upload_to_tables(
    db_engine,
    patient_first_name: str,
    patient_last_name: str,
    session_id: str,
    session_date: str,
    insights: Insights,
):
    with Session(db_engine) as db_session:
        patient = get_or_create_patient(
            db_session, patient_first_name, patient_last_name
        )
        create_session(db_session, session_id, session_date, patient)
        save_insights(db_session, session_id, insights)
        logger.info(
            "Uploaded insights to database",
            extra={
                "session_id": session_id,
                "patient_first_name": patient_first_name,
                "patient_last_name": patient_last_name,
                "session_date": session_date,
            },
        )


def analyze_transcript(
    gemini_client: genai.Client,
    minio_client: Minio,
    redis_client: redis.Redis,
    db_engine,
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

        session_id = file_name.split("/")[3]
        session_date = "-".join(file_name.split("/")[0:3])
        patient_first_name, patient_last_name = (
            file_name.split("/")[5].split(".")[0].split("-")[0:2]
        )

        transcript = get_transcript(minio_client, bucket_name, file_name)
        with open("system.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        response = call_llm(gemini_client, transcript, system_prompt)
        analysis = TranscriptAnalysis.model_validate_json(response)
        logger.info(
            "Transcript model validated successfully",
        )
        cache_key = f"analysis:{session_id}"

        cache_llm_response(redis_client, cache_key, analysis)
        insights = generate_insights(analysis)

        upload_to_tables(
            db_engine,
            patient_first_name,
            patient_last_name,
            session_id,
            session_date,
            insights,
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)
        event_data = {
            "file_name": file_name,
            "bucket_name": bucket_name,
        }
        ch.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key="transcript.analysis.completed",
            body=json.dumps(event_data),
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
            extra={"error": e, "Model": TranscriptAnalysis.model_json_schema()},
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
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
POSTGRES_DB = os.getenv("POSTGRES_DB")


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

    db_engine = get_engine(
        POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_DB
    )
    init_db(db_engine)
    logger.info("Database initialized", extra={"host": POSTGRES_HOST})

    callback = functools.partial(
        analyze_transcript, gemini_client, minio_client, redis_client, db_engine
    )
    rabbit_channel.basic_consume(
        queue="transcript_analysis_queue", on_message_callback=callback
    )
    logger.info("Service successfully initialized. Message consumption started.")
    rabbit_channel.start_consuming()


if __name__ == "__main__":
    main()
