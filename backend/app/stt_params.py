"""Request options for Gnani's Prisma REST endpoint.

Checked against docs.gnani.ai/api/STT/speech-to-text.md on 2026-11-06:
- Prisma v2.5 (used when `model` is left out): one language code; format verbatim or transcribe.
- Prisma v3.0 (`model=prisma-v3.0`): language_code may be `indic-auto` or 1-4 comma-separated codes;
  format verbatim, transcribe, codemix or transliterate.
- `preferred_language` is not a field in the REST reference, so this code never sends it.
- `itn_native_numerals` is a boolean that only has an effect when format=transcribe.
"""
from __future__ import annotations

V2_MODEL = "prisma-v2.5"
V3_MODEL = "prisma-v3.0"
SUPPORTED_MODELS = (V2_MODEL, V3_MODEL)
DEFAULT_MODEL = V3_MODEL
AUTO_LANGUAGE = "indic-auto"
MAX_LANGUAGES = 4
SUPPORTED_LANGUAGES = (
    "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN",
    "ml-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN",
)
V2_FORMATS = ("verbatim", "transcribe")
V3_FORMATS = ("verbatim", "transcribe", "codemix", "transliterate")


class ParamError(ValueError):
    """A request option that Gnani's REST reference does not allow for the chosen model."""


def default_language(model: str) -> str:
    return "hi-IN,en-IN" if model == V3_MODEL else "hi-IN"


def default_format(model: str) -> str:
    return "codemix" if model == V3_MODEL else "verbatim"


def build_stt_fields(language_code: str, model: str = DEFAULT_MODEL,
                     output_format: str | None = None,
                     itn_native_numerals: bool = False) -> dict:
    """Return the multipart form fields (besides audio_file) for one request. Raises ParamError."""
    if model not in SUPPORTED_MODELS:
        raise ParamError(f"Unknown model '{model}'. Use {V2_MODEL} or {V3_MODEL}.")
    language = (language_code or "").replace(" ", "")
    if not language:
        raise ParamError("language_code is required, for example hi-IN.")
    output_format = output_format or default_format(model)
    allowed_formats = V3_FORMATS if model == V3_MODEL else V2_FORMATS
    if output_format not in allowed_formats:
        raise ParamError(f"Format '{output_format}' is not available with {model}. "
                         f"Use one of: {', '.join(allowed_formats)}.")
    _check_language(language, model)
    fields = {"language_code": language, "format": output_format}
    if model == V3_MODEL:
        fields["model"] = V3_MODEL
    if output_format == "transcribe" and itn_native_numerals:
        fields["itn_native_numerals"] = "true"
    return fields


def _check_language(language: str, model: str) -> None:
    if language == AUTO_LANGUAGE:
        if model != V3_MODEL:
            raise ParamError(f"Auto-detect needs {V3_MODEL}. Choose one language, such as hi-IN.")
        return
    codes = language.split(",")
    if len(codes) > 1 and model != V3_MODEL:
        raise ParamError(f"A language list needs {V3_MODEL}. Choose one language, such as hi-IN.")
    if len(codes) > MAX_LANGUAGES:
        raise ParamError(f"Use at most {MAX_LANGUAGES} language codes, got {len(codes)}.")
    for code in codes:
        if code not in SUPPORTED_LANGUAGES:
            raise ParamError(f"Unsupported language code '{code}'. "
                             f"Supported: {', '.join(SUPPORTED_LANGUAGES)}.")
