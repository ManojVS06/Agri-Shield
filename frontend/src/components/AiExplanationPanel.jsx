import React, { useEffect, useState } from 'react';
import { Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import { fetchTransactionExplanation } from '../api/client';

export default function AiExplanationPanel({ txnId, onClose }) {
  const [explanation, setExplanation] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadExplanation = () => {
    setLoading(true);
    setError(null);
    fetchTransactionExplanation(txnId)
      .then(response => {
        if (response.data?.explanation) {
          setExplanation(response.data.explanation);
        } else {
          setError('No explanation returned from server.');
        }
      })
      .catch(err => {
        setError('Failed to fetch AI explanation. Make sure the API key is configured.');
        console.error(err);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadExplanation();
  }, [txnId]);

  const containerStyle = {
    background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%)',
    border: '1px solid rgba(0, 212, 170, 0.25)',
    boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
    backdropFilter: 'blur(8px)',
    borderRadius: '12px',
    padding: '18px 22px',
    marginTop: '12px',
    position: 'relative',
    transition: 'all 0.3s ease',
  };

  const headerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '10px',
  };

  const titleWrapStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  };

  const titleStyle = {
    fontWeight: 600,
    fontSize: '0.88rem',
    color: '#00d4aa',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  };

  const badgeStyle = {
    background: 'rgba(0, 212, 170, 0.15)',
    color: '#00d4aa',
    border: '1px solid rgba(0, 212, 170, 0.3)',
    borderRadius: '12px',
    padding: '2px 8px',
    fontSize: '0.68rem',
    fontWeight: 500,
  };

  const contentStyle = {
    fontSize: '0.85rem',
    lineHeight: '1.5',
    color: '#cbd5e1',
    whiteSpace: 'pre-wrap',
  };

  const closeButtonStyle = {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#94a3b8',
    fontSize: '0.9rem',
    padding: '4px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'color 0.2s',
  };

  if (loading) return (
    <div style={containerStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#94a3b8', fontSize: '0.85rem' }}>
        <RefreshCw size={14} className="spin" style={{ animation: 'spin-anim 1.5s linear infinite' }} />
        <span>Gemini AI is analyzing agricultural context and generating explanation...</span>
        <style>{`
          @keyframes spin-anim {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );

  if (error) return (
    <div style={{ ...containerStyle, border: '1px solid rgba(239, 68, 68, 0.25)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#ef4444', fontSize: '0.85rem', fontWeight: 600 }}>
          <AlertCircle size={15} />
          <span>AI Explanation Error</span>
        </div>
        <button onClick={onClose} style={closeButtonStyle}>✕</button>
      </div>
      <div style={{ color: '#cbd5e1', fontSize: '0.82rem', marginBottom: 10 }}>
        {error}
      </div>
      <button 
        onClick={loadExplanation}
        style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#ef4444',
          borderRadius: '6px',
          padding: '4px 10px',
          fontSize: '0.75rem',
          cursor: 'pointer',
          fontWeight: 500,
          transition: 'all 0.2s',
        }}
      >
        Retry
      </button>
    </div>
  );

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={titleWrapStyle}>
          <div style={titleStyle}>
            <Sparkles size={15} />
            <span>AI Automated Reasoning</span>
          </div>
          <span style={badgeStyle}>Gemini AI</span>
        </div>
        <button onClick={onClose} style={closeButtonStyle} title="Close explanation">✕</button>
      </div>
      <div style={contentStyle}>
        {explanation}
      </div>
    </div>
  );
}
