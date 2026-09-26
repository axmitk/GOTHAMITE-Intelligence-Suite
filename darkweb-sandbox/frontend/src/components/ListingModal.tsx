import React, { useState, useEffect } from 'react';
import { X, ShieldCheck, Check, Copy, AlertCircle, ShoppingCart, User, MessageSquare, AlertTriangle, Key } from 'lucide-react';
import { ListingItem } from '../types';
import { ListingGraphic } from './ListingGraphic';
import { fetchSandboxPage, parseItemPage } from '../services/sandboxGateway';

interface ListingModalProps {
  listing: ListingItem | null;
  onClose: () => void;
}

export const ListingModal: React.FC<ListingModalProps> = ({ listing, onClose }) => {
  const [activeTab, setActiveTab] = useState<'details' | 'pgp' | 'vendor'>('details');
  const [realDesc, setRealDesc] = useState('');
  const [realPgp, setRealPgp] = useState('');
  const [copied, setCopied] = useState(false);
  const [escrowStatus, setEscrowStatus] = useState<'idle' | 'processing' | 'completed'>('idle');

  useEffect(() => {
    if (listing && (listing as any).rawHref) {
      const href = (listing as any).rawHref;
      fetchSandboxPage(href.startsWith('/') ? href.substring(1) : href).then(({html}) => {
        const { body, pgp } = parseItemPage(html);
        setRealDesc(body);
        setRealPgp(pgp);
      });
    } else {
      setRealDesc(listing?.description || '');
      setRealPgp(listing?.pgpSignature || '');
    }
  }, [listing]);

  if (!listing) return null;

  const handleCopyPGP = () => {
    navigator.clipboard.writeText(realPgp || listing.pgpSignature);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSimulateBuy = () => {
    setEscrowStatus('processing');
    setTimeout(() => {
      setEscrowStatus('completed');
    }, 1200);
  };

  return (
    <div
      id="listing-modal"
      className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-[#0a1617] border border-[#1d4a46] rounded-lg max-w-lg w-full p-5 shadow-2xl font-mono relative space-y-4 text-gray-200 animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Top Bar */}
        <div className="flex items-start justify-between border-b border-[#153634] pb-3">
          <div>
            <span
              id="modal-category"
              className="text-[10px] text-[#2bf0a6] bg-emerald-950 px-2 py-0.5 rounded border border-[#2bf0a6]/30 font-semibold uppercase tracking-wider"
            >
              {listing.category}
            </span>
            <h3 id="modal-title" className="text-base font-bold text-white mt-1">
              {listing.title}
            </h3>
            <p className="text-xs text-gray-400">
              Vendor: <span id="modal-vendor" className="text-[#2bf0a6]">@{listing.vendor}</span> • ★{' '}
              {listing.rating} ({listing.ratingCount} deals)
            </p>
          </div>
          <button
            id="modal-close-btn"
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body Content */}
        <div className="space-y-3 text-xs">
          <div className="flex justify-between items-baseline bg-[#0d1f20] p-2.5 rounded border border-[#153634]">
            <span className="text-gray-400">Synthetic Escrow Price:</span>
            <div className="flex items-baseline space-x-2">
              <span id="modal-price" className="text-lg font-bold text-[#2bf0a6]">
                ${listing.price}
              </span>
              <span className="text-[10px] text-gray-500">≈ {(listing.price / 62000).toFixed(4)} BTC</span>
            </div>
          </div>

          <div className="space-y-1 text-gray-300">
            <div className="text-[10px] uppercase font-bold text-gray-400 mb-1">
              Item Description
            </div>
            <p id="modal-desc" className="text-gray-300 text-[11px] leading-relaxed whitespace-pre-wrap">
              {realDesc}
            </p>
          </div>

          {/* Technical Specs if available */}
          {listing.specs && listing.specs.length > 0 && (
            <div className="space-y-2 pt-2">
              <h4 className="font-bold text-[#2bf0a6] uppercase tracking-wider text-[11px]">
                Technical Specifications
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {listing.specs.map((spec, idx) => (
                  <div
                    key={idx}
                    className="p-2 bg-[#0d1f20] border border-[#153634] rounded flex flex-col"
                  >
                    <span className="text-[9px] text-gray-500 uppercase">{spec.label}</span>
                    <span className="text-xs text-gray-200">{spec.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* PGP Signature Panel */}
          <div className="pb-2">
            <div className="p-3 bg-[#050c0d] border border-[#1d4a46] rounded-lg space-y-2 font-mono">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-[#2bf0a6]" />
                  <span className="text-[11px] font-bold text-gray-300 uppercase tracking-wider">
                    Vendor PGP Signature Verification
                  </span>
                </div>
                <button
                  onClick={handleCopyPGP}
                  className="text-[10px] text-gray-400 hover:text-white flex items-center gap-1 transition cursor-pointer"
                >
                  {copied ? <Check className="w-3 h-3 text-[#2bf0a6]" /> : <Copy className="w-3 h-3" />}
                  {copied ? 'Copied' : 'Copy Block'}
                </button>
              </div>
              <pre className="text-[9px] text-emerald-400/80 bg-black/80 p-2 rounded border border-[#153634] overflow-x-auto">
                {realPgp}
              </pre>
            </div>
          </div>

          {/* Escrow simulation feedback */}
          {escrowStatus === 'processing' && (
            <div className="p-2.5 bg-cyan-950/40 border border-cyan-500/40 rounded text-cyan-300 text-[11px] flex items-center gap-2">
              <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin shrink-0" />
              <span>Generating 2-of-3 multisig synthetic escrow address...</span>
            </div>
          )}

          {escrowStatus === 'completed' && (
            <div className="p-2.5 bg-emerald-950/60 border border-emerald-500/50 rounded text-emerald-300 text-[11px] space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <Check className="w-4 h-4 text-[#2bf0a6]" />
                Simulated Escrow Order Placed #ORD-98214
              </div>
              <p className="text-[10px] text-gray-400">
                Synthetic funds locked in timelocked sandbox escrow. Vendor notified via onion telemetry.
              </p>
            </div>
          )}

          {/* Academic Disclaimer */}
          <div className="p-2.5 rounded bg-emerald-950/40 border border-[#2bf0a6]/30 text-[10px] text-emerald-300 flex items-start gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-[#2bf0a6]" />
            <div>
              <span className="font-bold">SIMULATED CYBERSECURITY DEMONSTRATION:</span> This item is
              non-functional and serves solely for threat analysis and educational UI training.
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="pt-2 flex justify-end space-x-2 border-t border-[#153634]">
          <button
            id="modal-dismiss-btn"
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-[#0d1f20] text-gray-300 hover:text-white hover:bg-[#112929] border border-[#1d4a46] text-xs transition cursor-pointer"
          >
            Close
          </button>
          {escrowStatus !== 'completed' && (
            <button
              onClick={handleSimulateBuy}
              disabled={escrowStatus === 'processing'}
              className="px-4 py-1.5 rounded bg-[#2bf0a6] hover:bg-emerald-400 text-black font-bold text-xs transition flex items-center gap-1.5 shadow-[0_0_12px_rgba(43,240,166,0.2)] cursor-pointer"
            >
              <ShoppingCart className="w-3.5 h-3.5" />
              Buy via Escrow
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
