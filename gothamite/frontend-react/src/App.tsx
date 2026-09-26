import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Network, Activity, User, Clock } from 'lucide-react';
import { getGraph, getHealth } from './api/client';
import type { GraphPayload } from './types/api';
import { Overview } from './pages/Overview';
import { Graph } from './pages/Graph';
import { Dossier } from './pages/Dossier';
import { Timeline } from './pages/Timeline';

export const App: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'error'>('checking');

  useEffect(() => {
    // Acceptance criterion 3: Call GET /api/v1/graph and log real response
    const verifyBackendConnection = async () => {
      try {
        console.log('[GOTHAMITE] Verifying API backend connection...');
        const health = await getHealth();
        console.log('[GOTHAMITE] Backend Health check response:', health);

        const graph: GraphPayload = await getGraph();
        console.log('[GOTHAMITE] GET /api/v1/graph successfully received real payload:', graph);

        setBackendStatus('connected');
      } catch (err) {
        console.error('[GOTHAMITE] Failed to connect to backend:', err);
        setBackendStatus('error');
      }
    };

    verifyBackendConnection();
  }, []);

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-surface-raised text-accent-cyan border border-border'
        : 'text-text-secondary hover:text-text-primary hover:bg-surface'
    }`;

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-base text-text-primary flex flex-col font-body">
        {/* TOP BAR */}
        <header className="border-b border-border bg-surface px-6 py-3 flex items-center justify-between sticky top-0 z-50">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-lg tracking-wider text-text-primary">
                GOTHAMITE
              </span>
            </div>

            {/* Navigation Tabs */}
            <nav className="flex items-center gap-2">
              <NavLink to="/overview" className={navLinkClass}>
                <Activity size={16} />
                <span>Overview</span>
              </NavLink>
              <NavLink to="/graph" className={navLinkClass}>
                <Network size={16} />
                <span>Graph</span>
              </NavLink>
              <NavLink to="/dossier" className={navLinkClass}>
                <User size={16} />
                <span>Dossier</span>
              </NavLink>
              <NavLink to="/timeline" className={navLinkClass}>
                <Clock size={16} />
                <span>Timeline</span>
              </NavLink>
            </nav>
          </div>

          {/* Backend Connection Indicator (UX_CORRECTION.md §5) */}
          <div className="flex items-center gap-2 text-xs font-mono">
            {backendStatus === 'connected' && (
              <div className="flex items-center gap-2 text-text-secondary">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span>Connected</span>
              </div>
            )}
            {backendStatus === 'checking' && (
              <div className="flex items-center gap-2 text-text-tertiary">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                <span>Connecting...</span>
              </div>
            )}
            {backendStatus === 'error' && (
              <div className="flex items-center gap-2 text-red-400">
                <span className="w-2 h-2 rounded-full bg-red-400"></span>
                <span>Disconnected</span>
              </div>
            )}
          </div>
        </header>

        {/* MAIN CONTENT ROUTING */}
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/graph" element={<Graph />} />
            <Route path="/dossier" element={<Dossier />} />
            <Route path="/dossier/:personaId" element={<Dossier />} />
            <Route path="/timeline" element={<Timeline />} />
            <Route path="*" element={<Navigate to="/overview" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
