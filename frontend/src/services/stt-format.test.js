import { test } from "node:test";
import assert from "node:assert/strict";
import { LANGUAGE_OPTIONS, sttSummaryText } from "./format.js";

test("only the list and auto-detect options require Prisma v3.0", () => {
  const multi = LANGUAGE_OPTIONS.filter((o) => o.needsV3).map((o) => o.value);
  assert.deepEqual(multi, ["hi-IN,en-IN", "indic-auto"]);
  assert.ok(LANGUAGE_OPTIONS.some((o) => o.value === "hi-IN" && !o.needsV3));
});

test("summary states the settings and reports detection only when Gnani returned it", () => {
  const text = sttSummaryText({ model: "prisma-v3.0", format: "codemix", language_code: "indic-auto", detected_language_code: null, truncated: false });
  assert.match(text, /Model prisma-v3.0/);
  assert.match(text, /format codemix/);
  assert.doesNotMatch(text, /detected language/);
});

test("summary shows Gnani's detected language and truncation when present", () => {
  const text = sttSummaryText({ model: "prisma-v3.0", format: "codemix", language_code: "indic-auto", detected_language_code: "hi-IN", truncated: true });
  assert.match(text, /Gnani reported detected language hi-IN/);
  assert.match(text, /cut short/);
});

test("summary is empty without a speech result", () => {
  assert.equal(sttSummaryText(null), "");
});
