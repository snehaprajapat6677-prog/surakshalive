import json
import unittest

from app.stt import GnaniSTTClient, STTAPIError, STTConfigError, validate_upload


def fake_transport(status=200, body=None, exc=None, calls=None):
    def transport(url, key, data, content_type, timeout):
        if calls is not None:
            calls.append({"url": url, "key": key, "data": data, "ctype": content_type})
        if exc is not None:
            raise exc
        payload = body if body is not None else json.dumps({"success": True, "transcript": "नमस्ते"}).encode()
        return status, payload
    return transport


class GnaniSTTClientTests(unittest.TestCase):
    def test_missing_key_fails_before_any_request(self):
        calls = []
        client = GnaniSTTClient(api_key="", transport=fake_transport(calls=calls))
        with self.assertRaises(STTConfigError):
            client.transcribe(b"RIFF", "a.wav")
        self.assertEqual(calls, [])

    def test_success_returns_transcript(self):
        client = GnaniSTTClient(api_key="test-key", transport=fake_transport())
        self.assertEqual(client.transcribe(b"RIFF", "a.wav", "hi-IN"), "नमस्ते")

    def test_request_uses_documented_header_and_fields(self):
        calls = []
        GnaniSTTClient(api_key="test-key", transport=fake_transport(calls=calls)).transcribe(b"AUDIO", "a.wav", "hi-IN")
        call = calls[0]
        self.assertEqual(call["url"], "https://api.vachana.ai/stt/v3")
        self.assertEqual(call["key"], "test-key")
        self.assertTrue(call["ctype"].startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="language_code"', call["data"])
        self.assertIn(b"hi-IN", call["data"])
        self.assertIn(b'name="audio_file"', call["data"])
        self.assertIn(b"AUDIO", call["data"])

    def test_timeout_becomes_api_error(self):
        client = GnaniSTTClient(api_key="k", transport=fake_transport(exc=TimeoutError()))
        with self.assertRaises(STTAPIError):
            client.transcribe(b"RIFF", "a.wav")

    def test_server_error_message(self):
        client = GnaniSTTClient(api_key="k", transport=fake_transport(status=503, body=b""))
        with self.assertRaisesRegex(STTAPIError, "temporarily unavailable"):
            client.transcribe(b"RIFF", "a.wav")

    def test_bad_key_error_never_echoes_the_key(self):
        client = GnaniSTTClient(api_key="secret-123", transport=fake_transport(status=401, body=b""))
        with self.assertRaises(STTAPIError) as ctx:
            client.transcribe(b"RIFF", "a.wav")
        self.assertNotIn("secret-123", str(ctx.exception))

    def test_non_json_response(self):
        client = GnaniSTTClient(api_key="k", transport=fake_transport(body=b"<html>"))
        with self.assertRaises(STTAPIError):
            client.transcribe(b"RIFF", "a.wav")

    def test_response_without_transcript(self):
        client = GnaniSTTClient(api_key="k", transport=fake_transport(body=b'{"success": false}'))
        with self.assertRaises(STTAPIError):
            client.transcribe(b"RIFF", "a.wav")


class UploadValidationTests(unittest.TestCase):
    def test_rejects_unsupported_extension(self):
        with self.assertRaises(ValueError):
            validate_upload("notes.exe", 100)

    def test_rejects_empty_file(self):
        with self.assertRaises(ValueError):
            validate_upload("a.wav", 0)

    def test_rejects_oversized_file(self):
        with self.assertRaises(ValueError):
            validate_upload("a.wav", 11 * 1024 * 1024)

    def test_accepts_valid_file(self):
        validate_upload("call.WAV", 1000)


if __name__ == "__main__":
    unittest.main()
