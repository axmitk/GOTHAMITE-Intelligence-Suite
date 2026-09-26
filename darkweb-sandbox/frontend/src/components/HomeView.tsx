import React from 'react';
import { Shield, BookOpen, Terminal, ShoppingBag, MessageSquare, ArrowRight } from 'lucide-react';
import { NavView } from '../types';

interface HomeViewProps {
  onSelectView: (view: NavView) => void;
}

export const HomeView: React.FC<HomeViewProps> = ({ onSelectView }) => {
  return (
    <div id="view-home" className="p-6 space-y-6 max-w-5xl mx-auto font-mono text-gray-200">
      {/* Banner */}
      <div className="border-b border-[#153634] pb-4">
        <h2 className="text-2xl font-bold text-[#2bf0a6] font-serif uppercase tracking-widest">
          GOTHAMITE Sandbox Environment
        </h2>
        <p className="text-xs text-gray-400 font-mono mt-1">
          Cybersecurity Educational Simulation System — SIH 26151
        </p>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div className="p-4 bg-[#0d1f20] border border-[#153634] rounded-lg space-y-2.5">
          <div className="flex items-center space-x-2 text-[#2bf0a6]">
            <BookOpen className="w-4 h-4" />
            <h3 className="font-bold text-white uppercase tracking-wider">Mission Directive</h3>
          </div>
          <p className="text-gray-400 leading-relaxed text-[11px]">
            GOTHAMITE allows security researchers, university students, and ethical cybersecurity analysts to study darknet protocols, marketplace architectures, and threat actor behavior safely without real-world illicit exposure.
          </p>
        </div>

        <div className="p-4 bg-[#0d1f20] border border-[#153634] rounded-lg space-y-2.5">
          <div className="flex items-center space-x-2 text-[#2bf0a6]">
            <Shield className="w-4 h-4" />
            <h3 className="font-bold text-white uppercase tracking-wider">Simulation Safety Rules</h3>
          </div>
          <p className="text-gray-400 leading-relaxed text-[11px]">
            All cryptographic keys, passports, credit cards, driver licenses, and database dumps rendered in this sandbox are synthetic placeholders generated strictly for threat detection pattern analysis and SIEM signature modeling.
          </p>
        </div>
      </div>

      {/* Quick Launch Card */}
      <div className="p-4 bg-[#051614] border border-[#2bf0a6]/40 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="font-bold text-[#2bf0a6] text-sm flex items-center gap-1.5">
            <ShoppingBag className="w-4 h-4" />
            Launch Active Marketplace Sandbox
          </div>
          <div className="text-gray-400 text-xs mt-0.5">
            Access DarkTrade Beta mock storefront with 8 verified threat intelligence vectors
          </div>
        </div>
        <button
          onClick={() => onSelectView('marketplace')}
          className="bg-[#2bf0a6] text-black font-bold px-4 py-2 rounded text-xs hover:bg-emerald-400 transition flex items-center justify-center gap-1.5 shrink-0 cursor-pointer shadow-[0_0_12px_rgba(43,240,166,0.2)]"
        >
          <span>Open DarkTrade</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Auxiliary Nav Quick-Links */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
        <div
          onClick={() => onSelectView('forum-alpha')}
          className="p-3 bg-[#0d1f20] border border-[#153634] hover:border-[#2bf0a6]/50 rounded cursor-pointer transition flex items-center justify-between"
        >
          <div>
            <div className="text-xs font-bold text-white flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-[#2bf0a6]" />
              Forum Alpha
            </div>
            <div className="text-[10px] text-gray-400">Underground discussions &amp; 0-day leaks</div>
          </div>
          <ArrowRight className="w-4 h-4 text-gray-500" />
        </div>

        <div
          onClick={() => onSelectView('forum-gamma')}
          className="p-3 bg-[#0d1f20] border border-[#153634] hover:border-[#2bf0a6]/50 rounded cursor-pointer transition flex items-center justify-between"
        >
          <div>
            <div className="text-xs font-bold text-white flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-[#2bf0a6]" />
              Forum Gamma
            </div>
            <div className="text-[10px] text-gray-400">De-anonymization telemetry &amp; live traces</div>
          </div>
          <ArrowRight className="w-4 h-4 text-gray-500" />
        </div>
      </div>
    </div>
  );
};
