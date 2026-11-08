import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { analyzeAudio, analyzeText, errorMessageFromDetail, fetchHealth } from "./api.js";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function mockFetch(handler) {
  globalThis.fetch = async (url, options) => handler(url, options);
}

function json(status, body) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

test("health check calls the backend route and returns its body", async () => {
  mockFetch((url) => {
    assert.equal(url, "/api/health");
    return json(200, { status: "ok", gnani_configured: false });
  });
  const body = await fetchHealth();
  assert.equal(body.gnani_configured, false);
});

test("text analysis sends the transcript as JSON", async () => {
  let sent;
  mockFetch((url, options) => {
    sent = JSON.parse(options.body);
    assert.equal(options.method, "POST");
    return json(200, { risk_level: "LOW" });
  });
  await analyzeText("Caller: hello");
  assert.deepEqual(sent, { transcript: "Caller: hello" });
});

test("validation errors show the backend message", async () => {
  mockFetch(() => json(422, { detail: [{ msg: "String should have at least 1 character" }] }));
  await assert.rejects(() => analyzeText(""), /String should have at least 1 character/);
});

test("plain string details are shown as-is", async () => {
  mockFetch(() => json(503, { detail: "GNANI_API_KEY is missing." }));
  await assert.rejects(() => analyzeAudio(new Blob(["x"]), "call.webm"), /GNANI_API_KEY is missing/);
});

test("network failure gives a friendly message", async () => {
  mockFetch(() => {
    throw new TypeError("fetch failed");
  });
  await assert.rejects(() => fetchHealth(), /Cannot reach the Suraksha Live backend/);
});

test("audio upload sends the file and language as form data", async () => {
  let form;
  mockFetch((url, options) => {
    form = options.body;
    return json(200, { transcript: "" });
  });
  await analyzeAudio(new Blob(["RIFF"]), "call.webm", "hi-IN");
  assert.ok(form instanceof FormData);
  assert.equal(form.get("file").name, "call.webm");
  assert.equal(form.get("language_code"), "hi-IN");
});

test("unknown error shapes fall back to the HTTP status", () => {
  assert.equal(errorMessageFromDetail(undefined, 500), "Request failed (HTTP 500).");
});
