"""FastAPI application entry point."""

from ddtrace import patch_all
from fastapi import FastAPI

from routes import upload_router

patch_all()

app = FastAPI(title="Session Upload Service")
app.include_router(upload_router)
