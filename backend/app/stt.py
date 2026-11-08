"""Gnani Prisma REST client.

Checked against docs.gnani.ai/api/STT/speech-to-text.md on 2026-11-06:
  POST https://api.vachana.ai/stt/v3, multipart/form-data, header X-API-Key-ID
  Fields: audio_file (required), language_code (required), model, format, itn_native_numerals
  Accepted audio: WAV, MP3, OGG, FLAC, AAC, M4A. Maximum 30 seconds per request.
  Success: HTTP 200 with a JSON body containing "transcript" (a string, possibly empty).
Tests use fake transports. This client has not yet been run against the live API.
The API key is read on the server, is never returned, and is removed from any message text.
"""
from __future__ import annotations

import json
import os
import uuid
from urllib import error, request

from app.stt_params import DEFAULT_MODEL, build_stt_fields

GNANI_STT_URL = "https://api.vachana.ai/stt/v3"
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a"}
MAX_MESSAGE_CHARS = 200
GNANI_ERROR_MESSAGES = {
    "INVALID_LANGUAGE_CODE": "Gnani does not support that language code. Check the language setting.",
    "MODEL_UNSUPPORTED_LANGUAGE": "The configured Gnani model does not support that language.",
    "INVALID_MODEL": "Gnani does not recognise the configured model. Check GNANI_STT_MODEL.",
    "INVALID_FORMAT": "Gnani does not support that output format for the configured model.",
    "INVALID_CONTEXT": "Gnani rejected the request options.",
    "EMPTY_AUDIO": "The audio file is empty.",
    "UNSUPPORTED_AUDIO_FORMAT": "Gnani does not accept this audio format. Use WAV, MP3, OGG, FLAC, AAC or M4A.",
    "AUDIO_CONVERSION_ERROR": "Gnani could not decode this audio file.",
    "MAX_AUDIO_DURATION_EXCEEDED": "The audio is longer than Gnani's 30-second limit.",
}


class STTError(Exception):
    """Base class for speech-to-text failures."""


class STTConfigError(STTError):
    """A required setting, such as the API key, is missing."""


class STTAPIError(STTError):
    """Gnani returned an error or an unexpected response."""

    def __init__(self, message: str, http_status: int | None = None, gnani_type: str | None = None):
        super().__init__(message)
        self.http_status = http_status
        self.gnani_type = gnani_type


class STTAuthError(STTAPIError):
    """The key was rejected or lacks permission (HTTP 401 or 403)."""


class STTQuotaError(STTAPIError):
    """Credit is exhausted or the rate limit was hit (HTTP 402 or 429)."""


class STTRequestError(STTAPIError):
    """Gnani rejected the audio or the options (HTTP 400 or 422)."""


class STTTimeoutError(STTAPIError):
    """Gnani or the network did not answer in time."""


class STTUnavailableError(STTAPIError):
    """Gnani is down or the network failed (HTTP 500 and up, or a connection error)."""


class STTResponseError(STTAPIError):
    """Gnani answered, but the body was not a transcript."""


def key_from_env() -> str:
    return os.environ.get("GNANI_API_KEY", "").strip()


def validate_upload(filename: str, size_bytes: int, max_mb: int = 10) -> None:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported audio type '{ext or 'none'}'. "
                         f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if size_bytes <= 0:
        raise ValueError("Audio file is empty.")
    if size_bytes > max_mb * 1024 * 1024:
        raise ValueError(f"Audio file is larger than {max_mb} MB.")


def _multipart(fields: dict, file_field: str, filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    safe_name = filename.replace('"', "")
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
                  f'filename="{safe_name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
                 + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _http_post(url: str, api_key: str, body: bytes, content_type: str, timeout: float) -> tuple[int, bytes]:
    req = request.Request(url, data=body, method="POST",
                          headers={"X-API-Key-ID": api_key, "Content-Type": content_type})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except error.HTTPError as exc:
        return exc.code, exc.read()


def _str_or_none(value) -> str | None:
    return value if isinstance(value, str) else None


def _parse_error(raw: bytes) -> tuple[str | None, str | None]:
    """Read Gnani's error shapes: {"error": {...}}, {"detail": {...}} or {"code", "message"}."""
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, None
    if not isinstance(body, dict):
        return None, None
    error_obj = body.get("error")
    if isinstance(error_obj, dict):
        return _str_or_none(error_obj.get("type")), _str_or_none(error_obj.get("message"))
    detail = body.get("detail")
    if isinstance(detail, dict):
        return _str_or_none(detail.get("error_code")), _str_or_none(detail.get("message"))
    return _str_or_none(body.get("code")), _str_or_none(body.get("message"))


class GnaniSTTClient:
    def __init__(self, api_key: str | None, url: str = GNANI_STT_URL,
                 transport=_http_post, timeout: float = 45.0):
        self._api_key = (api_key or "").strip()
        self._url = url
        self._transport = transport
        self._timeout = timeout

    def transcribe_detailed(self, audio: bytes, filename: str, language_code: str = "hi-IN",
                            model: str = DEFAULT_MODEL, output_format: str | None = None) -> dict:
        if not self._api_key:
            raise STTConfigError("GNANI_API_KEY is missing. Add it to backend/.env. Never commit that file.")
        fields = build_stt_fields(language_code, model, output_format)  # raises ParamError
        body, content_type = _multipart(fields, "audio_file", filename, audio)
        try:
            status, raw = self._transport(self._url, self._api_key, body, content_type, self._timeout)
        except TimeoutError:
            raise STTTimeoutError("Gnani did not respond in time. Try a shorter recording.") from None
        except OSError as exc:
            raise STTUnavailableError(f"Could not reach Gnani ({type(exc).__name__}). Check the network.") from None
        if 200 <= status < 300:
            return self._parse_success(raw, fields)
        raise self._error_for_status(status, raw)

    def transcribe(self, audio: bytes, filename: str, language_code: str = "hi-IN",
                   model: str = DEFAULT_MODEL, output_format: str | None = None) -> str:
        return self.transcribe_detailed(audio, filename, language_code, model, output_format)["transcript"]

    def _clean(self, text: str | None) -> str:
        if not text:
            return ""
        cleaned = text.replace(self._api_key, "[redacted]") if self._api_key else text
        return cleaned[:MAX_MESSAGE_CHARS]

    def _parse_success(self, raw: bytes, fields: dict) -> dict:
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise STTResponseError("Gnani STT returned a non-JSON response.") from None
        if not isinstance(data, dict):
            raise STTResponseError("Gnani STT returned an unexpected response.")
        if data.get("success") is False:
            gnani_type, gnani_message = _parse_error(raw)
            raise STTAPIError(self._clean(gnani_message) or "Gnani STT reported a failed transcription.",
                              gnani_type=gnani_type)
        transcript = data.get("transcript")
        if not isinstance(transcript, str):
            raise STTResponseError("Gnani STT response did not contain a transcript.")
        return {
            "transcript": transcript,
            "model": _str_or_none(data.get("model")),
            "detected_language_code": _str_or_none(data.get("detected_language_code")),
            "truncated": data.get("truncated") is True,
            "fields": fields,
        }

    def _error_for_status(self, status: int, raw: bytes) -> STTAPIError:
        gnani_type, gnani_message = _parse_error(raw)
        detail = self._clean(gnani_message)
        if status == 401:
            return STTAuthError("Gnani rejected the API key (HTTP 401). Check GNANI_API_KEY in backend/.env.",
                                status, gnani_type)
        if status == 403:
            # Preserve Gnani's non-secret diagnostic code/message so the UI and
            # Render logs can distinguish account permission from other denials.
            reason = f" Gnani code: {gnani_type}." if gnani_type else ""
            if detail:
                reason += f" Gnani says: {detail}"
            return STTAuthError(
                "Gnani denied this STT request (HTTP 403)." + reason +
                " Check that this API key is enabled for Prisma STT on the Gnani account.",
                status, gnani_type
            )
        if status == 402:
            return STTQuotaError("Gnani reports insufficient credit (HTTP 402). Check the account balance.",
                                 status, gnani_type)
        if status == 429:
            return STTQuotaError("Gnani rate limit or quota reached (HTTP 429). Wait a moment and try again.",
                                 status, gnani_type)
        if status == 504:
            return STTTimeoutError("Gnani transcription timed out (HTTP 504). Try a shorter recording.",
                                   status, gnani_type)
        if status in (400, 422):
            message = GNANI_ERROR_MESSAGES.get(gnani_type or "") or detail or f"Gnani rejected the request (HTTP {status})."
            return STTRequestError(message, status, gnani_type)
        if status >= 500:
            return STTUnavailableError(f"Gnani STT is temporarily unavailable (HTTP {status}). Retry shortly.",
                                       status, gnani_type)
        return STTRequestError(detail or f"Gnani rejected the request (HTTP {status}).", status, gnani_type)
