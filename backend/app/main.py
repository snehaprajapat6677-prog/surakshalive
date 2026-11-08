"""Suraksha Live - FastAPI application."""

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.config import BACKEND_DIR, Settings, load_env_file, load_settings
from app.service import (
    MAX_TRANSCRIPT_CHARS,
    ServiceError,
    analyze_transcript,
    stt_summary,
    transcribe_and_analyze,
    transcribe_audio,
)
from app.stt import GnaniSTTClient


# Load environment variables
load_env_file(BACKEND_DIR / ".env")


# Application
app = FastAPI(
    title="Suraksha Live API",
    description="Real-time scam detection and voice threat analysis API.",
    version="0.4.0",
)


# Settings
def get_settings() -> Settings:
    return load_settings()


# Gnani STT Client
def get_stt_client(
    settings: Settings = Depends(get_settings),
) -> GnaniSTTClient:
    return GnaniSTTClient(
        api_key=settings.gnani_api_key,
        url=settings.gnani_stt_url,
    )


# Request model
class AnalyzeRequest(BaseModel):
    transcript: str = Field(
        min_length=1,
        max_length=MAX_TRANSCRIPT_CHARS,
    )


# Error handler
@app.exception_handler(ServiceError)
async def service_error_handler(request, exc: ServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Health check
@app.get("/")
def root():
    return {
        "name": "Suraksha Live API",
        "status": "running",
        "version": "0.4.0",
    }


@app.get("/api/health")
def health(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "application": "Suraksha Live",
        "gnani_configured": bool(settings.gnani_api_key),
        "mode": "batch",
        "stt_model": settings.stt_model,
        "max_upload_mb": settings.max_upload_mb,
    }


# Text analysis
@app.post("/api/analyze")
def analyze_text(body: AnalyzeRequest):
    return analyze_transcript(body.transcript)


# Audio transcription
@app.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language_code: str | None = Form(None),
    settings: Settings = Depends(get_settings),
    client: GnaniSTTClient = Depends(get_stt_client),
):
    data = await file.read(
        settings.max_upload_mb * 1024 * 1024 + 1
    )

    if len(data) > settings.max_upload_mb * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={"detail": "Audio file exceeds maximum upload size."},
        )

    stt = await run_in_threadpool(
        transcribe_audio,
        client,
        data,
        file.filename or "",
        language_code,
        settings.max_upload_mb,
        settings.stt_model,
        None,
    )

    return {
        "transcript": stt["transcript"],
        "mode": "batch",
        "stt": stt_summary(stt),
    }


# Audio analysis
@app.post("/api/analyze-audio")
async def analyze_audio(
    file: UploadFile = File(...),
    language_code: str | None = Form(None),
    settings: Settings = Depends(get_settings),
    client: GnaniSTTClient = Depends(get_stt_client),
):
    data = await file.read(
        settings.max_upload_mb * 1024 * 1024 + 1
    )

    if len(data) > settings.max_upload_mb * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={"detail": "Audio file exceeds maximum upload size."},
        )

    return await run_in_threadpool(
        transcribe_and_analyze,
        client,
        data,
        file.filename or "",
        language_code,
        settings.max_upload_mb,
        settings.stt_model,
        None,
    )
