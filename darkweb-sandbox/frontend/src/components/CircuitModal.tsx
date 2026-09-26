import React from 'react';
import { X, ShieldCheck, RefreshCw, Globe, ArrowRight, Layers } from 'lucide-react';
import { CircuitHop } from '../types';

interface CircuitModalProps {
  isOpen: boolean;
  onClose: () => void;
  circuitRoute: CircuitHop[];
  onNewIdentity: () => void;
  isGeneratingIdentity: boolean;
}

export const CircuitModal: React.FC<CircuitModalProps> = ({
  isOpen,
  onClose,
  circuitRoute,
  onNewIdentity,
  isGeneratingIdentity
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-[#0a1617] border border-[#1d4a46] rounded-lg max-w-xl w-full p-5 shadow-2xl font-mono text-gray-200 relative space-y-4 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between border-b border-[#153634] pb-3">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded bg-emerald-950/70 border border-[#2bf0a6]/40 text-[#2bf0a6]">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide">
                Simulated Onion Circuit Inspector
              </h3>
              <p className="text-[10px] text-gray-400">
                Tor v3 3-hop telescoping path with layered AES-CTR-256 wrapping
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Visual Hop Flow */}
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
            {circuitRoute.map((hop, idx) => {
              const roleTitle = idx === 0 ? 'Guard Node' : idx === 1 ? 'Middle Relay' : 'Exit Relay';
              const roleBadge =
                idx === 0
                  ? 'bg-blue-950 text-blue-300 border-blue-500/30'
                  : idx === 1
                  ? 'bg-purple-950 text-purple-300 border-purple-500/30'
                  : 'bg-emerald-950 text-emerald-300 border-emerald-500/30';

              return (
                <div
                  key={hop.name}
                  className="p-3 bg-[#0d1f20] border border-[#153634] rounded relative overflow-hidden flex flex-col justify-between space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#2bf0a6]">{hop.name}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-semibold ${roleBadge}`}>
                      {roleTitle}
                    </span>
                  </div>

                  <div className="space-y-1 text-[11px] text-gray-300">
                    <div className="flex items-center gap-1.5 text-gray-400">
                      <Globe className="w-3 h-3 text-[#1da876]" />
                      <span>{hop.country} ({hop.countryCode})</span>
                    </div>
                    <div className="text-[10px] text-gray-500 font-mono">IP: {hop.ip}</div>
                    <div className="text-[10px] text-gray-400">Latency: {hop.latency}ms</div>
                  </div>

                  <div className="text-[9px] text-[#1da876] pt-1 border-t border-[#153634]/60 flex items-center justify-between">
                    <span>Layer {3 - idx}: Encrypted</span>
                    <ShieldCheck className="w-3 h-3" />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Circuit Details Information */}
          <div className="p-3 bg-black/60 rounded border border-[#153634] text-[11px] space-y-1.5 text-gray-400">
            <div className="text-xs font-bold text-gray-300 flex items-center gap-1.5">
              <span>Circuit Status:</span>
              <span className="text-[#2bf0a6]">ESTABLISHED &amp; ISOLATED</span>
            </div>
            <p className="text-[10px] leading-relaxed">
              In this educational sandbox, circuit routing isolates each connection so that the origin sandbox client IP is strictly hidden behind the multi-hop onion proxy tunnel.
            </p>
          </div>
        </div>

        <div className="pt-2 flex items-center justify-between border-t border-[#153634]">
          <button
            disabled={true}
            className="px-3 py-1.5 rounded bg-[#0d1f20] border border-[#1d4a46] text-gray-500 text-xs flex items-center gap-2 cursor-not-allowed"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Path rotated automatically by demo_viewer</span>
          </button>

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-[#2bf0a6] hover:bg-emerald-400 text-black font-bold text-xs transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
