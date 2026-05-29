import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpDown, Filter } from 'lucide-react';
import { fetchDealers } from '../api/client';
import RiskBadge from '../components/RiskBadge';

const DISTRICTS = ['','Pune','Nashik','Nagpur','Aurangabad','Amravati',
                   'Solapur','Kolhapur','Jalgaon','Akola','Latur'];

export default function DealerTable() {
  const [dealers,  setDealers]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [district, setDistrict] = useState('');
  const [risk,     setRisk]     = useState('');
  const [sortBy,   setSortBy]   = useState('avg_fraud_prob');
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    fetchDealers({ district: district || undefined, risk_level: risk || undefined,
                   sort_by: sortBy, limit: 300 })
      .then(r => setDealers(r.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [district, risk, sortBy]);

  const fmt = (n) => n >= 1e5 ? `₹${(n/1e5).toFixed(1)}L` : `₹${(n||0).toFixed(0)}`;

  return (
    <div>
      <div className="section-header">
        <div>
          <div className="section-title">Dealer Risk Analysis</div>
          <div className="section-sub">Click any dealer to open full investigation profile</div>
        </div>

        {/* Filters */}
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <Filter size={15} style={{ color:'var(--text-muted)' }} />
          <select id="filter-district" className="input" value={district}
            onChange={e => setDistrict(e.target.value)} style={{ width:150 }}>
            {DISTRICTS.map(d => <option key={d} value={d}>{d || 'All Districts'}</option>)}
          </select>
          <select id="filter-risk" className="input" value={risk}
            onChange={e => setRisk(e.target.value)} style={{ width:140 }}>
            <option value="">All Risk Levels</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
          <select id="sort-by" className="input" value={sortBy}
            onChange={e => setSortBy(e.target.value)} style={{ width:160 }}>
            <option value="avg_fraud_prob">Sort: Fraud Prob</option>
            <option value="total_subsidy">Sort: Total Subsidy</option>
            <option value="farmer_count">Sort: Farmers</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading-wrap"><div className="spinner" /><span>Loading dealers...</span></div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Dealer ID</th>
                <th>Name</th>
                <th>District</th>
                <th>Farmers Served</th>
                <th>Transactions</th>
                <th>Total Subsidy</th>
                <th>ML Fraud Prob</th>
                <th>Rule Score</th>
                <th>Risk Level</th>
              </tr>
            </thead>
            <tbody>
              {dealers.map(d => (
                <tr key={d.dealer_id} style={{ cursor:'pointer' }}
                  onClick={() => navigate(`/dealers/${d.dealer_id}`)}>
                  <td className="primary">{d.dealer_id}</td>
                  <td className="primary">{d.dealer_name}</td>
                  <td>{d.district}</td>
                  <td>{d.farmer_count ?? '—'}</td>
                  <td>{d.total_transactions ?? '—'}</td>
                  <td>{fmt(d.total_subsidy)}</td>
                  <td>
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <div className="risk-bar" style={{ width:60 }}>
                        <div className="risk-bar-fill" style={{
                          width: `${((d.avg_fraud_prob||0)*100).toFixed(0)}%`,
                          background: (d.avg_fraud_prob||0)>=0.6?'var(--red)':(d.avg_fraud_prob||0)>=0.35?'var(--yellow)':'var(--green)'
                        }} />
                      </div>
                      <span style={{ fontSize:'0.8rem', color:'var(--text-secondary)' }}>
                        {d.avg_fraud_prob != null ? `${(d.avg_fraud_prob*100).toFixed(1)}%` : '—'}
                      </span>
                    </div>
                  </td>
                  <td style={{ color:'var(--text-secondary)' }}>
                    {d.rule_score != null ? `${d.rule_score}` : '—'}
                  </td>
                  <td><RiskBadge level={d.risk_level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {dealers.length === 0 && (
            <div className="empty-state"><h3>No dealers found</h3><p>Try adjusting your filters.</p></div>
          )}
        </div>
      )}
    </div>
  );
}
