import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  RadialBarChart, RadialBar, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { ArrowLeft, Lightbulb, AlertCircle, TrendingUp, Zap, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { fetchDealer, fetchDealerStats, fetchTransactions, fetchDealerMapData, fetchSHAP } from '../api/client';
import RiskBadge from '../components/RiskBadge';
import AiExplanationPanel from '../components/AiExplanationPanel';


// Import Leaflet styles and components
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

function StatRow({ label, dealer, district, unit = '' }) {
  const ratio = district ? dealer / district : 1;
  const color = ratio > 1.8 ? '#ef4444' : ratio > 1.2 ? '#eab308' : '#22c55e';
  return (
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
      padding:'10px 0', borderBottom:'1px solid var(--border)' }}>
      <span style={{ color:'var(--text-secondary)', fontSize:'0.85rem' }}>{label}</span>
      <div style={{ textAlign:'right' }}>
        <span style={{ fontWeight:600, color:'var(--text-primary)' }}>
          {unit}{typeof dealer === 'number' ? dealer.toLocaleString('en-IN', {maximumFractionDigits:1}) : dealer}
        </span>
        {district != null && (
          <div style={{ fontSize:'0.72rem', color }}>
            {ratio.toFixed(1)}× district avg ({unit}{typeof district === 'number'
              ? district.toLocaleString('en-IN',{maximumFractionDigits:1}) : district})
          </div>
        )}
      </div>
    </div>
  );
}

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

// ── GIS Map component ─────────────────────────────────────────────────────────
function DealerFarmerMap({ mapData }) {
  if (!mapData || mapData.lat == null || mapData.long == null) {
    return (
      <div style={{ height: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        No coordinates available for mapping.
      </div>
    );
  }

  const dealerPos = [mapData.lat, mapData.long];

  return (
    <div style={{ height: 380, border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden', position: 'relative' }}>
      <MapContainer center={dealerPos} zoom={11} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Dealer Marker (Blue Circle) */}
        <CircleMarker
          center={dealerPos}
          radius={12}
          fillColor="#3b82f6"
          color="#1e3a8a"
          weight={2.5}
          fillOpacity={0.85}
        >
          <Popup>
            <div style={{ fontSize: '0.82rem', color: '#1e293b' }}>
              <strong>Dealer: {mapData.dealer_name}</strong><br />
              ID: {mapData.dealer_id}<br />
              Location: {mapData.lat.toFixed(4)}, {mapData.long.toFixed(4)}
            </div>
          </Popup>
        </CircleMarker>

        {/* Farmer Markers & Connection Lines */}
        {mapData.farmers.map(f => {
          if (f.lat == null || f.long == null) return null;
          const farmerPos = [f.lat, f.long];
          const color = f.risk_level === 'High' ? '#ef4444' : f.risk_level === 'Medium' ? '#eab308' : '#22c55e';

          return (
            <React.Fragment key={f.farmer_id}>
              {/* Connection Line */}
              <Polyline
                positions={[dealerPos, farmerPos]}
                pathOptions={{
                  color: f.risk_level === 'High' ? '#ef4444' : '#475569',
                  weight: f.risk_level === 'High' ? 1.5 : 0.8,
                  dashArray: f.risk_level === 'High' ? '4, 4' : '6, 6',
                  opacity: f.risk_level === 'High' ? 0.8 : 0.4
                }}
              />

              {/* Farmer Marker */}
              <CircleMarker
                center={farmerPos}
                radius={7}
                fillColor={color}
                color={f.risk_level === 'High' ? '#991b1b' : '#334155'}
                weight={1.5}
                fillOpacity={0.75}
              >
                <Popup>
                  <div style={{ fontSize: '0.8rem', color: '#1e293b' }}>
                    <strong>Farmer: {f.name}</strong><br />
                    ID: {f.farmer_id}<br />
                    Location: {f.lat.toFixed(4)}, {f.long.toFixed(4)}<br />
                    Transactions with Dealer: {f.txn_count}<br />
                    Max Fraud Prob: {(f.max_fraud_prob * 100).toFixed(1)}%<br />
                    Risk Level: <strong style={{ color }}>{f.risk_level}</strong>
                  </div>
                </Popup>
              </CircleMarker>
            </React.Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}

// ── Main Page Component ─────────────────────────────────────────────────────────
export default function DealerProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [dealer, setDealer] = useState(null);
  const [stats,  setStats]  = useState(null);
  const [txns,   setTxns]   = useState([]);
  const [mapData, setMapData] = useState(null);
  const [loading,setLoading]= useState(true);

  const [expandedTxn, setExpandedTxn] = useState(null);
  const [shapTxn, setShapTxn] = useState(null);
  const [hiddenExplanations, setHiddenExplanations] = useState({});


  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchDealer(id),
      fetchDealerStats(id),
      fetchTransactions({ dealer_id: id, limit: 10 }),
      fetchDealerMapData(id)
    ]).then(([d, s, t, m]) => {
      setDealer(d.data);
      setStats(s.data);
      setTxns(t.data || []);
      setMapData(m.data);
    }).catch(console.error)
    .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading-wrap"><div className="spinner" /><span>Loading dealer profile...</span></div>;
  if (!dealer) return <div className="empty-state"><h3>Dealer not found</h3></div>;

  const prob = dealer.avg_fraud_prob ?? 0;
  const probPct = (prob * 100).toFixed(1);
  const riskColor = prob >= 0.6 ? '#ef4444' : prob >= 0.35 ? '#eab308' : '#22c55e';

  return (
    <div>
      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:24 }}>
        <button onClick={() => navigate(-1)}
          style={{ background:'var(--bg-card)', border:'1px solid var(--border)', borderRadius:8,
            padding:'7px 12px', color:'var(--text-secondary)', cursor:'pointer',
            display:'flex', alignItems:'center', gap:6, fontSize:'0.85rem' }}>
          <ArrowLeft size={15} /> Back
        </button>
        <div>
          <div className="section-title">{dealer.dealer_name}</div>
          <div className="section-sub">ID: {id} · {dealer.district} · <RiskBadge level={dealer.risk_level} /></div>
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom:24 }}>
        {/* Gauge */}
        <div className="card" style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:12 }}>
          <div style={{ fontWeight:600, color:'var(--text-secondary)', fontSize:'0.85rem' }}>ML Fraud Probability</div>
          <div style={{ position:'relative', width:160, height:160 }}>
            <svg viewBox="0 0 160 160" style={{ position:'absolute', top:0, left:0 }}>
              <circle cx="80" cy="80" r="60" fill="none" stroke="var(--bg-secondary)" strokeWidth="14" />
              <circle cx="80" cy="80" r="60" fill="none" stroke={riskColor} strokeWidth="14"
                strokeDasharray={`${prob * 376.99} 376.99`}
                strokeLinecap="round"
                style={{ transform:'rotate(-90deg)', transformOrigin:'80px 80px', transition:'stroke-dasharray 0.8s ease' }}
              />
            </svg>
            <div style={{ position:'absolute', inset:0, display:'flex', flexDirection:'column',
              alignItems:'center', justifyContent:'center' }}>
              <div style={{ fontSize:'1.8rem', fontWeight:800, color: riskColor }}>{probPct}%</div>
              <div style={{ fontSize:'0.7rem', color:'var(--text-muted)' }}>fraud probability</div>
            </div>
          </div>
          <RiskBadge level={dealer.risk_level} />
        </div>

        {/* Rule score */}
        <div className="card">
          <div style={{ fontWeight:600, color:'var(--text-secondary)', fontSize:'0.85rem', marginBottom:16 }}>Rule-Based Score</div>
          <div style={{ fontSize:'3rem', fontWeight:800, color: (dealer.rule_score||0)>60?'#ef4444':(dealer.rule_score||0)>30?'#eab308':'#22c55e' }}>
            {dealer.rule_score?.toFixed(0) ?? '—'}<span style={{ fontSize:'1.2rem', color:'var(--text-muted)' }}>/100</span>
          </div>
          <div style={{ marginTop:12 }}>
            <div className="risk-bar" style={{ height:10 }}>
              <div className="risk-bar-fill" style={{
                width: `${dealer.rule_score || 0}%`,
                background: (dealer.rule_score||0)>60?'var(--red)':(dealer.rule_score||0)>30?'var(--yellow)':'var(--green)'
              }} />
            </div>
          </div>
          <div style={{ marginTop:8, fontSize:'0.75rem', color:'var(--text-muted)' }}>
            Based on 6 anomaly rules
          </div>
        </div>

        {/* Quick stats */}
        <div className="card">
          <div style={{ fontWeight:600, color:'var(--text-secondary)', fontSize:'0.85rem', marginBottom:16 }}>Quick Stats</div>
          {[
            ['Farmers Served',   dealer.farmer_count],
            ['Total Transactions',dealer.total_transactions],
            ['Total Subsidy',    `₹${(dealer.total_subsidy||0).toLocaleString('en-IN',{maximumFractionDigits:0})}`],
            ['Shop Size',        dealer.shop_size],
            ['Years Active',     `${dealer.years_active} years`],
          ].map(([k,v]) => (
            <div key={k} style={{ display:'flex', justifyContent:'space-between', padding:'7px 0',
              borderBottom:'1px solid var(--border)', fontSize:'0.85rem' }}>
              <span style={{ color:'var(--text-muted)' }}>{k}</span>
              <span style={{ color:'var(--text-primary)', fontWeight:600 }}>{v ?? '—'}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Comparisons + Insights row */}
      <div className="grid-2" style={{ marginBottom:24 }}>
        {/* vs district */}
        {stats && (
          <div className="card">
            <div className="chart-title">Dealer vs District Average</div>
            <StatRow label="Transactions" dealer={stats.dealer_txn_count} district={stats.district_avg_txns} />
            <StatRow label="Avg Subsidy Amount" dealer={stats.dealer_avg_subsidy} district={stats.district_avg_subsidy} unit="₹" />
            <StatRow label="Unique Farmers" dealer={stats.dealer_farmer_count} district={stats.district_avg_farmers} />
            <StatRow label="Fraud Rate" dealer={`${stats.dealer_fraud_rate}%`} district={null} />
          </div>
        )}

        {/* AI Insights */}
        <div className="card">
          <div className="chart-title" style={{ display:'flex', alignItems:'center', gap:8 }}>
            <Lightbulb size={16} style={{ color:'var(--accent)' }} />
            Dynamic Insights
          </div>
          <div className="insight-list">
            {dealer.insights?.length ? dealer.insights.map((ins, i) => (
              <div key={i} className="insight-item">
                <AlertCircle size={14} style={{ flexShrink:0, marginTop:1 }} />
                {ins}
              </div>
            )) : (
              <div style={{ color:'var(--text-muted)', fontSize:'0.85rem' }}>No significant anomalies detected.</div>
            )}
          </div>
        </div>
      </div>

      {/* GIS Network Map */}
      <div className="card" style={{ marginBottom:24 }}>
        <div className="chart-title" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <TrendingUp size={16} style={{ color: 'var(--accent)' }} />
          Geographic Network of Farmers Served
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>
            (Connects dealer marker with farmer coordinates dynamically colored by risk)
          </span>
        </div>
        <DealerFarmerMap mapData={mapData} />
      </div>

      {/* Recent transactions */}
      <div className="card">
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
          <div className="chart-title">Recent Transactions</div>
          <Link to={`/transactions?dealer_id=${id}`}
            style={{ fontSize:'0.82rem', color:'var(--accent)' }}>View all →</Link>
        </div>
        <div className="table-wrapper" style={{ border:'none', borderRadius:0 }}>
          <table>
            <thead>
              <tr>
                <th>TXN ID</th><th>Farmer</th><th>Subsidy Type</th>
                <th>Amount</th><th>Land (acres)</th><th>Fraud Prob</th><th>Risk</th><th></th>
              </tr>
            </thead>
            <tbody>
              {txns.map(t => {
                const prob = t.fraud_probability || 0;
                const isSuspicious = prob > 0.7;
                const isMedium = prob > 0.35;
                const isExpanded = expandedTxn === t.txn_id;
                const shapOpen = shapTxn === t.txn_id;

                const toggleExpand = (txnId) => {
                  setExpandedTxn(prev => {
                    const nextVal = prev === txnId ? null : txnId;
                    if (nextVal !== null) {
                      setHiddenExplanations(prevHidden => ({ ...prevHidden, [txnId]: false }));
                    }
                    return nextVal;
                  });
                  setShapTxn(null);
                };

                const toggleShap = (e, txnId) => {
                  e.stopPropagation();
                  setShapTxn(prev => (prev === txnId ? null : shapTxn === txnId ? null : txnId));
                };

                return (
                  <React.Fragment key={t.txn_id}>
                    <tr
                      onClick={() => toggleExpand(t.txn_id)}
                      style={{
                        cursor: 'pointer',
                        background: isSuspicious ? 'rgba(239,68,68,0.07)' :
                                    isMedium     ? 'rgba(234,179,8,0.05)' : 'transparent',
                        borderLeft: isSuspicious ? '3px solid var(--red)' :
                                    isMedium     ? '3px solid var(--yellow)' : '3px solid transparent',
                      }}
                    >
                      <td className="primary">{t.txn_id}</td>
                      <td>{t.farmer_id}</td>
                      <td>{t.subsidy_type}</td>
                      <td>₹{(t.subsidy_amount||0).toLocaleString('en-IN',{maximumFractionDigits:0})}</td>
                      <td style={{ color: (t.land_size_acres || 0) < 0.1 ? '#ef4444' : 'var(--text-secondary)' }}>
                        {t.land_size_acres}
                      </td>
                      <td style={{ color: prob > 0.6 ? '#ef4444' : prob > 0.35 ? '#eab308' : '#22c55e', fontWeight: 600 }}>
                        {prob ? `${(prob * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td><RiskBadge level={t.risk_level} /></td>
                      <td onClick={e => e.stopPropagation()}>
                        {isExpanded && (
                          <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                            <button
                              title="AI Automated Reasoning"
                              onClick={e => {
                                e.stopPropagation();
                                setHiddenExplanations(prev => ({ ...prev, [t.txn_id]: !prev[t.txn_id] }));
                              }}
                              style={{
                                display: 'flex', alignItems: 'center', gap: 4,
                                background: !hiddenExplanations[t.txn_id] ? 'var(--accent)' : 'var(--bg-secondary)',
                                color: !hiddenExplanations[t.txn_id] ? '#000' : 'var(--accent)',
                                border: '1px solid var(--accent)',
                                borderRadius: 6, padding: '3px 8px',
                                fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600,
                                transition: 'all 0.2s',
                              }}
                            >
                              <Sparkles size={11} /> AI Explain
                            </button>

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
                          </div>
                        )}
                      </td>
                    </tr>

                    {isExpanded && (
                      <tr>
                        <td colSpan={8} style={{ padding: '0 16px 16px', background: 'var(--bg-secondary)' }}>
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

                          {!hiddenExplanations[t.txn_id] && (
                            <AiExplanationPanel 
                              txnId={t.txn_id} 
                              onClose={() => setHiddenExplanations(prev => ({ ...prev, [t.txn_id]: true }))} 
                            />
                          )}

                          {shapOpen && <ShapPanel txnId={t.txn_id} onClose={() => setShapTxn(null)} />}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
