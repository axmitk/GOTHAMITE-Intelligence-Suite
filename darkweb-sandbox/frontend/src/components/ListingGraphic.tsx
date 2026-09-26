import React from 'react';
import { Lock } from 'lucide-react';
import { ListingItem } from '../types';

interface ListingGraphicProps {
  type: ListingItem['imageType'];
}

export const ListingGraphic: React.FC<ListingGraphicProps> = ({ type }) => {
  switch (type) {
    case 'passport':
      return (
        <div className="w-full h-full flex items-center justify-center space-x-2 p-2 bg-gradient-to-tr from-[#051112] to-[#0c2423]">
          {/* Blue Passport */}
          <div className="w-12 h-16 bg-[#162a36] border border-blue-400/40 rounded-sm flex flex-col items-center justify-center p-1 text-[7px] text-blue-200 text-center shadow-lg transform -rotate-1 hover:rotate-0 transition-transform">
            <span className="text-[6px] tracking-widest text-amber-300 font-serif font-bold">PASSPORT</span>
            <div className="w-4 h-4 rounded-full border border-amber-300/40 my-1 flex items-center justify-center">
              <div className="w-2 h-2 rounded-full border border-amber-300/20" />
            </div>
            <div className="w-7 h-0.5 bg-blue-300/30 mt-1" />
          </div>
          {/* Red/Burgundy Passport */}
          <div className="w-12 h-16 bg-[#2b161e] border border-rose-400/40 rounded-sm flex flex-col items-center justify-center p-1 text-[7px] text-rose-200 text-center shadow-lg transform rotate-2 hover:rotate-0 transition-transform">
            <span className="text-[6px] tracking-widest text-amber-300 font-serif font-bold">PASSPORT</span>
            <div className="w-4 h-4 rounded-full border border-amber-300/40 my-1 flex items-center justify-center">
              <div className="w-2 h-2 rounded-full border border-amber-300/20" />
            </div>
            <div className="w-7 h-0.5 bg-rose-300/30 mt-1" />
          </div>
        </div>
      );

    case 'card':
      return (
        <div className="w-full h-full flex flex-col items-center justify-center p-2 bg-gradient-to-tr from-[#051112] to-[#122b27] relative">
          <div className="w-24 h-14 bg-gradient-to-r from-zinc-800 to-zinc-900 border border-gray-600/40 rounded p-1.5 flex flex-col justify-between text-[7px] font-mono shadow-md">
            <div className="w-3.5 h-2.5 bg-amber-400/90 rounded-xs flex items-center justify-center shadow-xs">
              <div className="w-2 h-1 border border-amber-700/50" />
            </div>
            <div className="text-gray-200 tracking-wider font-semibold">•••• 8912</div>
            <div className="text-[6px] text-gray-400 flex justify-between tracking-tighter">
              <span>VALID</span>
              <span className="text-gray-300">08/28</span>
            </div>
          </div>
        </div>
      );

    case 'vpn':
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-tr from-[#041014] to-[#0d2a33]">
          <div className="p-2 rounded-full bg-cyan-950/40 border border-cyan-500/30 mb-1">
            <Lock className="w-7 h-7 text-cyan-400" />
          </div>
          <span className="text-[8px] font-mono text-cyan-300 tracking-wider font-semibold">
            SECURE TUNNEL
          </span>
        </div>
      );

    case 'pgp':
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-tr from-[#051112] to-[#122822] p-2 font-mono">
          <div className="text-[8px] text-emerald-400/90 border border-emerald-500/30 p-1.5 rounded bg-black/50 text-center leading-tight shadow-inner">
            -----BEGIN PGP-----
            <br />
            8G2F d8el8 610E
            <br />
            -----END PGP-----
          </div>
        </div>
      );

    case 'malware':
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-tr from-[#160a0a] to-[#250d0d]">
          <svg className="w-10 h-10 text-red-500/90 drop-shadow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="2.5" strokeWidth="2" />
            <path
              d="M12 4a5 5 0 0 1 4.33 7.5M12 4a5 5 0 0 0-4.33 7.5M5.07 16a5 5 0 0 1 8.66 0M18.93 16a5 5 0 0 0-8.66 0M12 12v6"
              strokeLinecap="round"
              strokeWidth="1.8"
            />
          </svg>
          <span className="text-[8px] font-mono text-red-400 mt-1 font-semibold tracking-wide">
            FUD BUILDER v3.1
          </span>
        </div>
      );

    case 'crypto':
      return (
        <div className="w-full h-full flex items-center justify-center space-x-2 bg-gradient-to-tr from-[#161206] to-[#2b210c]">
          <div className="w-8 h-8 rounded-full bg-amber-500/20 border border-amber-500/80 flex items-center justify-center font-bold text-amber-400 text-xs shadow-inner">
            ₿
          </div>
          <span className="text-gray-400 font-mono text-xs">↔</span>
          <div className="w-8 h-8 rounded-full bg-orange-600/20 border border-orange-500/80 flex items-center justify-center font-bold text-orange-400 text-xs shadow-inner">
            ɱ
          </div>
        </div>
      );

    case 'rdp':
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-tr from-[#05141e] to-[#0c2438]">
          <div className="space-y-1.5 w-16">
            <div className="h-3 bg-blue-950 border border-blue-400/40 rounded-xs flex items-center justify-between px-1 shadow-sm">
              <span className="w-1 h-1 rounded-full bg-blue-400 animate-pulse"></span>
              <span className="w-1 h-1 rounded-full bg-emerald-400"></span>
            </div>
            <div className="h-3 bg-blue-950 border border-blue-400/40 rounded-xs flex items-center justify-between px-1 shadow-sm">
              <span className="w-1 h-1 rounded-full bg-blue-400"></span>
              <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse"></span>
            </div>
            <div className="h-3 bg-blue-950 border border-blue-400/40 rounded-xs flex items-center justify-between px-1 shadow-sm">
              <span className="w-1 h-1 rounded-full bg-blue-400"></span>
              <span className="w-1 h-1 rounded-full bg-emerald-400"></span>
            </div>
          </div>
          <span className="text-[8px] font-mono text-blue-300 mt-1 font-semibold tracking-wide">
            DEDICATED RDP
          </span>
        </div>
      );

    case 'social':
      return (
        <div className="w-full h-full flex items-center justify-center space-x-1.5 bg-gradient-to-tr from-[#120a16] to-[#25102a]">
          <div className="w-6 h-6 rounded-md bg-pink-600/30 border border-pink-400/60 flex items-center justify-center text-[8px] font-bold text-pink-300 shadow-sm">
            IG
          </div>
          <div className="w-6 h-6 rounded-md bg-zinc-700/40 border border-gray-400/60 flex items-center justify-center text-[8px] font-bold text-gray-200 shadow-sm">
            𝕏
          </div>
          <div className="w-6 h-6 rounded-md bg-orange-600/30 border border-orange-400/60 flex items-center justify-center text-[8px] font-bold text-orange-300 shadow-sm">
            RD
          </div>
        </div>
      );

    default:
      return (
        <div className="w-full h-full flex items-center justify-center bg-[#061113] text-gray-500 font-mono text-xs">
          ENCRYPTED ASSET
        </div>
      );
  }
};
