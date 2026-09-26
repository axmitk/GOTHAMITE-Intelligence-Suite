import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { formatMiddleTruncate } from '../utils/formatters';

export interface MonoValueProps {
  value: string;
  truncateLength?: number;
  truncateMiddle?: boolean;
  copyable?: boolean;
  className?: string;
  title?: string;
}
/**
 * Reusable wrapper for raw data identifiers (UI_SPEC.md §3 & §6).
 * Ensures font-mono styling, readable truncation, and copy-to-clipboard functionality.
 */
export const MonoValue: React.FC<MonoValueProps> = ({
  value,
  truncateLength,
  truncateMiddle = false,
  copyable = true,
  className = '',
  title,
}) => {
  const [copied, setCopied] = useState(false);

  const displayValue = truncateLength
    ? truncateMiddle
      ? formatMiddleTruncate(value, truncateLength)
      : value.length > truncateLength
      ? `${value.slice(0, truncateLength)}...`
      : value
    : value;

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Fallback
      setCopied(false);
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono text-text-primary group ${className}`}
      title={title || value}
    >
      <span className="truncate">{displayValue}</span>
      {copyable && (
        <button
          type="button"
          onClick={handleCopy}
          aria-label="Copy identifier"
          className="text-text-tertiary hover:text-accent-cyan p-0.5 rounded transition-colors focus:outline-none"
          title={copied ? 'Copied!' : 'Copy to clipboard'}
        >
          {copied ? (
            <Check size={13} className="text-emerald-400" />
          ) : (
            <Copy size={13} className="opacity-60 group-hover:opacity-100" />
          )}
        </button>
      )}
    </span>
  );
};

export default MonoValue;
