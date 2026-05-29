import React, { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import { searchDealers } from '../api/client';
import RiskBadge from '../components/RiskBadge';

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

export default function DealerSearch() {
  const [query,   setQuery]   = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open,    setOpen]    = useState(false);
  const navigate = useNavigate();
  const wrapRef  = useRef(null);

  const doSearch = useCallback(debounce(async (q) => {
    if (!q || q.length < 1) { setResults([]); setOpen(false); return; }
    setLoading(true);
    try {
      const res = await searchDealers(q);
      setResults(res.data || []);
      setOpen(true);
    } catch { setResults([]); }
    finally  { setLoading(false); }
  }, 280), []);

  const handleChange = (e) => {
    setQuery(e.target.value);
    doSearch(e.target.value);
  };

  const handleSelect = (d) => {
    setOpen(false);
    setQuery(d.dealer_name);
    navigate(`/dealers/${d.dealer_id}`);
  };

  return (
    <div>
      <div className="section-header">
        <div>
          <div className="section-title">Dealer Investigation Search</div>
          <div className="section-sub">Search by Dealer Name, ID, or District</div>
        </div>
      </div>

      {/* Big search bar */}
      <div className="card" style={{ maxWidth: 680, margin: '0 auto 32px', padding: '32px' }}>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 16, fontSize: '0.9rem' }}>
          Enter a dealer name, ID, or district to begin investigating. The system will
          compute ML fraud probability and rule-based anomaly scores in real-time.
        </p>
        <div className="search-wrapper" ref={wrapRef}>
          <Search className="search-icon" size={18} />
          <input
            id="dealer-search-input"
            className="input"
            placeholder="Search dealers... (e.g. AgriMart_0042, Nagpur)"
            value={query}
            onChange={handleChange}
            onFocus={() => results.length && setOpen(true)}
            autoComplete="off"
            style={{ fontSize: '1rem', padding: '13px 14px 13px 40px' }}
          />
          {query && (
            <button onClick={() => { setQuery(''); setResults([]); setOpen(false); }}
              style={{ position:'absolute', right:12, top:'50%', transform:'translateY(-50%)',
                       background:'none', border:'none', cursor:'pointer', color:'var(--text-muted)' }}>
              <X size={16} />
            </button>
          )}

          {open && results.length > 0 && (
            <div className="autocomplete-dropdown">
              {results.map(d => (
                <div key={d.dealer_id} className="autocomplete-item"
                  onClick={() => handleSelect(d)}>
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{d.dealer_name}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      ID: {d.dealer_id} · {d.district}
                    </div>
                  </div>
                  <RiskBadge level={d.risk_level} />
                </div>
              ))}
            </div>
          )}

          {open && results.length === 0 && !loading && query && (
            <div className="autocomplete-dropdown" style={{ padding: '16px', textAlign:'center',
              color:'var(--text-muted)', fontSize:'0.85rem' }}>
              No dealers found for "{query}"
            </div>
          )}
        </div>

        {loading && (
          <div style={{ display:'flex', alignItems:'center', gap:8, marginTop:12,
            color:'var(--text-muted)', fontSize:'0.8rem' }}>
            <div className="spinner" style={{ width:16, height:16, borderWidth:2 }} />
            Searching...
          </div>
        )}
      </div>

      {/* How-to guide */}
      <div style={{ maxWidth:680, margin:'0 auto' }}>
        <div className="card">
          <div className="section-title" style={{ marginBottom:16 }}>Investigation Workflow</div>
          {[
            ['1. Search', 'Enter a dealer name, ID, or district in the search box above.'],
            ['2. Select', 'Click a dealer from the autocomplete results.'],
            ['3. Analyze', 'Review ML fraud probability, rule-based anomaly score, and SHAP insights.'],
            ['4. Drill down', 'Inspect individual transactions to understand what triggered the flag.'],
            ['5. Act', 'Update investigation status — Pending → Under Review → Confirmed / Cleared.'],
          ].map(([step, desc]) => (
            <div key={step} style={{ display:'flex', gap:14, marginBottom:14, alignItems:'flex-start' }}>
              <div style={{ background:'var(--accent-dim)', color:'var(--accent)', borderRadius:6,
                padding:'3px 10px', fontWeight:700, fontSize:'0.75rem', flexShrink:0, marginTop:2 }}>
                {step}
              </div>
              <p style={{ color:'var(--text-secondary)', fontSize:'0.875rem', lineHeight:1.6 }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
