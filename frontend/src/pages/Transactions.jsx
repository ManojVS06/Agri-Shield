import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Zap, ChevronDown, ChevronUp } from 'lucide-react';
import { fetchTransactions, fetchSHAP } from '../api/client';
import RiskBadge from '../components/RiskBadge';

// ── SHAP inline panel ────────────────────────────────────────────────────────
function ShapPanel({ txnId, onClose }) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    fetchSHAP(txnId)
      .then(r => setData(r.data))
      .catch(() => setError('SHAP explanation unavailable'))
      .finally(() => setLoading(false));
  }, [txnId]);

  const containerStyle = {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '16px 20px',
    marginTop: 8,
  };

  if (loading) return (
    <div style={containerStyle}>
      <div className="loading-wrap" style={{ padding: 0, gap: 8, fontSize: '0.82rem' }}>
        <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
        <span>Computing SHAP values...</span>
      </div>
    </div>
  );

  if (error || !data?.shap_values?.length) return (
    <div style={{ ...containerStyle, color: 'var(--text-muted)', fontSize: '0.82rem' }}>
      {error || 'No SHAP data available for this transaction.'}
    </div>
  );

  const chartData = data.shap_values.map(s => ({
    feature: s.feature.replace(/_/g, ' '),
    impact:  parseFloat(s.shap_value.toFixed(4)),
    value:   s.value,
  }));

  return (
    <div style={containerStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Zap size={14} style={{ color: 'var(--accent)' }} />
          <span style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
            SHAP Feature Contributions
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            (Fraud prob: {data.fraud_probability != null ? `${(data.fraud_probability * 100).toFixed(1)}%` : '—'})
          </span>
        </div>
        <button onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '1rem' }}>
          ✕
        </button>
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 24 }}>
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <YAxis dataKey="feature" type="category" width={150}
            tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#1a2235', border: '1px solid #00d4aa44', borderRadius: 8, fontSize: '0.75rem' }}
            formatter={(v, _, props) => [`SHAP: ${v}  (value: ${props.payload.value})`, '']}
          />
          <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
            {chartData.map((d, i) => (
              <Cell key={i} fill={d.impact >= 0 ? '#ef4444' : '#22c55e'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 6 }}>
        🔴 Positive SHAP = pushes toward fraud &nbsp;|&nbsp; 🟢 Negative = pushes toward normal
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function Transactions() {
  const [searchParams] = useSearchParams();
  const dealerId = searchParams.get('dealer_id');

  const [txns,      setTxns]     = useState([]);
  const [loading,   setLoading]  = useState(true);
  const [expanded,  setExpanded] = useState(null);
  const [shapTxn,   setShapTxn]  = useState(null);

  useEffect(() => {
    fetchTransactions({ dealer_id: dealerId || undefined, limit: 300 })
      .then(r => setTxns(r.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [dealerId]);

  const toggleExpand = (txnId) => {
    setExpanded(prev => (prev === txnId ? null : txnId));
    setShapTxn(null);
  };

  const toggleShap = (e, txnId) => {
    e.stopPropagation();
    setShapTxn(prev => (prev === txnId ? null : txnId));
  };

  if (loading) return (
    <div className="loading-wrap"><div className="spinner" /><span>Loading transactions...</span></div>
  );

  return (
    <div>
      <div className="section-header">
        <div>
          <div className="section-title">
            {dealerId ? `Transactions — Dealer ${dealerId}` : 'All Transactions'}
          </div>
          <div className="section-sub">{txns.length} records · Click a row to expand details</div>
        </div>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>TXN ID</th><th>Farmer</th><th>Dealer</th><th>Type</th>
              <th>Amount (₹)</th><th>Actual Price</th><th>Land (ac)</th>
              <th>District</th><th>Fraud Prob</th><th>Fraud Type</th><th>Risk</th><th></th>
            </tr>
          </thead>
          <tbody>
            {txns.map(t => {
              const prob        = t.fraud_probability || 0;
              const isSuspicious = prob > 0.7;
              const isMedium     = prob > 0.35;
              const isExpanded   = expanded === t.txn_id;
              const shapOpen     = shapTxn === t.txn_id;

              return (
                <React.Fragment key={t.txn_id}>
                  <tr
                    onClick={() => toggleExpand(t.txn_id)}
                    style={{
                      cursor: 'pointer',
                      background: isSuspicious ? 'rgba(239,68,68,0.08)' :
                                  isMedium     ? 'rgba(234,179,8,0.05)' : 'transparent',
                      borderLeft: isSuspicious ? '3px solid var(--red)' :
                                  isMedium     ? '3px solid var(--yellow)' : '3px solid transparent',
                    }}
                  >
                    <td className="primary">{t.txn_id}</td>
                    <td>{t.farmer_id}</td>
                    <td>{t.dealer_id}</td>
                    <td>{t.subsidy_type}</td>
                    <td>{(t.subsidy_amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                    <td style={{ color: (t.actual_price || 0) < 10 ? '#ef4444' : 'var(--text-secondary)' }}>
                      {(t.actual_price || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                    <td style={{ color: (t.land_size_acres || 0) < 0.1 ? '#ef4444' : 'var(--text-secondary)' }}>
                      {t.land_size_acres}
                    </td>
                    <td>{t.district}</td>
                    <td style={{ color: prob > 0.6 ? '#ef4444' : prob > 0.35 ? '#eab308' : '#22c55e', fontWeight: 600 }}>
                      {prob ? `${(prob * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {t.fraud_type !== 'None' ? t.fraud_type : '—'}
                    </td>
                    <td><RiskBadge level={t.risk_level} /></td>
                    <td onClick={e => e.stopPropagation()}>
                      {isExpanded && (
                        <button
                          title="Explain with SHAP"
                          onClick={e => toggleShap(e, t.txn_id)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 4,
                            background: shapOpen ? 'var(--accent)' : 'var(--bg-secondary)',
                            color: shapOpen ? '#000' : 'var(--accent)',
                            border: `1px solid var(--accent)`,
                            borderRadius: 6, padding: '3px 8px',
                            fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600,
                            transition: 'all 0.2s',
                          }}
                        >
                          <Zap size={11} /> SHAP
                          {shapOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                        </button>
                      )}
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr>
                      <td colSpan={12} style={{ padding: '0 16px 16px', background: 'var(--bg-secondary)' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, paddingTop: 12 }}>
                          {[
                            ['Season',           t.season],
                            ['Crop Type',        t.crop_type],
                            ['Payment Mode',     t.payment_mode],
                            ['Transaction Hour', `${t.transaction_hour}:00`],
                            ['Distance (km)',    t.distance_farmer_dealer],
                            ['Subsidy/Acre',     t.land_size_acres > 0.05
                              ? `₹${((t.subsidy_amount || 0) / t.land_size_acres).toFixed(0)}`
                              : 'N/A (zero land)'],
                            ['Fraud Reason',     t.fraud_reason || 'Normal'],
                            ['Rule Score',       t.rule_score ?? '—'],
                          ].map(([k, v]) => (
                            <div key={k}>
                              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{k}</div>
                              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 500 }}>{v ?? '—'}</div>
                            </div>
                          ))}
                        </div>

                        {shapOpen && <ShapPanel txnId={t.txn_id} onClose={() => setShapTxn(null)} />}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>

        {txns.length === 0 && (
          <div className="empty-state"><h3>No transactions found</h3></div>
        )}
      </div>
    </div>
  );
}
