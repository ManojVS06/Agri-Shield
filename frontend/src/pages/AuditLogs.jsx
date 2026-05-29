import React, { useEffect, useState, useMemo } from 'react';
import { Search, Download, RefreshCw, Filter } from 'lucide-react';
import { fetchAuditLogs } from '../api/client';

const ENTITY_COLORS = {
  investigation: { bg: 'rgba(99,102,241,0.15)', color: '#818cf8' },
  dealer:        { bg: 'rgba(239,68,68,0.12)',   color: '#f87171' },
  transaction:   { bg: 'rgba(245,158,11,0.12)',  color: '#fbbf24' },
  upload:        { bg: 'rgba(34,197,94,0.12)',   color: '#4ade80' },
};

function EntityBadge({ type }) {
  const s = ENTITY_COLORS[type?.toLowerCase()] || { bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' };
  return (
    <span style={{
      background: s.bg, color: s.color,
      borderRadius: 4, padding: '2px 8px',
      fontSize: '0.72rem', fontWeight: 600, textTransform: 'capitalize',
    }}>
      {type || 'unknown'}
    </span>
  );
}

function exportToCSV(rows) {
  const headers = ['ID', 'Timestamp', 'User', 'Action', 'Entity Type', 'Entity ID', 'Details'];
  const lines = [
    headers.join(','),
    ...rows.map(l => [
      l.id,
      l.timestamp ? new Date(l.timestamp).toLocaleString('en-IN') : '',
      `"${l.user_email || ''}"`,
      `"${l.action || ''}"`,
      l.entity_type || '',
      l.entity_id || '',
      `"${l.details ? JSON.stringify(l.details).replace(/"/g, "'") : ''}"`,
    ].join(',')),
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AuditLogs() {
  const [logs,    setLogs]    = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search,     setSearch]     = useState('');
  const [entityFilter, setEntity]   = useState('');
  const [dateFrom,   setDateFrom]   = useState('');
  const [dateTo,     setDateTo]     = useState('');
  const [limit,      setLimit]      = useState(200);

  const load = () => {
    setLoading(true);
    fetchAuditLogs({ limit })
      .then(r => setLogs(r.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [limit]);

  // Client-side filter
  const filtered = useMemo(() => {
    let rows = logs;
    if (search) {
      const q = search.toLowerCase();
      rows = rows.filter(l =>
        (l.user_email || '').toLowerCase().includes(q) ||
        (l.action     || '').toLowerCase().includes(q)
      );
    }
    if (entityFilter) rows = rows.filter(l => l.entity_type === entityFilter);
    if (dateFrom) rows = rows.filter(l => l.timestamp && new Date(l.timestamp) >= new Date(dateFrom));
    if (dateTo)   rows = rows.filter(l => l.timestamp && new Date(l.timestamp) <= new Date(dateTo + 'T23:59:59'));
    return rows;
  }, [logs, search, entityFilter, dateFrom, dateTo]);

  const entityTypes = useMemo(() => [...new Set(logs.map(l => l.entity_type).filter(Boolean))], [logs]);

  return (
    <div>
      {/* Header */}
      <div className="section-header">
        <div>
          <div className="section-title">Audit Logs</div>
          <div className="section-sub">
            Full trail of all investigator actions — {filtered.length} of {logs.length} entries
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            id="btn-export-audit"
            className="btn btn-secondary btn-sm"
            onClick={() => exportToCSV(filtered)}
            disabled={!filtered.length}
          >
            <Download size={14} /> Export CSV
          </button>
          <button
            id="btn-refresh-audit"
            className="btn btn-secondary btn-sm"
            onClick={load}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="card" style={{ marginBottom: 20, padding: '14px 20px' }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Search */}
          <div style={{ position: 'relative', flex: '1 1 200px', minWidth: 180 }}>
            <Search size={14} style={{
              position: 'absolute', left: 10, top: '50%',
              transform: 'translateY(-50%)', color: 'var(--text-muted)',
            }} />
            <input
              id="audit-search"
              className="input"
              placeholder="Search user or action..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ paddingLeft: 32, paddingTop: 7, paddingBottom: 7 }}
            />
          </div>

          {/* Entity type */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Filter size={13} style={{ color: 'var(--text-muted)' }} />
            <select
              id="audit-entity-filter"
              className="input"
              value={entityFilter}
              onChange={e => setEntity(e.target.value)}
              style={{ paddingTop: 7, paddingBottom: 7, minWidth: 140 }}
            >
              <option value="">All entity types</option>
              {entityTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          {/* Date range */}
          <input
            id="audit-date-from"
            type="date"
            className="input"
            value={dateFrom}
            onChange={e => setDateFrom(e.target.value)}
            style={{ paddingTop: 7, paddingBottom: 7, minWidth: 140 }}
            title="From date"
          />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>to</span>
          <input
            id="audit-date-to"
            type="date"
            className="input"
            value={dateTo}
            onChange={e => setDateTo(e.target.value)}
            style={{ paddingTop: 7, paddingBottom: 7, minWidth: 140 }}
            title="To date"
          />

          {/* Limit */}
          <select
            id="audit-limit"
            className="input"
            value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            style={{ paddingTop: 7, paddingBottom: 7, minWidth: 110 }}
          >
            {[100, 200, 500, 1000].map(n => <option key={n} value={n}>Last {n}</option>)}
          </select>

          {(search || entityFilter || dateFrom || dateTo) && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => { setSearch(''); setEntity(''); setDateFrom(''); setDateTo(''); }}
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="table-wrapper">
        {loading ? (
          <div className="loading-wrap"><div className="spinner" /><span>Loading audit logs...</span></div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Timestamp</th>
                <th>User</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(l => (
                <tr key={l.id}>
                  <td className="primary" style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{l.id}</td>
                  <td style={{ whiteSpace: 'nowrap', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {l.timestamp ? new Date(l.timestamp).toLocaleString('en-IN') : '—'}
                  </td>
                  <td style={{ fontSize: '0.82rem' }}>{l.user_email || '—'}</td>
                  <td style={{ fontSize: '0.82rem', maxWidth: 260 }}>{l.action}</td>
                  <td>
                    <EntityBadge type={l.entity_type} />
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 6 }}>
                      #{l.entity_id}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {l.details ? JSON.stringify(l.details).slice(0, 80) : '—'}
                  </td>
                </tr>
              ))}
              {!filtered.length && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>
                    {logs.length ? 'No entries match the current filters.' : 'No audit entries yet.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
