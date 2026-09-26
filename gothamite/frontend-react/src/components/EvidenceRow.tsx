import React from 'react';
import { ExternalLink, FileText } from 'lucide-react';
import type { Evidence } from '../types/api';
import { MonoValue } from './MonoValue';

export interface EvidenceRowProps {
  evidence: Evidence;
  onViewArtifact?: (artifactId: string) => void;
  className?: string;
}

/**
 * Reusable EvidenceRow component per UI_SPEC.md §5 & §6 and SECURITY.md §4.
 * Displays:
 * - Direction indicator dot (Green: supporting, Red: contradicting)
 * - Signal name in monospace
 * - Explicit signed weight (+0.70, -0.30)
 * - Human-readable observation note
 * - Clickable source artifact reference
 */
export const EvidenceRow: React.FC<EvidenceRowProps> = ({
  evidence,
  onViewArtifact,
  className = '',
}) => {
  const isSupporting = evidence.direction === 'supporting';
  const dotColorClass = isSupporting ? 'bg-emerald-500' : 'bg-red-500';
  const weightColorClass = isSupporting ? 'text-emerald-400' : 'text-red-400';

  // Format weight with explicit sign (+0.70 or -0.30)
  const formattedWeight =
    evidence.weight >= 0
      ? `+${evidence.weight.toFixed(2)}`
      : evidence.weight.toFixed(2);

  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-md bg-surface border border-border/70 hover:border-border hover:bg-surface-raised/40 transition-colors gap-2 text-xs ${className}`}
    >
      {/* Left: Indicator, Signal Name, Note */}
      <div className="flex items-start gap-2.5 flex-1 min-w-0">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 mt-1 ${dotColorClass}`}
          title={isSupporting ? 'Supporting Evidence' : 'Contradicting Evidence'}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-semibold text-text-primary text-[13px]">
              {evidence.signal_type}
            </span>
            <span
              className={`font-mono font-bold px-1.5 py-0.2 rounded text-[11px] bg-base border border-border ${weightColorClass}`}
            >
              {formattedWeight}
            </span>
          </div>
          <p className="text-text-secondary mt-0.5 text-xs leading-relaxed">
            {evidence.note}
          </p>
        </div>
      </div>

      {/* Right: Artifact Reference */}
      <div className="flex items-center gap-2 shrink-0 self-end sm:self-center pl-5 sm:pl-2">
        <div className="flex items-center gap-1.5 bg-base/80 border border-border px-2 py-1 rounded text-text-tertiary">
          <FileText size={12} />
          <MonoValue
            value={evidence.artifact_id}
            truncateLength={10}
            truncateMiddle={true}
            copyable={false}
            className="text-[11px] text-text-secondary"
            title={`Artifact ID: ${evidence.artifact_id}`}
          />
        </div>

        {onViewArtifact && (
          <button
            type="button"
            onClick={() => onViewArtifact(evidence.artifact_id)}
            className="flex items-center gap-1 px-2 py-1 rounded bg-surface-raised border border-border hover:border-accent-primary hover:text-accent-primary text-text-secondary text-[11px] transition-colors focus:outline-none"
            title="Inspect raw immutable artifact in evidence locker"
          >
            <span>View</span>
            <ExternalLink size={11} />
          </button>
        )}
      </div>
    </div>
  );
};

export default EvidenceRow;
