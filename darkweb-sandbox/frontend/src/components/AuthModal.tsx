import React, { useState } from 'react';
import { X, Key, Shield, Check, Lock } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  mode: 'login' | 'register';
  onClose: () => void;
  onSuccess: (username: string) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, mode, onClose, onSuccess }) => {
  const [username, setUsername] = useState('');
  const [pin, setPin] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [authSuccess, setAuthSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      setAuthSuccess(true);
      setTimeout(() => {
        onSuccess(username || 'sandbox_operator');
        setAuthSuccess(false);
        onClose();
      }, 1000);
    }, 1200);
  };

  return (
    <div
      className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-center justify-center p-4 font-mono text-gray-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-[#0a1617] border border-[#1d4a46] rounded-lg max-w-md w-full p-5 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-[#153634] pb-3">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded bg-emerald-950/70 border border-[#2bf0a6]/40 text-[#2bf0a6]">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                {mode === 'login' ? 'PGP Challenge Authentication' : 'Create Sandbox Account'}
              </h3>
              <p className="text-[10px] text-gray-400">Zero-knowledge proof validation</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {authSuccess ? (
          <div className="p-4 bg-emerald-950/60 border border-emerald-500/50 rounded text-center space-y-2">
            <Check className="w-8 h-8 text-[#2bf0a6] mx-auto" />
            <div className="text-sm font-bold text-emerald-300">PGP Nonce Signature Verified!</div>
            <p className="text-xs text-gray-400">Authenticated as {username || 'sandbox_operator'}</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3 text-xs">
            <div className="space-y-1">
              <label className="text-gray-400 text-[11px]">Pseudonym / Handle</label>
              <input
                type="text"
                required
                placeholder="e.g. specter_0x"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-[#040c0d] border border-[#1d4a46] rounded px-3 py-2 text-white text-xs focus:border-[#2bf0a6] focus:outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-gray-400 text-[11px]">
                {mode === 'login' ? 'Synthetic Master Passphrase / PIN' : 'Synthetic 6-Digit PIN (Withdrawal)'}
              </label>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                className="w-full bg-[#040c0d] border border-[#1d4a46] rounded px-3 py-2 text-white text-xs focus:border-[#2bf0a6] focus:outline-none"
              />
            </div>

            <div className="p-2.5 bg-black/60 rounded border border-[#153634] text-[10px] text-gray-400 space-y-1">
              <div className="text-[#2bf0a6] font-semibold flex items-center gap-1">
                <Shield className="w-3 h-3" />
                <span>Simulated Security Model</span>
              </div>
              <p>
                No plain passwords are ever saved. Authentic marketplace nodes decrypt challenge tokens locally using PGP public keyring vectors.
              </p>
            </div>

            <div className="pt-2 flex justify-end space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 rounded bg-[#0d1f20] text-gray-400 hover:text-white border border-[#153634]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isProcessing}
                className="px-4 py-1.5 rounded bg-[#2bf0a6] hover:bg-emerald-400 text-black font-bold flex items-center gap-1.5"
              >
                {isProcessing ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                    <span>Verifying PGP...</span>
                  </>
                ) : (
                  <>
                    <Lock className="w-3.5 h-3.5" />
                    <span>{mode === 'login' ? 'Authenticate' : 'Create Identity'}</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
