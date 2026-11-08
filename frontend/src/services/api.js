const BASE_URL = "/api";
const UNREACHABLE = "Cannot reach the Suraksha Live backend. Start it on port 8000 (see README).";

export function errorMessageFromDetail(detail, status) {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item?.msg ?? "Invalid request.").join(" ");
  }
  return `Request failed (HTTP ${status}).`;
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, options);
  } catch {
    throw new Error(UNREACHABLE);
  }
  let body = {};
  try {
    body = await response.json();
  } catch {
    body = {};
  }
  if (!response.ok) {
    throw new Error(errorMessageFromDetail(body?.detail, response.status));
  }
  return body;
}

export function fetchHealth() {
  return request("/health");
}

export function analyzeText(transcript) {
  return request("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript }),
  });
}

// languageCode is optional; when omitted the backend applies the default for its configured model.
export function analyzeAudio(blob, filename, languageCode) {
  const form = new FormData();
  form.append("file", blob, filename);
  if (languageCode) form.append("language_code", languageCode);
  return request("/analyze-audio", { method: "POST", body: form });
}
