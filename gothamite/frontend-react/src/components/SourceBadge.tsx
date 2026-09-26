import React from 'react';
import { getSourceColor } from '../utils/formatters';

export interface SourceBadgeProps {
  source: string;
  showDot?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}
/**
 * Renders consistent source color dot and label across GOTHAMITE (UI_SPEC.md §6).
 */
export const SourceBadge: React.FC<SourceBadgeProps> = ({
  source,
  showDot = true,
  size = 'md',
  className = '',
}) => {
  const colors = getSourceColor(source);

  const sizeStyles = {
    sm: {
      gap: 'gap-1.5 text-xs',
      dot: 'w-1.5 h-1.5',
    },
    md: {
      gap: 'gap-2 text-xs',
      dot: 'w-2 h-2',
    },
  }[size];

  return (
    <span
      className={`inline-flex items-center font-mono ${colors.text} ${sizeStyles.gap} ${className}`}
    >
      {showDot && <span className={`rounded-full shrink-0 ${colors.dot} ${sizeStyles.dot}`} />}
      <span>{source}</span>
    </span>
  );
};

export default SourceBadge;

