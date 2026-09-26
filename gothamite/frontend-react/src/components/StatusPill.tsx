import React from 'react';
import type { RelationshipStatus } from '../types/api';

export interface StatusPillProps {
  status: RelationshipStatus;
  variant?: 'dot' | 'pill';
  size?: 'sm' | 'md';
  className?: string;
}

/**
 * Renders relationship review status (proposed, confirmed, rejected).
 * By default renders as a restrained colored dot + plain text (UI_CORRECTION.md §3.2).
 * In full detail views (Evidence Inspector), can render as pill container.
 */
export const StatusPill: React.FC<StatusPillProps> = ({
  status,
  variant = 'dot',
  size = 'md',
  className = '',
}) => {
  const config = {
    proposed: {
      label: 'PROPOSED',
      text: 'proposed',
      style: 'text-amber-400 bg-amber-950/40 border-amber-800/60',
      dot: 'bg-amber-400',
      dotText: 'text-amber-400/90',
    },
    confirmed: {
      label: 'CONFIRMED',
      text: 'confirmed',
      style: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/60',
      dot: 'bg-emerald-400',
      dotText: 'text-emerald-400/90',
    },
    rejected: {
      label: 'REJECTED',
      text: 'rejected',
      style: 'text-gray-400 bg-gray-900/60 border-gray-700/60',
      dot: 'bg-gray-500',
      dotText: 'text-gray-400',
    },
  }[status] || {
    label: status.toUpperCase(),
    text: status,
    style: 'text-gray-400 bg-gray-900/60 border-gray-700/60',
    dot: 'bg-gray-500',
    dotText: 'text-gray-400',
  };

  if (variant === 'dot') {
    return (
      <span className={`inline-flex items-center gap-1.5 font-mono text-xs ${config.dotText} ${className}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
        <span>{config.text}</span>
      </span>
    );
  }

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-0.5 text-xs',
  }[size];

  return (
    <span
      className={`inline-flex items-center justify-center font-mono font-medium uppercase tracking-wider rounded-full border ${config.style} ${sizeStyles} ${className}`}
    >
      {config.label}
    </span>
  );
};

export default StatusPill;

