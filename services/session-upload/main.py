from fastapi import FastAPI, UploadFile
from minio import Minio
import os
from dotenv import load_dotenv
import logging
from fastapi.exceptions import HTTPException

load_dotenv()

app = FastAPI()
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


minio_client = Minio(
    endpoint="localhost:9000",
    access_key=os.getenv("MINIO_USER"),
    secret_key=os.getenv("MINIO_PASSWORD"),
    secure=False,
)
logger.info(f"Minio client initialized with user {os.getenv('MINIO_USER')}")

bucket_name = "session-videos"
if not minio_client.bucket_exists(bucket_name):
    minio_client.make_bucket(bucket_name)
    logger.info(f"Bucket {bucket_name} created")
else:
    logger.debug(f"Bucket {bucket_name} already exists")


@app.post("/upload")
def upload_session(file: UploadFile):
    logger.info(f"Uploading session {file.filename}")
    try:
        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=file.filename,
            content_type=file.content_type,
            length=file.size,
            data=file.file,
        )
        logger.info(f"Session {file.filename} uploaded successfully")
        return {"message": "Session uploaded successfully"}
    except Exception as e:
        logger.exception(f"Error uploading session {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
