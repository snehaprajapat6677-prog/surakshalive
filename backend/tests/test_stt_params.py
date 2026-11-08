import unittest

from app.stt_params import ParamError, build_stt_fields, default_format, default_language


class V3ParameterTests(unittest.TestCase):
    def test_default_v3_request_fields(self):
        fields = build_stt_fields("hi-IN,en-IN", "prisma-v3.0")
        self.assertEqual(fields, {"language_code": "hi-IN,en-IN", "format": "codemix", "model": "prisma-v3.0"})

    def test_auto_detect_is_allowed_on_v3(self):
        self.assertEqual(build_stt_fields("indic-auto", "prisma-v3.0")["language_code"], "indic-auto")

    def test_four_languages_allowed_five_rejected(self):
        self.assertIn("hi-IN,en-IN,ta-IN,te-IN", build_stt_fields("hi-IN,en-IN,ta-IN,te-IN", "prisma-v3.0")["language_code"])
        with self.assertRaises(ParamError):
            build_stt_fields("hi-IN,en-IN,ta-IN,te-IN,kn-IN", "prisma-v3.0")

    def test_transliterate_is_v3_only(self):
        self.assertEqual(build_stt_fields("hi-IN", "prisma-v3.0", "transliterate")["format"], "transliterate")
        with self.assertRaises(ParamError):
            build_stt_fields("hi-IN", "prisma-v2.5", "transliterate")


class V2ParameterTests(unittest.TestCase):
    def test_v2_omits_model_field_and_uses_verbatim(self):
        fields = build_stt_fields("hi-IN", "prisma-v2.5")
        self.assertEqual(fields, {"language_code": "hi-IN", "format": "verbatim"})

    def test_v2_rejects_lists_and_auto_detect(self):
        for language in ("hi-IN,en-IN", "indic-auto"):
            with self.subTest(language=language), self.assertRaises(ParamError):
                build_stt_fields(language, "prisma-v2.5")

    def test_v2_rejects_codemix(self):
        with self.assertRaises(ParamError):
            build_stt_fields("hi-IN", "prisma-v2.5", "codemix")


class CommonParameterTests(unittest.TestCase):
    def test_unsupported_codes_are_rejected(self):
        for code in ("xx-XX", "hi", "hi-in", "hindi", ""):
            with self.subTest(code=code), self.assertRaises(ParamError):
                build_stt_fields(code, "prisma-v3.0")

    def test_spaces_inside_a_list_are_ignored(self):
        self.assertEqual(build_stt_fields("hi-IN, en-IN", "prisma-v3.0")["language_code"], "hi-IN,en-IN")

    def test_unknown_model_is_rejected(self):
        with self.assertRaises(ParamError):
            build_stt_fields("hi-IN", "prisma-v9")

    def test_itn_native_numerals_only_with_transcribe(self):
        on = build_stt_fields("hi-IN", "prisma-v3.0", "transcribe", itn_native_numerals=True)
        self.assertEqual(on["itn_native_numerals"], "true")
        off = build_stt_fields("hi-IN", "prisma-v3.0", "codemix", itn_native_numerals=True)
        self.assertNotIn("itn_native_numerals", off)

    def test_defaults_by_model(self):
        self.assertEqual(default_language("prisma-v3.0"), "hi-IN,en-IN")
        self.assertEqual(default_language("prisma-v2.5"), "hi-IN")
        self.assertEqual(default_format("prisma-v3.0"), "codemix")
        self.assertEqual(default_format("prisma-v2.5"), "verbatim")

    def test_preferred_language_is_never_sent(self):
        self.assertNotIn("preferred_language", build_stt_fields("hi-IN,en-IN", "prisma-v3.0"))


if __name__ == "__main__":
    unittest.main()
