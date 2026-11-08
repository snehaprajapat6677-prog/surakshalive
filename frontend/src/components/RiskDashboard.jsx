import { RISK_LABELS, riskTone, ruleTitle, scoreSummary } from "../services/format.js";

export default function RiskDashboard({ analysis }) {
  if (!analysis) {
    return (
      <section className="card">
        <h2>Risk dashboard</h2>
        <p className="muted">Results appear here with the transcript lines that triggered each alert.</p>
      </section>
    );
  }
  const tone = riskTone(analysis.risk_level);
  return (
    <section className="card">
      <h2>Risk dashboard</h2>
      <div className={`risk risk-${tone}`}>
        <span className="risk-label">{RISK_LABELS[analysis.risk_level] ?? analysis.risk_level}</span>
        <span className="small">{scoreSummary(analysis)}</span>
      </div>
      <p>
        <strong>Detected category:</strong> {analysis.category_label ?? "None"}
      </p>
      <p>
        <strong>Recommended action:</strong> {analysis.recommended_action}
      </p>
      <h3>Evidence</h3>
      {analysis.indicators.length === 0 ? (
        <p className="muted">No fraud indicators matched.</p>
      ) : (
        analysis.indicators.map((indicator) => (
          <article key={indicator.rule_id} className={`evidence ${indicator.critical ? "critical" : ""}`}>
            <header>
              <strong>{ruleTitle(indicator.rule_id)}</strong>
              <span className="small">
                +{indicator.weight}
                {indicator.critical ? " · critical" : ""}
              </span>
            </header>
            <p>{indicator.explanation}</p>
            <ul>
              {indicator.evidence.map((item, index) => (
                <li key={index}>
                  <span className="line-no">Line {item.line}</span> “{item.text}”
                </li>
              ))}
            </ul>
          </article>
        ))
      )}
      <div className="muted small">
        <p>{analysis.disclaimer}</p>
        <p>{analysis.safety_tips}</p>
      </div>
    </section>
  );
}
