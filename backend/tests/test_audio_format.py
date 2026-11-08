import io
import unittest
import wave

from app.audio_format import AudioError, check_container, detect_container, wav_duration_seconds
from app.stt import validate_upload


def make_wav(seconds, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()


class ContainerDetectionTests(unittest.TestCase):
    def test_detects_each_supported_container(self):
        cases = {
            "wav": make_wav(0.1),
            "ogg": b"OggS\x00\x02" + b"\x00" * 20,
            "flac": b"fLaC\x00\x00\x00\x22" + b"\x00" * 20,
            "mp3": b"ID3\x03\x00" + b"\x00" * 20,
            "mp4": b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 20,
        }
        for expected, data in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(detect_container(data), expected)

    def test_webm_is_detected_by_ebml_header(self):
        self.assertEqual(detect_container(b"\x1a\x45\xdf\xa3" + b"\x00" * 20), "webm")

    def test_unknown_bytes_are_not_blocked_here(self):
        self.assertIsNone(detect_container(b"fake-audio"))
        check_container(b"fake-audio")  # passes through to Gnani, which decides

    def test_riff_without_wave_tag_is_refused(self):
        with self.assertRaises(AudioError):
            check_container(b"RIFF\x00\x00\x00\x00AVI LIST" + b"\x00" * 8)


class WebmRefusalTests(unittest.TestCase):
    def test_webm_upload_gets_a_clear_message(self):
        with self.assertRaises(AudioError) as ctx:
            check_container(b"\x1a\x45\xdf\xa3" + b"\x00" * 50)
        self.assertIn("WebM", str(ctx.exception))
        self.assertIn("WAV", str(ctx.exception))

    def test_webm_filename_is_refused_by_extension_check(self):
        with self.assertRaises(ValueError):
            validate_upload("call.webm", 100)


class WavDurationTests(unittest.TestCase):
    def test_wav_reports_its_length(self):
        self.assertAlmostEqual(wav_duration_seconds(make_wav(2.0)), 2.0, places=2)

    def test_thirty_seconds_is_allowed(self):
        check_container(make_wav(30.0))

    def test_longer_than_thirty_seconds_is_refused(self):
        with self.assertRaises(AudioError) as ctx:
            check_container(make_wav(31.0))
        self.assertIn("30 seconds", str(ctx.exception))

    def test_unreadable_header_is_left_to_gnani(self):
        self.assertIsNone(wav_duration_seconds(b"RIFF"))
        check_container(b"RIFF")

    def test_accepted_extensions_match_gnani_docs(self):
        for name in ("a.wav", "a.mp3", "a.ogg", "a.flac", "a.aac", "a.m4a"):
            with self.subTest(name=name):
                validate_upload(name, 100)


if __name__ == "__main__":
    unittest.main()
