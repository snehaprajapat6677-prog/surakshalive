export const RISK_LABELS = { LOW: "Low risk", MEDIUM: "Medium risk", HIGH: "High risk" };

const ACRONYMS = new Set(["OTP", "UPI", "KYC", "PIN", "CVV", "ID"]);

// needsV3: true when the option only works with Prisma v3.0 (a language list or auto-detect).
export const LANGUAGE_OPTIONS = [
  { value: "hi-IN,en-IN", label: "Hinglish: Hindi and English", needsV3: true },
  { value: "indic-auto", label: "Auto-detect language", needsV3: true },
  { value: "hi-IN", label: "Hindi (hi-IN)", needsV3: false },
  { value: "en-IN", label: "English (en-IN)", needsV3: false },
];

export function riskTone(level) {
  return { LOW: "low", MEDIUM: "medium", HIGH: "high" }[level] ?? "unknown";
}

export function ruleTitle(ruleId) {
  const words = String(ruleId)
    .split("_")
    .map((word) => (ACRONYMS.has(word) ? word : word.toLowerCase()));
  const text = words.join(" ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function scoreSummary(analysis) {
  const { medium_at: medium, high_at: high } = analysis.thresholds;
  return `${analysis.score} points. MEDIUM from ${medium} points, HIGH from ${high}, or any critical indicator.`;
}

export function modeLabel(mode) {
  return mode === "batch"
    ? "Batch mode: audio is analyzed after you stop recording. This is not real-time streaming."
    : "Unknown mode";
}

export function flaggedLineNumbers(analysis) {
  const lines = new Set();
  if (!analysis) return lines;
  for (const indicator of analysis.indicators) {
    for (const item of indicator.evidence) lines.add(item.line);
  }
  return lines;
}

// Describes the Gnani settings that produced a transcript. Detection appears only when Gnani returned it.
export function sttSummaryText(stt) {
  if (!stt) return "";
  const parts = [`Model ${stt.model}`, `format ${stt.format}`, `language setting ${stt.language_code}`];
  if (stt.detected_language_code) parts.push(`Gnani reported detected language ${stt.detected_language_code}`);
  if (stt.truncated) parts.push("the transcript was cut short by Gnani; retry with a shorter clip");
  return parts.join(" · ");
}
