import React, { useState, useEffect } from 'react';
import { ArrowLeft, ArrowRight, Lock, ShieldCheck } from 'lucide-react';
import { CircuitHop } from '../types';

interface NavigationBarProps {
  currentUrl: string;
  onNavigateUrl: (url: string) => void;
  canGoBack: boolean;
  canGoForward: boolean;
  onBack: () => void;
  onForward: () => void;
  circuitRoute: CircuitHop[];
  onOpenCircuitModal: () => void;
  routeFlicker: boolean;
}

export const NavigationBar: React.FC<NavigationBarProps> = ({
  currentUrl,
  onNavigateUrl,
  canGoBack,
  canGoForward,
  onBack,
  onForward,
  circuitRoute,
  onOpenCircuitModal,
  routeFlicker
}) => {
  const [inputUrl, setInputUrl] = useState(currentUrl);

  useEffect(() => {
    setInputUrl(currentUrl);
  }, [currentUrl]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputUrl.trim()) {
      onNavigateUrl(inputUrl.trim());
    }
  };

  return (
    <div
      id="browser-navigation-bar"
      className="h-10 bg-[#081516] border-b border-[#153634] flex items-center px-3 justify-between text-xs font-mono shrink-0"
    >
      {/* Back / Forward Buttons */}
      <div className="flex items-center space-x-1 mr-3 text-gray-400">
        <button
          id="btn-browser-back"
          onClick={onBack}
          disabled={!canGoBack}
          className={`p-1 rounded transition-colors ${
            canGoBack
              ? 'hover:text-[#2bf0a6] text-gray-300 cursor-pointer'
              : 'text-gray-600 cursor-not-allowed'
          }`}
          title="Back"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <button
          id="btn-browser-forward"
          onClick={onForward}
          disabled={!canGoForward}
          className={`p-1 rounded transition-colors ${
            canGoForward
              ? 'hover:text-[#2bf0a6] text-gray-300 cursor-pointer'
              : 'text-gray-600 cursor-not-allowed'
          }`}
          title="Forward"
        >
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Address Bar Field */}
      <form
        onSubmit={handleSubmit}
        className="flex-1 max-w-2xl bg-[#04090a] border border-[#1d4a46] rounded px-3 py-1 flex items-center space-x-2 text-xs focus-within:border-[#2bf0a6] transition-colors"
      >
        <Lock className="w-3.5 h-3.5 text-[#2bf0a6] shrink-0" />
        <input
          id="browser-url-bar"
          type="text"
          value={inputUrl}
          onChange={(e) => setInputUrl(e.target.value)}
          className="bg-transparent text-gray-200 border-none p-0 text-xs w-full focus:outline-none select-all font-mono tracking-wide"
        />
        <span className="text-[10px] text-gray-600 select-none hidden sm:inline">.mock</span>
      </form>

      {/* Right Simulated Onion Network Circuit Status */}
      <div
        onClick={onOpenCircuitModal}
        className="hidden lg:flex items-center space-x-2 text-[11px] text-gray-400 pl-4 shrink-0 cursor-pointer hover:opacity-90 group"
        title="Click to inspect Onion Circuit Hops"
      >
        <span className="text-[#1da876] group-hover:text-[#2bf0a6] flex items-center gap-1 transition-colors">
          <ShieldCheck className="w-3.5 h-3.5" />
          Simulated Onion Network
        </span>
        <span className="text-gray-600">|</span>
        <span className="text-gray-400">
          3-hop route via{' '}
          <span
            id="relay-path"
            className={`text-[#2bf0a6] font-medium font-mono ${
              routeFlicker ? 'relay-flicker' : ''
            }`}
          >
            {circuitRoute.map((hop) => hop.name).join(' → ')}
          </span>
        </span>
      </div>
    </div>
  );
};
