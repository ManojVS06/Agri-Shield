import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchAlerts, updateInvestigation } from '../api/client';
import RiskBadge from '../components/RiskBadge';
import toast from 'react-hot-toast';

const STATUSES = ['Pending', 'Under Review', 'Confirmed Fraud', 'Cleared'];

// ── Action Modal ──────────────────────────────────────────────────────────────
function ActionModal({ dealer, onClose, onSave }) {
  const [status,     setStatus]     = useState(dealer.investigation_status || 'Pending');
  const [assignedTo, setAssignedTo] = useState('');
  const [notes,      setNotes]      = useState('');
  const [saving,     setSaving]     = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({ dealer_id: dealer.dealer_id, status, assigned_to: assignedTo, notes });
      onClose();
    } finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">
          Update Investigation — {dealer.dealer_name}
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 6, display: 'block' }}>Status</label>
          <select id="modal-status" className="input" value={status} onChange={e => setStatus(e.target.value)}>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 6, display: 'block' }}>Assign To</label>
          <input id="modal-assign" className="input" value={assignedTo} placeholder="Investigator name or email"
            onChange={e => setAssignedTo(e.target.value)} />
        </div>

        <div style={{ marginBottom: 24 }}>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 6, display: 'block' }}>Notes</label>
          <textarea id="modal-notes" className="input" value={notes} placeholder="Add investigation notes..."
            onChange={e => setNotes(e.target.value)}
            style={{ resize: 'vertical', minHeight: 90, fontFamily: 'inherit' }} />
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function Alerts() {
  const [alerts,  setAlerts]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal,   setModal]   = useState(null);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    fetchAlerts()
      .then(r => setAlerts(r.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleSave = async (data) => {
    try {
      // user_id/user_email are null in dev mode — backend handles this gracefully
      await updateInvestigation({
        ...data,
        user_id:    null,
        user_email: 'dev@agrishield.local',
      });
      toast.success('Investigation updated');
      load();
    } catch { toast.error('Failed to save'); }
  };

  if (loading) return <div className="loading-wrap"><div className="spinner" /><span>Loading alerts...</span></div>;

  return (
    <div>
      <div className="section-header">
        <div>
          <div className="section-title">Fraud Alerts</div>
          <div className="section-sub">{alerts.length} high-risk dealers (≥65% avg fraud probability)</div>
        </div>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Dealer</th><th>District</th><th>Farmers</th><th>Transactions</th>
              <th>Avg Fraud Prob</th><th>Risk</th><th>Investigation Status</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(a => (
              <tr key={a.dealer_id} style={{ cursor: 'pointer' }}>
                <td className="primary" onClick={() => navigate(`/dealers/${a.dealer_id}`)}>
                  {a.dealer_name}
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>ID: {a.dealer_id}</div>
                </td>
                <td>{a.district}</td>
                <td>{a.farmer_count}</td>
                <td>{a.total_transactions}</td>
                <td style={{ color: (a.avg_fraud_prob || 0) > 0.8 ? '#ef4444' : '#eab308', fontWeight: 700 }}>
                  {((a.avg_fraud_prob || 0) * 100).toFixed(1)}%
                </td>
                <td><RiskBadge level={a.risk_level} /></td>
                <td><RiskBadge level={a.investigation_status || 'Pending'} showDot={false} /></td>
                <td>
                  <button
                    id={`action-${a.dealer_id}`}
                    className="btn btn-secondary btn-sm"
                    onClick={() => setModal(a)}
                  >
                    Update
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {alerts.length === 0 && (
          <div className="empty-state"><h3>No high-risk dealers found</h3><p>All dealers are within normal ranges.</p></div>
        )}
      </div>

      {modal && (
        <ActionModal
          dealer={modal}
          onClose={() => setModal(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
