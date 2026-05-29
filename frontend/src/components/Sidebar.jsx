import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Search, Users, AlertTriangle,
  Upload, FileText, Shield, User
} from 'lucide-react';

// Only import UserButton when Clerk is actually configured
const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
let UserButton = null;
if (CLERK_KEY) {
  // Dynamic-style conditional — works fine since this module is only evaluated once
  // eslint-disable-next-line no-undef
  UserButton = React.lazy(() =>
    import('@clerk/clerk-react').then(m => ({ default: m.UserButton }))
  );
}

const NAV = [
  { section: 'Overview', items: [
    { to: '/',            icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/alerts',      icon: AlertTriangle,   label: 'Fraud Alerts' },
  ]},
  { section: 'Investigation', items: [
    { to: '/search',      icon: Search,          label: 'Search Dealers' },
    { to: '/dealers',     icon: Users,           label: 'Dealer Risk Table' },
    { to: '/transactions',icon: FileText,        label: 'Transactions' },
  ]},
  { section: 'System', items: [
    { to: '/admin',       icon: Upload,          label: 'Admin Upload' },
    { to: '/audit',       icon: Shield,          label: 'Audit Logs' },
  ]},
];

export default function Sidebar() {
  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark">
          <div className="logo-icon">🌾</div>
          <div>
            <div>AgriGuard</div>
            <div className="logo-sub">Fraud Detection Platform</div>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(section => (
          <div key={section.section}>
            <div className="nav-section-label">{section.section}</div>
            {section.items.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
              >
                <item.icon size={16} />
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        {CLERK_KEY && UserButton ? (
          <React.Suspense fallback={null}>
            <UserButton afterSignOutUrl="/sign-in" showName />
          </React.Suspense>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            <User size={16} />
            <span>Dev Mode</span>
          </div>
        )}
      </div>
    </div>
  );
}
