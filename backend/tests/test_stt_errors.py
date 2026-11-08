"""Error handling and request shape for the Gnani client and service layer. All responses are mocked."""
import json
import socket
import unittest
from urllib.error import URLError

from app.service import ServiceError, transcribe_and_analyze, transcribe_audio
from app.stt import (GnaniSTTClient, STTAPIError, STTAuthError, STTConfigError, STTQuotaError,
                     STTRequestError, STTResponseError, STTTimeoutError, STTUnavailableError)
from app.stt_params import ParamError

WAV = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 16
KEY = "live-key-do-not-leak"


def reply(status, body=None, raw=None):
    payload = raw if raw is not None else json.dumps(body or {}).encode("utf-8")

    def transport(url, key, data, ctype, timeout):
        transport.calls.append({"url": url, "key": key, "data": data, "ctype": ctype})
        if isinstance(payload, BaseException):
            raise payload
        return status, payload

    transport.calls = []
    return transport


def client(transport, key=KEY):
    return GnaniSTTClient(api_key=key, transport=transport)


class RequestShapeTests(unittest.TestCase):
    def test_v3_request_carries_model_language_and_format(self):
        t = reply(200, {"success": True, "transcript": "ok"})
        client(t).transcribe(WAV, "call.wav", "hi-IN,en-IN")
        body = t.calls[0]["data"]
        self.assertIn(b'name="model"\r\n\r\nprisma-v3.0', body)
        self.assertIn(b'name="language_code"\r\n\r\nhi-IN,en-IN', body)
        self.assertIn(b'name="format"\r\n\r\ncodemix', body)
        self.assertNotIn(b"preferred_language", body)

    def test_v2_request_omits_model_field(self):
        t = reply(200, {"success": True, "transcript": "ok"})
        client(t).transcribe(WAV, "call.wav", "hi-IN", model="prisma-v2.5")
        self.assertNotIn(b'name="model"', t.calls[0]["data"])

    def test_invalid_options_never_reach_the_network(self):
        t = reply(200, {"success": True, "transcript": "ok"})
        with self.assertRaises(ParamError):
            client(t).transcribe(WAV, "call.wav", "indic-auto", model="prisma-v2.5")
        self.assertEqual(t.calls, [])

    def test_success_returns_detected_language_model_and_truncation(self):
        t = reply(200, {"success": True, "transcript": "मेरा खाता", "model": "prisma-v3.0",
                        "detected_language_code": "hi-IN", "truncated": True})
        result = client(t).transcribe_detailed(WAV, "call.wav", "indic-auto")
        self.assertEqual(result["transcript"], "मेरा खाता")
        self.assertEqual(result["detected_language_code"], "hi-IN")
        self.assertEqual(result["model"], "prisma-v3.0")
        self.assertTrue(result["truncated"])

    def test_success_without_success_field_is_still_accepted(self):
        t = reply(200, {"transcript": "hello"})
        self.assertEqual(client(t).transcribe(WAV, "call.wav", "en-IN"), "hello")

    def test_empty_transcript_is_a_valid_answer(self):
        t = reply(200, {"success": True, "transcript": ""})
        self.assertEqual(client(t).transcribe(WAV, "call.wav"), "")

    def test_missing_transcript_is_a_response_error(self):
        with self.assertRaises(STTResponseError):
            client(reply(200, {"success": True})).transcribe(WAV, "call.wav")


class GnaniErrorMappingTests(unittest.TestCase):
    def test_status_codes_map_to_error_kinds(self):
        cases = [
            (401, STTAuthError), (403, STTAuthError), (402, STTQuotaError), (429, STTQuotaError),
            (400, STTRequestError), (422, STTRequestError), (504, STTTimeoutError),
            (500, STTUnavailableError), (503, STTUnavailableError), (502, STTUnavailableError),
        ]
        for status, expected in cases:
            with self.subTest(status=status):
                with self.assertRaises(expected):
                    client(reply(status, raw=b"")).transcribe(WAV, "call.wav")

    def test_gnani_error_type_gives_a_specific_message(self):
        body = {"success": False, "error": {"type": "UNSUPPORTED_AUDIO_FORMAT", "message": "nope"}}
        with self.assertRaises(STTRequestError) as ctx:
            client(reply(400, body)).transcribe(WAV, "call.wav")
        self.assertIn("WAV, MP3, OGG, FLAC, AAC or M4A", str(ctx.exception))
        self.assertEqual(ctx.exception.gnani_type, "UNSUPPORTED_AUDIO_FORMAT")

    def test_duration_error_mentions_the_limit(self):
        body = {"success": False, "error": {"type": "MAX_AUDIO_DURATION_EXCEEDED", "message": "x"}}
        with self.assertRaises(STTRequestError) as ctx:
            client(reply(400, body)).transcribe(WAV, "call.wav")
        self.assertIn("30-second", str(ctx.exception))

    def test_rate_limit_detail_shape_is_understood(self):
        body = {"detail": {"error_code": "RATE_LIMITED", "message": "Only 1 active request", "status_code": 429}}
        with self.assertRaises(STTQuotaError):
            client(reply(429, body)).transcribe(WAV, "call.wav")

    def test_gateway_timeout_shape_is_understood(self):
        body = {"error": "Gateway Timeout", "code": "UPSTREAM_TIMEOUT", "message": "too slow"}
        with self.assertRaises(STTTimeoutError):
            client(reply(504, body)).transcribe(WAV, "call.wav")

    def test_network_failures_are_unavailable_or_timeout(self):
        with self.assertRaises(STTUnavailableError):
            client(reply(0, raw=URLError("no route"))).transcribe(WAV, "call.wav")
        with self.assertRaises(STTTimeoutError):
            client(reply(0, raw=socket.timeout("slow"))).transcribe(WAV, "call.wav")

    def test_success_false_is_an_api_error(self):
        body = {"success": False, "error": {"type": "TRANSCRIPTION_FAILED", "message": "try again"}}
        with self.assertRaises(STTAPIError) as ctx:
            client(reply(200, body)).transcribe(WAV, "call.wav")
        self.assertEqual(ctx.exception.gnani_type, "TRANSCRIPTION_FAILED")


class SecretHandlingTests(unittest.TestCase):
    def test_key_is_redacted_if_gnani_echoes_it(self):
        body = {"success": False, "error": {"type": "INVALID_CONTEXT", "message": f"bad key {KEY}"}}
        with self.assertRaises(STTRequestError) as ctx:
            client(reply(422, body)).transcribe(WAV, "call.wav")
        self.assertNotIn(KEY, str(ctx.exception))

    def test_no_error_kind_contains_the_key(self):
        for status in (400, 401, 402, 403, 429, 503, 504):
            with self.subTest(status=status):
                t = reply(status, {"success": False, "error": {"type": "X", "message": KEY}})
                with self.assertRaises(STTAPIError) as ctx:
                    client(t).transcribe(WAV, "call.wav")
                self.assertNotIn(KEY, str(ctx.exception))

    def test_missing_key_fails_before_any_request(self):
        t = reply(200, {"success": True, "transcript": "x"})
        with self.assertRaises(STTConfigError):
            client(t, key="").transcribe(WAV, "call.wav")
        self.assertEqual(t.calls, [])

    def test_request_never_writes_the_key_into_the_body(self):
        t = reply(200, {"success": True, "transcript": "x"})
        client(t).transcribe(WAV, "call.wav")
        self.assertNotIn(KEY.encode(), t.calls[0]["data"])


class ServiceMappingTests(unittest.TestCase):
    def run_service(self, transport, **kwargs):
        return transcribe_audio(client(transport), kwargs.get("data", WAV), "call.wav",
                                kwargs.get("language", "hi-IN,en-IN"), 10, kwargs.get("model", "prisma-v3.0"))

    def test_insufficient_credit_becomes_402(self):
        with self.assertRaises(ServiceError) as ctx:
            self.run_service(reply(402, raw=b""))
        self.assertEqual(ctx.exception.status_code, 402)

    def test_rate_limit_becomes_429(self):
        with self.assertRaises(ServiceError) as ctx:
            self.run_service(reply(429, raw=b""))
        self.assertEqual(ctx.exception.status_code, 429)

    def test_bad_audio_becomes_422_with_gnani_message(self):
        body = {"success": False, "error": {"type": "AUDIO_CONVERSION_ERROR", "message": "x"}}
        with self.assertRaises(ServiceError) as ctx:
            self.run_service(reply(400, body))
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("could not decode", ctx.exception.detail)

    def test_timeout_becomes_504(self):
        with self.assertRaises(ServiceError) as ctx:
            self.run_service(reply(0, raw=TimeoutError()))
        self.assertEqual(ctx.exception.status_code, 504)

    def test_bad_key_becomes_503_without_leaking_it(self):
        with self.assertRaises(ServiceError) as ctx:
            self.run_service(reply(401, raw=b""))
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertNotIn(KEY, ctx.exception.detail)

    def test_auto_detect_on_v2_is_422_before_upload(self):
        t = reply(200, {"success": True, "transcript": "x"})
        with self.assertRaises(ServiceError) as ctx:
            transcribe_audio(client(t), WAV, "call.wav", "indic-auto", 10, "prisma-v2.5")
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(t.calls, [])

    def test_webm_bytes_are_refused_before_upload(self):
        t = reply(200, {"success": True, "transcript": "x"})
        with self.assertRaises(ServiceError) as ctx:
            transcribe_audio(client(t), b"\x1a\x45\xdf\xa3" + b"\x00" * 40, "call.wav", "hi-IN", 10)
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(t.calls, [])

    def test_summary_reports_settings_and_detected_language(self):
        t = reply(200, {"success": True, "transcript": "OTP batao", "detected_language_code": "hi-IN"})
        result = transcribe_and_analyze(client(t), WAV, "call.wav", "indic-auto", 10, "prisma-v3.0")
        self.assertEqual(result["stt"]["model"], "prisma-v3.0")
        self.assertEqual(result["stt"]["language_code"], "indic-auto")
        self.assertEqual(result["stt"]["format"], "codemix")
        self.assertEqual(result["stt"]["detected_language_code"], "hi-IN")
        self.assertEqual(result["analysis"]["risk_level"], "HIGH")


class SourceHygieneTests(unittest.TestCase):
    def test_backend_code_does_not_print_or_log(self):
        from pathlib import Path
        app_dir = Path(__file__).resolve().parents[1] / "app"
        for path in app_dir.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertNotIn("print(", text)
                self.assertNotIn("import logging", text)


if __name__ == "__main__":
    unittest.main()
