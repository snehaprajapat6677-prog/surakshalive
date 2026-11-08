"""Application logic shared by the HTTP routes. No FastAPI imports, so it is testable with the standard library."""
from __future__ import annotations

from app.audio_format import AudioError, check_container
from app.detection import analyze
from app.stt import (STTAuthError, STTConfigError, STTError, STTQuotaError, STTRequestError,
                     STTTimeoutError, validate_upload)
from app.stt_params import DEFAULT_MODEL, ParamError, build_stt_fields, default_language

MB = 1024 * 1024
MAX_TRANSCRIPT_CHARS = 20000


class ServiceError(Exception):
    """An error that maps directly to an HTTP status code and a safe message."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def analyze_transcript(transcript: str) -> dict:
    if not transcript or not transcript.strip():
        raise ServiceError(422, "Transcript is empty.")
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        raise ServiceError(413, f"Transcript is longer than {MAX_TRANSCRIPT_CHARS} characters.")
    return analyze(transcript)


def _map_stt_error(exc: STTError) -> ServiceError:
    if isinstance(exc, (STTConfigError, STTAuthError)):
        return ServiceError(503, str(exc))
    if isinstance(exc, STTQuotaError):
        return ServiceError(429, str(exc))
    if isinstance(exc, STTRequestError):
        return ServiceError(422, str(exc))
    if isinstance(exc, STTTimeoutError):
        return ServiceError(504, str(exc))
    return ServiceError(502, str(exc))


def transcribe_audio(client, data: bytes, filename: str, language_code: str | None,
                     max_mb: int, model: str = DEFAULT_MODEL, output_format: str | None = None) -> dict:
    language = (language_code or "").strip() or default_language(model)
    try:
        build_stt_fields(language, model, output_format)
    except ParamError as exc:
        raise ServiceError(422, str(exc)) from None
    if len(data) > max_mb * MB:
        raise ServiceError(413, f"Audio is larger than {max_mb} MB.")
    try:
        validate_upload(filename, len(data), max_mb)
    except ValueError as exc:
        raise ServiceError(422, str(exc)) from None
    try:
        check_container(data)
    except AudioError as exc:
        raise ServiceError(422, str(exc)) from None
    try:
        result = client.transcribe_detailed(data, filename, language, model=model, output_format=output_format)
    except ParamError as exc:
        raise ServiceError(422, str(exc)) from None
    except STTError as exc:
        raise _map_stt_error(exc) from None
    return {
        "transcript": result["transcript"],
        "language_code": result["fields"]["language_code"],
        "model": model,
        "format": result["fields"]["format"],
        "detected_language_code": result["detected_language_code"],
        "truncated": result["truncated"],
    }


def stt_summary(stt: dict) -> dict:
    return {key: stt[key] for key in ("model", "language_code", "format", "detected_language_code", "truncated")}


def transcribe_and_analyze(client, data: bytes, filename: str, language_code: str | None,
                           max_mb: int, model: str = DEFAULT_MODEL, output_format: str | None = None) -> dict:
    stt = transcribe_audio(client, data, filename, language_code, max_mb, model, output_format)
    transcript = stt["transcript"]
    return {
        "transcript": transcript,
        "mode": "batch",
        "speech_detected": bool(transcript.strip()),
        "stt": stt_summary(stt),
        "analysis": analyze(transcript),
    }
