import React from 'react';

const COLORS = {
  High:    { cls: 'badge-high',   dot: '#ef4444' },
  Medium:  { cls: 'badge-medium', dot: '#eab308' },
  Low:     { cls: 'badge-low',    dot: '#22c55e' },
  Unknown: { cls: 'badge-pending',dot: '#9ca3af' },
  Pending:        { cls: 'badge-pending',      dot: '#9ca3af' },
  'Under Review': { cls: 'badge-under-review', dot: '#4f8ef7' },
  'Confirmed Fraud':{ cls: 'badge-confirmed',  dot: '#ef4444' },
  Cleared:        { cls: 'badge-cleared',      dot: '#22c55e' },
};

export default function RiskBadge({ level, showDot = true }) {
  const cfg = COLORS[level] || COLORS.Unknown;
  return (
    <span className={`badge ${cfg.cls}`}>
      {showDot && (
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: cfg.dot, display: 'inline-block', flexShrink: 0
        }} />
      )}
      {level || 'Unknown'}
    </span>
  );
}
