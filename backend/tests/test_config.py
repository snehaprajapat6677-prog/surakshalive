import os
import tempfile
import unittest
from pathlib import Path

from app.config import load_env_file, load_settings


class SettingsTests(unittest.TestCase):
    def test_defaults(self):
        s = load_settings({})
        self.assertEqual((s.gnani_api_key, s.max_upload_mb), ("", 10))
        self.assertEqual(s.gnani_stt_url, "https://api.vachana.ai/stt/v3")

    def test_upload_limit_is_clamped(self):
        self.assertEqual(load_settings({"MAX_UPLOAD_MB": "999"}).max_upload_mb, 25)
        self.assertEqual(load_settings({"MAX_UPLOAD_MB": "0"}).max_upload_mb, 1)
        self.assertEqual(load_settings({"MAX_UPLOAD_MB": "abc"}).max_upload_mb, 10)

    def test_key_is_trimmed(self):
        self.assertEqual(load_settings({"GNANI_API_KEY": "  k  "}).gnani_api_key, "k")


class EnvFileTests(unittest.TestCase):
    def test_loads_values_without_overriding_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("# comment\nGNANI_API_KEY=from-file\nSURAKSHA_TEST_VALUE='quoted'\n", encoding="utf-8")
            old = os.environ.get("GNANI_API_KEY")
            os.environ["GNANI_API_KEY"] = "already-set"
            os.environ.pop("SURAKSHA_TEST_VALUE", None)
            try:
                load_env_file(path)
                self.assertEqual(os.environ["GNANI_API_KEY"], "already-set")
                self.assertEqual(os.environ["SURAKSHA_TEST_VALUE"], "quoted")
            finally:
                os.environ.pop("SURAKSHA_TEST_VALUE", None)
                if old is None:
                    os.environ.pop("GNANI_API_KEY", None)
                else:
                    os.environ["GNANI_API_KEY"] = old

    def test_missing_file_is_ignored(self):
        load_env_file(Path("/nonexistent/suraksha/.env"))


if __name__ == "__main__":
    unittest.main()
