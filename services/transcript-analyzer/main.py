import os
from typing import List, Literal, Optional

import redis
from ddtrace import patch_all
from google import genai
from minio import Minio
from psychology_common import setup_logging
from pydantic import BaseModel

logger = setup_logging()
patch_all()


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_USER")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class Utterance(BaseModel):
    id: int
    speaker: str
    role: Literal["therapist", "patient"]
    text: str
    topic: List[str]
    emotion: List[str]


class SpeakerRoles(BaseModel):
    speaker_a: Literal["therapist", "patient"]
    speaker_b: Literal["therapist", "patient"]


class TranscriptAnalysis(BaseModel):
    speaker_roles: Optional[SpeakerRoles] = None
    utterances: Optional[List[Utterance]] = None
    error: Optional[str] = None


def main():
    minio_client = Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False,
    )
    redis_client = redis.Redis(
        host=REDIS_HOST,
        decode_responses=True,
    )
    client = genai.Client(api_key=GEMINI_API_KEY)

    with minio_client.get_object(
        bucket_name="sessions",
        object_name="2025/12/02/test/testy/transcription/testy-test-2025-12-02.txt",
    ) as response:
        data = response.data.decode("utf-8")
        logger.info("Transcription data", extra={"data": data})

    try:
        with open("system.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=data,
            config={
                "response_mime_type": "application/json",
                "response_schema": TranscriptAnalysis,
                "system_instruction": system_prompt,
            },
        )
        logger.info("Response", extra={"response": response.text})
        cache_key = f"transcript:{'2025'}:{'12'}:{'02'}:{'test'}:{'testy'}"
        redis_client.set(cache_key, response.text)
        logger.info("Cached transcript analysis", extra={"cache_key": cache_key})
    except Exception as e:
        logger.exception("Error generating response from Gemini", extra={"error": e})


if __name__ == "__main__":
    main()
