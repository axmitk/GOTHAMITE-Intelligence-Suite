import React from 'react';
import { Home, MessageSquare, ShoppingBag, ShieldAlert, RefreshCw } from 'lucide-react';
import { NavView } from '../types';

interface SidebarProps {
  currentView: NavView;
  onSelectView: (view: NavView) => void;
  onNewIdentity: () => void;
  isGeneratingIdentity: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onSelectView,
  onNewIdentity,
  isGeneratingIdentity
}) => {
  return (
    <aside
      id="application-sidebar"
      className="w-56 md:w-60 bg-[#071213] border-r border-[#153634] flex flex-col justify-between p-3.5 shrink-0 select-none z-20"
    >
      {/* Brand & Nav Links */}
      <div className="space-y-5">
        {/* GOTHAMITE Sandbox Brand Logo */}
        <div className="flex flex-col items-center text-center pt-2 pb-2 border-b border-[#153634]/70">
          <div className="relative w-14 h-14 flex items-center justify-center mb-2">
            <svg
              className="w-14 h-14 text-[#2bf0a6]/30 absolute animate-pulse pointer-events-none"
              fill="none"
              viewBox="0 0 100 100"
            >
              <polygon
                points="50 3, 93 25, 93 75, 50 97, 7 75, 7 25"
                stroke="currentColor"
                strokeWidth="2"
              />
            </svg>
            {/* Stylized G logo */}
            <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-[#0c2e2c] to-[#041112] border border-[#2bf0a6]/50 flex items-center justify-center shadow-lg">
              <span className="text-2xl font-black text-[#2bf0a6] font-mono tracking-tighter">
                G
              </span>
            </div>
          </div>
          <h1 className="text-lg font-bold tracking-[0.18em] text-white font-serif uppercase leading-tight">
            GOTHAMITE
          </h1>
          <p className="text-[9px] font-bold tracking-[0.22em] text-[#2bf0a6] mt-0.5">
            DARK WEB SANDBOX
          </p>
          <p className="text-[10px] text-gray-400 font-mono tracking-wide mt-1">
            Explore • Scrape • De-anonymize
          </p>
        </div>

        {/* Primary Sandbox Navigation Menu */}
        <nav className="space-y-1.5 font-mono" id="sandbox-navigation">
          {/* Home Item */}
          <button
            onClick={() => onSelectView('home')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-left transition group ${
              currentView === 'home'
                ? 'text-white bg-[#0e332e]/90 border border-[#2bf0a6]/60 shadow-[0_0_12px_rgba(43,240,166,0.15)] relative'
                : 'text-gray-400 hover:text-white hover:bg-[#0d1f20]'
            }`}
          >
            {currentView === 'home' && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#2bf0a6] rounded-r" />
            )}
            <Home
              className={`w-4 h-4 ${
                currentView === 'home' ? 'text-[#2bf0a6]' : 'text-gray-400 group-hover:text-[#2bf0a6]'
              }`}
            />
            <div className="text-xs">
              <div className={currentView === 'home' ? 'font-medium text-[#2bf0a6]' : 'font-medium text-gray-300'}>
                Home
              </div>
            </div>
          </button>

          {/* Forum Alpha */}
          <button
            onClick={() => onSelectView('forum-alpha')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-left transition group ${
              currentView === 'forum-alpha'
                ? 'text-white bg-[#0e332e]/90 border border-[#2bf0a6]/60 shadow-[0_0_12px_rgba(43,240,166,0.15)] relative'
                : 'text-gray-400 hover:text-white hover:bg-[#0d1f20]'
            }`}
          >
            {currentView === 'forum-alpha' && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#2bf0a6] rounded-r" />
            )}
            <MessageSquare
              className={`w-4 h-4 ${
                currentView === 'forum-alpha'
                  ? 'text-[#2bf0a6]'
                  : 'text-gray-400 group-hover:text-[#2bf0a6]'
              }`}
            />
            <div className="text-xs">
              <div className={currentView === 'forum-alpha' ? 'font-medium text-[#2bf0a6]' : 'font-medium text-gray-300'}>
                Forum Alpha
              </div>
              <div className="text-[10px] text-gray-500 font-sans">Discussions | Leaks | Tools</div>
            </div>
          </button>

          {/* Marketplace Beta (Default Active View in Spec) */}
          <button
            onClick={() => onSelectView('marketplace')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-left transition group ${
              currentView === 'marketplace'
                ? 'text-white bg-[#0e332e]/90 border border-[#2bf0a6]/60 shadow-[0_0_12px_rgba(43,240,166,0.15)] relative'
                : 'text-gray-400 hover:text-white hover:bg-[#0d1f20]'
            }`}
          >
            {currentView === 'marketplace' && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#2bf0a6] rounded-r" />
            )}
            <ShoppingBag
              className={`w-4 h-4 ${
                currentView === 'marketplace'
                  ? 'text-[#2bf0a6]'
                  : 'text-gray-400 group-hover:text-[#2bf0a6]'
              }`}
            />
            <div className="text-xs">
              <div className="font-medium text-[#2bf0a6]">Marketplace Beta</div>
              <div className="text-[10px] text-gray-400 font-sans">Digital | Fraud | Access</div>
            </div>
          </button>

          {/* Forum Gamma */}
          <button
            onClick={() => onSelectView('forum-gamma')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-left transition group ${
              currentView === 'forum-gamma'
                ? 'text-white bg-[#0e332e]/90 border border-[#2bf0a6]/60 shadow-[0_0_12px_rgba(43,240,166,0.15)] relative'
                : 'text-gray-400 hover:text-white hover:bg-[#0d1f20]'
            }`}
          >
            {currentView === 'forum-gamma' && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#2bf0a6] rounded-r" />
            )}
            <ShieldAlert
              className={`w-4 h-4 ${
                currentView === 'forum-gamma'
                  ? 'text-[#2bf0a6]'
                  : 'text-gray-400 group-hover:text-[#2bf0a6]'
              }`}
            />
            <div className="text-xs">
              <div className={currentView === 'forum-gamma' ? 'font-medium text-[#2bf0a6]' : 'font-medium text-gray-300'}>
                Forum Gamma
              </div>
              <div className="text-[10px] text-gray-500 font-sans">Underground | Research</div>
            </div>
          </button>
        </nav>

        {/* Onion Network Status Module */}
        <div className="pt-4 border-t border-[#153634]/70 space-y-3 font-mono">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="relative flex items-center justify-center w-4 h-4">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#2bf0a6] opacity-30"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#2bf0a6]"></span>
              </div>
              <span className="text-xs text-gray-300 font-medium">Onion Network</span>
            </div>
          </div>
          <div className="pl-6 space-y-1">
            <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-500/30">
              Connected
            </span>
            <p className="text-[10px] text-gray-500">3-hop route active</p>
          </div>

          {/* New Identity Interactive Generator */}
          <button
            id="btn-new-identity"
            disabled={true}
            className="w-full mt-2 py-1.5 px-2 bg-[#0d1f20] border border-[#1d4a46] rounded text-gray-500 text-[10px] flex items-center justify-center gap-1.5 cursor-not-allowed"
            title="Paths are auto-rotated by the proxy"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Auto-Rotated</span>
          </button>
        </div>
      </div>

      {/* Sidebar Bottom Signature */}
      <div className="pt-4 border-t border-[#153634]/70 text-center font-serif">
        <p className="text-[11px] italic text-gray-400">
          "Same shadows.
          <br />
          A safer world."
        </p>
        <div className="mt-3 text-[11px] font-mono tracking-wider font-semibold text-gray-300">
          GOTHAMITE
          <div className="text-[10px] text-gray-400 font-normal">SIH 26151</div>
        </div>
      </div>
    </aside>
  );
};
