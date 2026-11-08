import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { RISK_LABELS, flaggedLineNumbers, modeLabel, riskTone, ruleTitle, scoreSummary } from "./format.js";

const here = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(join(here, "../../../shared/sample-analysis.json"), "utf8"));

test("risk levels map to display tones and labels", () => {
  assert.equal(riskTone("LOW"), "low");
  assert.equal(riskTone("MEDIUM"), "medium");
  assert.equal(riskTone("HIGH"), "high");
  assert.equal(riskTone("UNKNOWN"), "unknown");
  assert.equal(RISK_LABELS.HIGH, "High risk");
});

test("rule ids become readable titles and keep acronyms", () => {
  assert.equal(ruleTitle("OTP_REQUEST"), "OTP request");
  assert.equal(ruleTitle("UPI_PIN_REQUEST"), "UPI PIN request");
  assert.equal(ruleTitle("URGENCY"), "Urgency");
});

test("score summary states the thresholds the backend used", () => {
  const text = scoreSummary({ score: 13, thresholds: { medium_at: 2, high_at: 6 } });
  assert.match(text, /13 points/);
  assert.match(text, /HIGH from 6/);
});

test("mode label is honest that batch mode is not streaming", () => {
  assert.match(modeLabel("batch"), /not real-time streaming/);
});

test("flagged line numbers come from the evidence in the real fixture", () => {
  const lines = flaggedLineNumbers(fixture.analysis);
  assert.ok(lines.size > 0);
  assert.ok(lines.has(1));
  assert.equal(riskTone(fixture.analysis.risk_level), "high");
});

test("flagged line numbers are empty without an analysis", () => {
  assert.equal(flaggedLineNumbers(null).size, 0);
});
