import json
import unittest
from pathlib import Path

from app.service import MB, ServiceError, analyze_transcript, transcribe_and_analyze, transcribe_audio
from app.stt import GnaniSTTClient

ROOT = Path(__file__).resolve().parents[2]
DEMO = (ROOT / "sample-scripts" / "digital-arrest.txt").read_text(encoding="utf-8")
FIXTURE = json.loads((ROOT / "shared" / "sample-analysis.json").read_text(encoding="utf-8"))


def fake(status=200, transcript=DEMO, exc=None):
    def transport(url, key, data, ctype, timeout):
        if exc is not None:
            raise exc
        if status != 200:
            return status, b""
        return 200, json.dumps({"success": True, "transcript": transcript}).encode("utf-8")
    return transport


def client(key="test-key", **kwargs):
    return GnaniSTTClient(api_key=key, transport=fake(**kwargs))


class TextAnalysisTests(unittest.TestCase):
    def test_empty_transcript_is_rejected(self):
        for text in ("", "   \n  "):
            with self.subTest(text=text), self.assertRaises(ServiceError) as ctx:
                analyze_transcript(text)
            self.assertEqual(ctx.exception.status_code, 422)

    def test_overlong_transcript_is_rejected(self):
        with self.assertRaises(ServiceError) as ctx:
            analyze_transcript("a" * 20001)
        self.assertEqual(ctx.exception.status_code, 413)

    def test_demo_script_is_high_risk(self):
        self.assertEqual(analyze_transcript(DEMO)["risk_level"], "HIGH")


class AudioTranscriptionTests(unittest.TestCase):
    def test_invalid_language_code(self):
        with self.assertRaises(ServiceError) as ctx:
            transcribe_audio(client(), b"RIFF", "a.wav", "hindi", 10)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_oversize_audio_is_rejected_before_calling_gnani(self):
        calls = []

        def spy(url, key, data, ctype, timeout):
            calls.append(url)
            return 200, b"{}"

        with self.assertRaises(ServiceError) as ctx:
            transcribe_audio(GnaniSTTClient(api_key="k", transport=spy), b"x" * (MB + 1), "a.wav", "hi-IN", 1)
        self.assertEqual(ctx.exception.status_code, 413)
        self.assertEqual(calls, [])

    def test_unsupported_extension_is_rejected(self):
        with self.assertRaises(ServiceError) as ctx:
            transcribe_audio(client(), b"data", "a.exe", "hi-IN", 10)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_missing_key_maps_to_503_and_names_the_setting(self):
        with self.assertRaises(ServiceError) as ctx:
            transcribe_audio(client(key=""), b"RIFF", "a.wav", "hi-IN", 10)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("GNANI_API_KEY", ctx.exception.detail)

    def test_gnani_outage_maps_to_502(self):
        with self.assertRaises(ServiceError) as ctx:
            transcribe_audio(client(status=503), b"RIFF", "a.wav", "hi-IN", 10)
        self.assertEqual(ctx.exception.status_code, 502)

    def test_error_detail_never_contains_the_key(self):
        with self.assertRaises(ServiceError) as ctx:
            transcribe_audio(client(key="secret-xyz", status=401), b"RIFF", "a.wav", "hi-IN", 10)
        self.assertNotIn("secret-xyz", ctx.exception.detail)

    def test_silent_audio_gives_low_risk(self):
        result = transcribe_and_analyze(client(transcript=""), b"RIFF", "a.wav", "hi-IN", 10)
        self.assertFalse(result["speech_detected"])
        self.assertEqual(result["analysis"]["risk_level"], "LOW")


class PipelineContractTests(unittest.TestCase):
    def test_pipeline_matches_shared_fixture_shape(self):
        result = transcribe_and_analyze(client(), b"RIFF", "call.wav", "hi-IN", 10)
        self.assertEqual(set(result), set(FIXTURE))
        self.assertEqual(set(result["analysis"]), set(FIXTURE["analysis"]))
        self.assertEqual(result["analysis"]["risk_level"], FIXTURE["analysis"]["risk_level"])
        self.assertEqual(result["mode"], "batch")


if __name__ == "__main__":
    unittest.main()
