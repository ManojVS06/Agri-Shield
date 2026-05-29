import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import {
  ClerkProvider, SignedIn, SignedOut, RedirectToSignIn,
  SignIn, SignUp,
} from '@clerk/clerk-react';
import { Toaster } from 'react-hot-toast';

import Sidebar      from './components/Sidebar';
import Dashboard    from './pages/Dashboard';
import DealerSearch from './pages/DealerSearch';
import DealerTable  from './pages/DealerTable';
import DealerProfile from './pages/DealerProfile';
import Transactions from './pages/Transactions';
import Alerts       from './pages/Alerts';
import AdminUpload  from './pages/AdminUpload';
import AuditLogs    from './pages/AuditLogs';

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function ProtectedLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <div className="topbar">
          <span className="topbar-title">AgriGuard — Fraud Detection Platform</span>
          <div className="topbar-right" style={{ fontSize:'0.82rem', color:'var(--text-muted)' }}>
            National Agricultural Subsidy Monitoring System
          </div>
        </div>
        <div className="page-content">
          <Routes>
            <Route path="/"                element={<Dashboard />} />
            <Route path="/search"          element={<DealerSearch />} />
            <Route path="/dealers"         element={<DealerTable />} />
            <Route path="/dealers/:id"     element={<DealerProfile />} />
            <Route path="/transactions"    element={<Transactions />} />
            <Route path="/alerts"          element={<Alerts />} />
            <Route path="/admin"           element={<AdminUpload />} />
            <Route path="/audit"           element={<AuditLogs />} />
            <Route path="*"               element={<Navigate to="/" />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  if (!CLERK_KEY) {
    // Fallback: run without auth for local dev if key not set
    return (
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{
          style: { background:'var(--bg-card)', color:'var(--text-primary)', border:'1px solid var(--border)' }
        }} />
        <ProtectedLayout />
      </BrowserRouter>
    );
  }

  return (
    <ClerkProvider publishableKey={CLERK_KEY}>
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{
          style: { background:'var(--bg-card)', color:'var(--text-primary)', border:'1px solid var(--border)' }
        }} />
        <Routes>
          <Route path="/sign-in/*" element={<SignIn routing="path" path="/sign-in" />} />
          <Route path="/sign-up/*" element={<SignUp routing="path" path="/sign-up" />} />
          <Route path="/*" element={
            <>
              <SignedIn><ProtectedLayout /></SignedIn>
              <SignedOut><RedirectToSignIn /></SignedOut>
            </>
          } />
        </Routes>
      </BrowserRouter>
    </ClerkProvider>
  );
}
