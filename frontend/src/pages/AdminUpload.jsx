import React, { useEffect, useRef, useState } from 'react';
import { Upload, RefreshCw, Terminal } from 'lucide-react';
import { uploadCSV, triggerRetrain, fetchUploadLogs, fetchAuditLogs } from '../api/client';
import toast from 'react-hot-toast';

export default function AdminUpload() {
  const [dragging,   setDragging]   = useState(false);
  const [uploading,  setUploading]  = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [logs,       setLogs]       = useState([]);
  const [auditLogs,  setAuditLogs]  = useState([]);
  const fileRef   = useRef(null);
  const logsRef   = useRef(null);

  const refreshLogs = () => {
    fetchUploadLogs().then(r => setLogs(r.data?.logs || []));
    fetchAuditLogs().then(r => setAuditLogs(r.data || []));
  };

  useEffect(() => {
    refreshLogs();
    const t = setInterval(refreshLogs, 3000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (logsRef.current) logsRef.current.scrollTop = logsRef.current.scrollHeight;
  }, [logs]);

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await uploadCSV(fd);
      toast.success(r.data.message);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    } finally { setUploading(false); }
  };

  const handleDrop = (e) => {
    e.preventDefault(); setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleRetrain = async () => {
    setRetraining(true);
    try {
      const r = await triggerRetrain();
      toast.success(r.data.message);
    } catch { toast.error('Failed to trigger retrain'); }
    finally { setRetraining(false); }
  };

  return (
    <div>
      <div className="section-header">
        <div>
          <div className="section-title">Admin Control Panel</div>
          <div className="section-sub">Upload datasets, refresh anomaly scores, retrain model</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom:24 }}>
        {/* Upload drop zone */}
        <div className="card">
          <div className="chart-title">Upload CSV Dataset</div>
          <div
            id="csv-dropzone"
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            style={{
              border: `2px dashed ${dragging ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 'var(--radius)',
              padding: '40px 20px',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s',
              background: dragging ? 'var(--accent-dim)' : 'var(--bg-secondary)',
            }}
          >
            <Upload size={32} style={{ color:'var(--accent)', marginBottom:12 }} />
            <div style={{ color:'var(--text-secondary)', fontSize:'0.9rem' }}>
              {uploading ? 'Uploading...' : 'Drop transactions.csv here or click to browse'}
            </div>
            <div style={{ color:'var(--text-muted)', fontSize:'0.75rem', marginTop:6 }}>
              CSV must have headers matching the pipeline schema
            </div>
          </div>
          <input ref={fileRef} type="file" accept=".csv" style={{ display:'none' }}
            onChange={e => handleFile(e.target.files[0])} />
        </div>

        {/* Pipeline actions */}
        <div className="card">
          <div className="chart-title">Pipeline Actions</div>
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            <div style={{ padding:16, background:'var(--bg-secondary)', borderRadius:'var(--radius)', border:'1px solid var(--border)' }}>
              <div style={{ fontWeight:600, marginBottom:4 }}>Retrain ML Model</div>
              <div style={{ fontSize:'0.8rem', color:'var(--text-muted)', marginBottom:12 }}>
                Runs 30 Optuna trials on uploaded data. Takes ~5 minutes.
              </div>
              <button id="btn-retrain" className="btn btn-primary btn-sm"
                onClick={handleRetrain} disabled={retraining}>
                <RefreshCw size={14} />
                {retraining ? 'Triggering...' : 'Retrain Model'}
              </button>
            </div>

            <div style={{ padding:16, background:'var(--bg-secondary)', borderRadius:'var(--radius)', border:'1px solid var(--border)' }}>
              <div style={{ fontWeight:600, marginBottom:4 }}>Processing Logs</div>
              <div style={{ fontSize:'0.8rem', color:'var(--text-muted)', marginBottom:12 }}>
                Auto-refreshes every 3 seconds during processing.
              </div>
              <button id="btn-refresh-logs" className="btn btn-secondary btn-sm" onClick={refreshLogs}>
                <Terminal size={14} /> Refresh Logs
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Live log terminal */}
      <div className="card" style={{ marginBottom:24 }}>
        <div className="chart-title" style={{ display:'flex', alignItems:'center', gap:8 }}>
          <Terminal size={16} style={{ color:'var(--accent)' }} />
          Processing Log
          <span style={{ marginLeft:'auto', fontSize:'0.72rem', color:'var(--text-muted)' }}>
            Auto-refreshing every 3s
          </span>
        </div>
        <div ref={logsRef} style={{
          background:'#050d18', borderRadius:'var(--radius-sm)',
          padding:16, maxHeight:250, overflowY:'auto',
          fontFamily:'monospace', fontSize:'0.78rem', color:'#7dd3fc',
          lineHeight:1.8, border:'1px solid var(--border)',
        }}>
          {logs.length ? logs.map((l,i) => <div key={i}>{l}</div>)
            : <div style={{ color:'#475569' }}>No logs yet...</div>}
        </div>
      </div>

      {/* Audit log */}
      <div className="card">
        <div className="chart-title">Audit Log</div>
        <div className="table-wrapper" style={{ border:'none', borderRadius:0 }}>
          <table>
            <thead>
              <tr><th>Timestamp</th><th>User</th><th>Action</th><th>Entity</th></tr>
            </thead>
            <tbody>
              {auditLogs.map(l => (
                <tr key={l.id}>
                  <td style={{ fontSize:'0.78rem', whiteSpace:'nowrap' }}>
                    {l.timestamp ? new Date(l.timestamp).toLocaleString('en-IN') : '—'}
                  </td>
                  <td>{l.user_email}</td>
                  <td>{l.action}</td>
                  <td>{l.entity_type} #{l.entity_id}</td>
                </tr>
              ))}
              {!auditLogs.length && (
                <tr><td colSpan={4} style={{ textAlign:'center', color:'var(--text-muted)', padding:24 }}>No audit entries yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
