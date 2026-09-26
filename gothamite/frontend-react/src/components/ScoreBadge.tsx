import React from 'react';
import { getScoreBand } from '../utils/formatters';
import type { ScoreBand, ScoreBandInfo } from '../utils/formatters';

export type { ScoreBand, ScoreBandInfo };


export interface ScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

/**
 * Single source of truth for confidence score rendering across GOTHAMITE.
 * STRICT RULE (SECURITY.md §5): Scores are arithmetic evidentiary sums,
 * NEVER percentages. Always displays decimal representation.
 */
export const ScoreBadge: React.FC<ScoreBadgeProps> = ({
  score,
  size = 'md',
  showLabel = true,
  className = '',
}) => {
  const bandInfo = getScoreBand(score);
  const formattedScore = score.toFixed(2);

  const sizeStyles = {
    sm: {
      container: 'px-2 py-0.5 text-xs gap-1.5',
      score: 'text-xs font-mono font-bold',
      label: 'text-[10px] tracking-wide uppercase',
    },
    md: {
      container: 'px-2.5 py-1 text-sm gap-2',
      score: 'text-sm font-mono font-bold',
      label: 'text-xs tracking-wide uppercase font-medium',
    },
    lg: {
      container: 'px-3.5 py-1.5 text-base gap-2.5',
      score: 'text-lg font-mono font-bold',
      label: 'text-sm tracking-wider uppercase font-semibold',
    },
  }[size];

  return (
    <div
      className={`inline-flex items-center rounded border ${bandInfo.bgClass} ${bandInfo.borderClass} ${bandInfo.colorClass} ${sizeStyles.container} ${className}`}
      title={`Confidence Score: ${formattedScore} (${bandInfo.label})`}
    >
      <span className={sizeStyles.score}>{formattedScore}</span>
      {showLabel && (
        <span className={`text-text-tertiary border-l border-border/80 pl-2 ${sizeStyles.label}`}>
          {bandInfo.label}
        </span>
      )}
    </div>
  );
};

export default ScoreBadge;
