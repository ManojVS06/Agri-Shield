import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { IndianRupee, TrendingUp, AlertTriangle, Users, Map, CheckCircle } from 'lucide-react';
import { fetchKPIs, fetchMonthlyTrend, fetchFraudTypes, fetchDistrictHeatmap } from '../api/client';

const FRAUD_COLORS = ['#ef4444','#f59e0b','#8b5cf6','#4f8ef7','#00d4aa','#22c55e','#ec4899','#6366f1'];

function KPICard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="kpi-card">
      <div className="kpi-icon" style={{ background: `${color}20`, color }}>
        <Icon size={20} />
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [kpis,     setKpis]     = useState(null);
  const [trend,    setTrend]    = useState([]);
  const [types,    setTypes]    = useState([]);
  const [heatmap,  setHeatmap]  = useState([]);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    Promise.all([fetchKPIs(), fetchMonthlyTrend(), fetchFraudTypes(), fetchDistrictHeatmap()])
      .then(([k, t, ty, h]) => {
        setKpis(k.data);
        setTrend(t.data);
        setTypes(ty.data);
        setHeatmap(h.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="loading-wrap">
      <div className="spinner" />
      <span>Loading dashboard...</span>
    </div>
  );

  const fmt = (n) => n >= 1e7 ? `₹${(n/1e7).toFixed(1)}Cr` : n >= 1e5 ? `₹${(n/1e5).toFixed(1)}L` : `₹${n?.toLocaleString('en-IN')}`;

  return (
    <div>
      <div className="section-header">
        <div>
          <div className="section-title">Dashboard Overview</div>
          <div className="section-sub">Real-time agricultural subsidy fraud monitoring</div>
        </div>
      </div>

      {/* KPI Cards */}
      {kpis && (
        <div className="kpi-grid">
          <KPICard icon={IndianRupee} label="Total Subsidy Distributed" color="#00d4aa"
            value={fmt(kpis.total_subsidy_distributed)} sub="Across all districts" />
          <KPICard icon={TrendingUp} label="Total Transactions" color="#4f8ef7"
            value={kpis.total_transactions?.toLocaleString()} sub="All time" />
          <KPICard icon={AlertTriangle} label="Fraud Rate" color="#ef4444"
            value={`${kpis.fraud_percentage}%`} sub="ML + Rule-based flags" />
          <KPICard icon={Users} label="High-Risk Dealers" color="#f59e0b"
            value={kpis.high_risk_dealers} sub="Avg probability ≥ 60%" />
          <KPICard icon={Map} label="Districts Monitored" color="#8b5cf6"
            value={kpis.districts_monitored} sub="Pan-India" />
          <KPICard icon={CheckCircle} label="Confirmed Fraud Cases" color="#22c55e"
            value={kpis.confirmed_fraud_cases} sub="Investigator confirmed" />
        </div>
      )}

      {/* Charts row */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Monthly trend */}
        <div className="chart-card">
          <div className="chart-title">Monthly Fraud Trend</div>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={v => v?.slice(2)} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid #00d4aa44', borderRadius: 8 }} />
              <Legend />
              <Line type="monotone" dataKey="total_transactions" stroke="#4f8ef7" name="Total" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="fraud_transactions" stroke="#ef4444" name="Fraud" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Fraud type pie */}
        <div className="chart-card">
          <div className="chart-title">Fraud Type Distribution</div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={types} dataKey="count" nameKey="fraud_type"
                cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name?.split(' ')[0]} ${(percent*100).toFixed(0)}%`}
                labelLine={false} fontSize={10}>
                {types.map((_, i) => <Cell key={i} fill={FRAUD_COLORS[i % FRAUD_COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid #00d4aa44', borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* District fraud rate bar */}
      <div className="chart-card">
        <div className="chart-title">District-Level Fraud Rate (%)</div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={[...heatmap].sort((a,b) => b.fraud_rate - a.fraud_rate)}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="district" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} unit="%" />
            <Tooltip contentStyle={{ background: '#1a2235', border: '1px solid #00d4aa44', borderRadius: 8 }}
              formatter={v => [`${v}%`, 'Fraud Rate']} />
            <Bar dataKey="fraud_rate" fill="#ef4444" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
