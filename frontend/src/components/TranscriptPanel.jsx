export default function TranscriptPanel({ transcript, flagged, meta }) {
  if (!transcript || !transcript.trim()) {
    return (
      <section className="card">
        <h2>Transcript</h2>
        <p className="muted">No transcript yet. Record, upload, or paste a transcript.</p>
      </section>
    );
  }
  // Line numbers match the backend's numbering, which counts blank lines too.
  const rows = transcript
    .split(/\r?\n/)
    .map((text, index) => ({ number: index + 1, text }))
    .filter((row) => row.text.trim());
  return (
    <section className="card">
      <h2>Transcript</h2>
      <ol className="transcript">
        {rows.map((row) => (
          <li key={row.number} className={flagged.has(row.number) ? "flagged" : ""}>
            <span className="line-no">{row.number}</span>
            <span>{row.text}</span>
          </li>
        ))}
      </ol>
      <p className="muted small">Highlighted lines contributed to an alert.</p>
      {meta && <p className="muted small">{meta}</p>}
    </section>
  );
}
