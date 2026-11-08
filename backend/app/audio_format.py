"""Audio checks based on Gnani's REST reference (checked 2026-11-06).

Accepted by Gnani: WAV, MP3, OGG, FLAC, AAC, M4A. WebM is not on that list, so the
browser converts recordings to WAV before upload. Maximum length for REST: 30 seconds.
Only clear mismatches are rejected here. Anything unreadable goes to Gnani, which returns
its own error, so valid-but-unusual files are not blocked by this code.
"""
from __future__ import annotations

import io
import struct
import wave

MAX_REST_SECONDS = 30
EBML_MAGIC = b"\x1a\x45\xdf\xa3"


class AudioError(ValueError):
    """Audio that the backend refuses before calling Gnani."""


def detect_container(data: bytes) -> str | None:
    head = data[:12]
    if head[:4] == EBML_MAGIC:
        return "webm"
    if head[:4] == b"RIFF":
        return "wav" if len(head) < 12 or head[8:12] == b"WAVE" else "riff-other"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"fLaC":
        return "flac"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return "mp4"
    return None


def wav_duration_seconds(data: bytes) -> float | None:
    """Length of a WAV file in seconds, or None when the header cannot be read."""
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            frames, rate = wav.getnframes(), wav.getframerate()
    except (wave.Error, EOFError, struct.error):
        return None
    if rate <= 0:
        return None
    return frames / rate


def check_container(data: bytes) -> None:
    kind = detect_container(data)
    if kind == "webm":
        raise AudioError("WebM audio is not accepted by Gnani. The app converts recordings to WAV; "
                         "upload WAV, MP3, OGG, FLAC, AAC or M4A instead.")
    if kind == "riff-other":
        raise AudioError("The file has a RIFF header but is not a WAV file.")
    if kind == "wav":
        seconds = wav_duration_seconds(data)
        if seconds is not None and seconds > MAX_REST_SECONDS:
            raise AudioError(f"Audio is {seconds:.1f} seconds long. Gnani's REST endpoint accepts "
                             f"up to {MAX_REST_SECONDS} seconds.")
