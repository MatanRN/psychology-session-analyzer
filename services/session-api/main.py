"""FastAPI application entry point."""

from ddtrace import patch_all
from fastapi import FastAPI

from routes import sessions_router

patch_all()

app = FastAPI(title="Psychology Session API")
app.include_router(sessions_router)
