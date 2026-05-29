import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  RadialBarChart, RadialBar, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';
import { ArrowLeft, Lightbulb, AlertCircle, TrendingUp } from 'lucide-react';
import { fetchDealer, fetchDealerStats, fetchTransactions } from '../api/client';
import RiskBadge from '../components/RiskBadge';

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

export default function DealerProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [dealer, setDealer] = useState(null);
  const [stats,  setStats]  = useState(null);
  const [txns,   setTxns]   = useState([]);
  const [loading,setLoading]= useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchDealer(id),
      fetchDealerStats(id),
      fetchTransactions({ dealer_id: id, limit: 10 }),
    ]).then(([d, s, t]) => {
      setDealer(d.data);
      setStats(s.data);
      setTxns(t.data || []);
    }).catch(console.error)
    .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading-wrap"><div className="spinner" /><span>Loading dealer profile...</span></div>;
  if (!dealer) return <div className="empty-state"><h3>Dealer not found</h3></div>;

  const prob = dealer.avg_fraud_prob ?? 0;
  const probPct = (prob * 100).toFixed(1);
  const riskColor = prob >= 0.6 ? '#ef4444' : prob >= 0.35 ? '#eab308' : '#22c55e';

  const gaugeData = [{ name: 'Fraud Prob', value: parseFloat(probPct), fill: riskColor }];

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
                <th>Amount</th><th>Land (acres)</th><th>Fraud Prob</th><th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {txns.map(t => (
                <tr key={t.txn_id} style={{
                  background: (t.fraud_probability||0)>0.7 ? 'rgba(239,68,68,0.07)' :
                              (t.fraud_probability||0)>0.35 ? 'rgba(234,179,8,0.05)' : 'transparent'
                }}>
                  <td className="primary">{t.txn_id}</td>
                  <td>{t.farmer_id}</td>
                  <td>{t.subsidy_type}</td>
                  <td>₹{(t.subsidy_amount||0).toLocaleString('en-IN',{maximumFractionDigits:0})}</td>
                  <td>{t.land_size_acres}</td>
                  <td style={{ color:(t.fraud_probability||0)>0.6?'#ef4444':(t.fraud_probability||0)>0.35?'#eab308':'#22c55e', fontWeight:600 }}>
                    {t.fraud_probability != null ? `${(t.fraud_probability*100).toFixed(1)}%` : '—'}
                  </td>
                  <td><RiskBadge level={t.risk_level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
