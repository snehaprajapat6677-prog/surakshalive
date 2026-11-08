import { useEffect, useState } from "react";
import Recorder from "./components/Recorder.jsx";
import RiskDashboard from "./components/RiskDashboard.jsx";
import TranscriptPanel from "./components/TranscriptPanel.jsx";
import { analyzeAudio, analyzeText, fetchHealth } from "./services/api.js";
import {
  LANGUAGE_OPTIONS,
  RISK_LABELS,
  flaggedLineNumbers,
  modeLabel,
  riskTone,
  sttSummaryText,
} from "./services/format.js";

const V3_MODEL = "prisma-v3.0";

const DEMO_TRANSCRIPT = `Caller: Hello, this is Inspector Sharma from the Cyber Crime Police Station.
Customer: Police? Why are you calling me?
Caller: Your Aadhaar was used in a money laundering case. You are under investigation.
Caller: If you do not cooperate, a non-bailable arrest warrant will be issued today.
Caller: Do not tell anyone about this call and do not disconnect the line.
Caller: To clear the case, you must pay a security deposit of fifty thousand rupees to our verification account.`;

function StatusChip({ label, value, tone }) {
  return (
    <div className={`chip chip-${tone}`}>
      <span className="chip-label">{label}</span>
      <span className="chip-value">{value}</span>
    </div>
  );
}

function HistoryPanel({ history }) {
  return (
    <section className="card">
      <h2>Session history</h2>
      {history.length === 0 ? (
        <p className="muted">Results from this browser session only. Nothing is saved to disk.</p>
      ) : (
        <ol className="history">
          {history.map((entry) => (
            <li key={entry.id}>
              <span className={`pill pill-${riskTone(entry.risk)}`}>{RISK_LABELS[entry.risk]}</span>
              <span>{entry.category}</span>
              <span className="muted small"> {entry.time}</span>
              <div className="muted small">{entry.preview}</div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [sttInfo, setSttInfo] = useState(null);
  const [pasted, setPasted] = useState("");
  const [language, setLanguage] = useState("hi-IN,en-IN");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealth(h);
        if (h.stt_model !== V3_MODEL) setLanguage("hi-IN");
      })
      .catch(() => setHealthError(true));
  }, []);

  const gnaniReady = Boolean(health?.gnani_configured);
  const v3Ready = health?.stt_model === V3_MODEL;

  function showResult(text, result, stt) {
    setTranscript(text);
    setAnalysis(result);
    setSttInfo(stt ?? null);
    setHistory((previous) =>
      [
        {
          id: Date.now(),
          time: new Date().toLocaleTimeString(),
          risk: result.risk_level,
          category: result.category_label ?? "No category",
          preview: text.slice(0, 80),
        },
        ...previous,
      ].slice(0, 10)
    );
  }

  async function runAudio(blob, filename) {
    setBusy(true);
    setError("");
    try {
      const data = await analyzeAudio(blob, filename, language);
      showResult(data.transcript, data.analysis, data.stt);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runText() {
    setBusy(true);
    setError("");
    try {
      const result = await analyzeText(pasted);
      showResult(pasted, result, null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const backendValue = healthError ? "Offline" : health ? "Online" : "Checking";
  const backendTone = healthError ? "high" : health ? "low" : "unknown";
  const gnaniValue = !health ? "Checking" : gnaniReady ? "Configured" : "Key missing";
  const gnaniTone = !health ? "unknown" : gnaniReady ? "low" : "medium";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">S</span>
          <div>
            <h1>Suraksha Live</h1>
            <p className="muted">Detect the threat before you trust the voice.</p>
          </div>
        </div>
        <div className="chips">
          <StatusChip label="Backend" value={backendValue} tone={backendTone} />
          <StatusChip label="Gnani STT" value={gnaniValue} tone={gnaniTone} />
          <StatusChip label="Model" value={health?.stt_model ?? "…"} tone="unknown" />
        </div>
      </header>

      {healthError && (
        <p className="notice error">
          The backend is not reachable. Start it with uvicorn on port 8000, as described in the README.
        </p>
      )}
      {health && !gnaniReady && (
        <p className="notice">
          Gnani key is not set. Add GNANI_API_KEY to backend/.env to enable audio. {modeLabel("batch")}
        </p>
      )}

      <main className="grid">
        <div className="column">
          <section className="card">
            <h2>Language</h2>
            <label className="field">
              <span className="muted small">Language setting sent to Gnani</span>
              <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                {LANGUAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value} disabled={option.needsV3 && !v3Ready}>
                    {option.label}
                    {option.needsV3 && !v3Ready ? " (needs Prisma v3.0)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <p className="muted small">
              Detection appears only when Gnani returns it. The app does not guess the language.
            </p>
          </section>

          <Recorder onAudio={runAudio} disabled={busy || !gnaniReady} />

          <section className="card">
            <h2>Analyze a pasted transcript</h2>
            <p className="muted">Uses no Gnani credits. Useful for testing the rules.</p>
            <textarea
              rows={6}
              value={pasted}
              onChange={(event) => setPasted(event.target.value)}
              placeholder="Caller: ...&#10;Customer: ..."
            />
            <div className="controls">
              <button className="btn primary" onClick={runText} disabled={busy || healthError || !pasted.trim()}>
                Analyze text
              </button>
              <button className="btn ghost" onClick={() => setPasted(DEMO_TRANSCRIPT)}>
                Load demo script
              </button>
            </div>
          </section>

          <TranscriptPanel
            transcript={transcript}
            flagged={flaggedLineNumbers(analysis)}
            meta={sttSummaryText(sttInfo)}
          />
        </div>

        <div className="column">
          {busy && <p className="notice">Analyzing…</p>}
          {error && <p className="notice error">{error}</p>}
          <RiskDashboard analysis={analysis} />
          <HistoryPanel history={history} />
        </div>
      </main>

      <footer className="privacy">
        Privacy: audio is processed in memory and is not stored. Use synthetic or consented audio only.
        Never share OTPs, UPI PINs or passwords. Suraksha Live supports judgment; it does not guarantee
        fraud prevention.
      </footer>
    </div>
  );
}
