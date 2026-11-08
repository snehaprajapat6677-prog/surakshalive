import unittest
from pathlib import Path

from app.detection import analyze, normalize

SAMPLES = Path(__file__).resolve().parents[2] / "sample-scripts"


def ids(result):
    return {i["rule_id"] for i in result["indicators"]}


class SampleScenarioTests(unittest.TestCase):
    EXPECTED = {
        "digital-arrest.txt": ("HIGH", "DIGITAL_ARREST", {"DA_ARREST", "DA_PAYMENT_DEMAND"}),
        "fake-kyc.txt": ("HIGH", "FAKE_KYC_BANK", {"OTP_REQUEST", "CREDENTIAL_REQUEST"}),
        "upi-refund.txt": ("HIGH", "UPI_PAYMENT", {"UPI_PIN_REQUEST", "COLLECT_APPROVAL"}),
        "legitimate-call.txt": ("LOW", None, set()),
    }

    def test_scenarios_match_expected_risk(self):
        for name, (risk, category, rules) in self.EXPECTED.items():
            with self.subTest(name=name):
                result = analyze((SAMPLES / name).read_text(encoding="utf-8"))
                self.assertEqual(result["risk_level"], risk)
                self.assertEqual(result["category"], category)
                self.assertTrue(rules <= ids(result), f"missing {rules - ids(result)}")


class LanguageTests(unittest.TestCase):
    def test_hinglish_otp_request(self):
        self.assertIn("OTP_REQUEST", ids(analyze("Aapke account ka OTP batao")))

    def test_hindi_otp_request(self):
        self.assertIn("OTP_REQUEST", ids(analyze("कृपया अपना ओटीपी बताइए")))

    def test_hindi_upi_pin_request(self):
        self.assertIn("UPI_PIN_REQUEST", ids(analyze("आप यूपीआई पिन डालें ताकि पैसे आ सकें")))

    def test_normalize_unifies_spellings(self):
        self.assertEqual(normalize("OT\u200bP"), "otp")
        self.assertEqual(normalize("माँगते"), normalize("मांगते"))
        self.assertEqual(normalize("ज़मानत"), normalize("जमानत"))


class RuleBehaviourTests(unittest.TestCase):
    def test_bank_warning_is_not_flagged(self):
        result = analyze("We will never ask for your OTP. Never share it with anyone.")
        self.assertNotIn("OTP_REQUEST", ids(result))
        self.assertEqual(result["risk_level"], "LOW")

    def test_upi_pin_warning_is_not_flagged(self):
        self.assertNotIn("UPI_PIN_REQUEST", ids(analyze("Never enter your UPI PIN to receive money.")))

    def test_urgency_alone_stays_low(self):
        result = analyze("This is urgent, please call back today.")
        self.assertEqual(result["risk_level"], "LOW")

    def test_pressure_with_money_demand_is_medium(self):
        self.assertEqual(analyze("Pay a fine to avoid trouble.")["risk_level"], "MEDIUM")

    def test_critical_indicator_forces_high(self):
        result = analyze("Install AnyDesk now and share your screen.")
        self.assertEqual(result["risk_level"], "HIGH")
        self.assertTrue(result["critical_indicator"])

    def test_evidence_keeps_original_line(self):
        result = analyze("Caller: send me the OTP now")
        evidence = result["indicators"][0]["evidence"][0]
        self.assertEqual(evidence, {"line": 1, "text": "Caller: send me the OTP now"})

    def test_empty_transcript(self):
        result = analyze("")
        self.assertEqual((result["risk_level"], result["utterance_count"], result["indicators"]), ("LOW", 0, []))


if __name__ == "__main__":
    unittest.main()
