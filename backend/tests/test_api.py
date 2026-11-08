"""HTTP-level integration tests. They need FastAPI and httpx (see requirements.txt).
Gnani is replaced with a fake transport, so no credits are used."""
import json
import unittest
from pathlib import Path

from app.config import Settings
from app.stt import GnaniSTTClient

try:
    from fastapi.testclient import TestClient
    from app.main import app, get_settings, get_stt_client
    HAVE_FASTAPI = True
except ImportError:
    HAVE_FASTAPI = False

SAMPLE = (Path(__file__).resolve().parents[2] / "sample-scripts" / "digital-arrest.txt").read_text(encoding="utf-8")
GNANI_URL = "https://api.vachana.ai/stt/v3"


def transport(status=200, transcript=SAMPLE):
    def call(url, key, data, ctype, timeout):
        if status != 200:
            return status, b""
        return 200, json.dumps({"success": True, "transcript": transcript}).encode("utf-8")
    return call


def settings(key="test-key", max_mb=10):
    return Settings(gnani_api_key=key, gnani_stt_url=GNANI_URL, max_upload_mb=max_mb)


@unittest.skipUnless(HAVE_FASTAPI, "Install backend/requirements.txt to run the API tests")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.http = TestClient(app)
        self.use(settings(), transport())

    def tearDown(self):
        app.dependency_overrides.clear()

    def use(self, cfg, fake):
        stt = GnaniSTTClient(api_key=cfg.gnani_api_key, url=cfg.gnani_stt_url, transport=fake)
        app.dependency_overrides[get_settings] = lambda: cfg
        app.dependency_overrides[get_stt_client] = lambda: stt

    def test_health_reports_key_presence_without_revealing_it(self):
        self.use(settings(key="super-secret-key"), transport())
        r = self.http.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["gnani_configured"])
        self.assertNotIn("super-secret-key", r.text)

    def test_analyze_text_returns_risk(self):
        r = self.http.post("/api/analyze", json={"transcript": SAMPLE})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["risk_level"], "HIGH")

    def test_analyze_text_rejects_empty_input(self):
        self.assertEqual(self.http.post("/api/analyze", json={"transcript": ""}).status_code, 422)
        self.assertEqual(self.http.post("/api/analyze", json={"transcript": "   "}).status_code, 422)

    def test_analyze_audio_returns_transcript_and_analysis(self):
        r = self.http.post("/api/analyze-audio",
                           files={"file": ("call.wav", b"fake-audio", "audio/wav")},
                           data={"language_code": "hi-IN"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["transcript"], SAMPLE)
        self.assertEqual(body["analysis"]["risk_level"], "HIGH")
        self.assertEqual(body["mode"], "batch")

    def test_transcribe_endpoint_returns_text_only(self):
        r = self.http.post("/api/transcribe", files={"file": ("call.wav", b"RIFF", "audio/wav")})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["transcript"], SAMPLE)
        self.assertNotIn("analysis", r.json())

    def test_unsupported_file_type_returns_422(self):
        r = self.http.post("/api/analyze-audio", files={"file": ("notes.exe", b"x", "application/octet-stream")})
        self.assertEqual(r.status_code, 422)

    def test_missing_key_returns_503(self):
        self.use(settings(key=""), transport())
        r = self.http.post("/api/analyze-audio", files={"file": ("call.wav", b"RIFF", "audio/wav")})
        self.assertEqual(r.status_code, 503)
        self.assertIn("GNANI_API_KEY", r.json()["detail"])

    def test_gnani_outage_returns_502(self):
        self.use(settings(), transport(status=503))
        r = self.http.post("/api/analyze-audio", files={"file": ("call.wav", b"RIFF", "audio/wav")})
        self.assertEqual(r.status_code, 502)

    def test_gnani_insufficient_credit_returns_402(self):
        self.use(settings(), transport(status=402))
        r = self.http.post("/api/analyze-audio", files={"file": ("call.wav", b"RIFF", "audio/wav")})
        self.assertEqual(r.status_code, 402)

    def test_oversize_upload_returns_413(self):
        self.use(settings(max_mb=1), transport())
        big = b"x" * (1024 * 1024 + 10)
        r = self.http.post("/api/analyze-audio", files={"file": ("call.wav", big, "audio/wav")})
        self.assertEqual(r.status_code, 413)


if __name__ == "__main__":
    unittest.main()
