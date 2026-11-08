"""Settings from environment variables and an optional backend/.env file (no third-party dependency)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.stt import GNANI_STT_URL
from app.stt_params import DEFAULT_MODEL

BACKEND_DIR = Path(__file__).resolve().parents[1]
MAX_UPLOAD_CAP_MB = 25


@dataclass(frozen=True)
class Settings:
    gnani_api_key: str
    gnani_stt_url: str
    max_upload_mb: int
    stt_model: str = DEFAULT_MODEL


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ. Existing environment variables win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_settings(env=None) -> Settings:
    env = os.environ if env is None else env
    try:
        max_mb = int(env.get("MAX_UPLOAD_MB", "10"))
    except ValueError:
        max_mb = 10
    return Settings(
        gnani_api_key=env.get("GNANI_API_KEY", "").strip(),
        gnani_stt_url=(env.get("GNANI_STT_URL") or GNANI_STT_URL).strip(),
        max_upload_mb=min(max(max_mb, 1), MAX_UPLOAD_CAP_MB),
        stt_model=(env.get("GNANI_STT_MODEL") or DEFAULT_MODEL).strip(),
    )
