import { useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { InsightState } from '../insight';

export function InsightCard({ insight, interactive = false }: { insight: InsightState; interactive?: boolean }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const evidenceId = useId();
  const navigate = useNavigate();
  if (insight.status === 'loading') return <p className="insight-status" role="status">Loading your insight…</p>;
  if (insight.status === 'error' || !insight.item) return <p className="insight-status" role="status">Insight unavailable.</p>;

  return <div className="insight-card">
    <h3>{insight.item.title}</h3>
    <p>{insight.item.summary}</p>
    <ul id={evidenceId} hidden={interactive && !showEvidence}>{insight.item.evidence.map((detail) => <li key={detail}>{detail}</li>)}</ul>
    {interactive && <div className="insight-actions">
      <button type="button" aria-label={showEvidence ? 'Hide supporting signals' : 'Show supporting signals'} aria-expanded={showEvidence} aria-controls={evidenceId} onClick={() => setShowEvidence((visible) => !visible)}>
        {showEvidence ? 'Hide details' : 'Why this?'}
      </button>
      <button type="button" onClick={() => navigate('/timeline')}>Review transactions</button>
    </div>}
    <small>Experimental pattern from demo transactions, not a prediction or financial advice.</small>
  </div>;
}
