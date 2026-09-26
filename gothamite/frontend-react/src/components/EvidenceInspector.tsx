import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  RotateCcw,
  Info,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import type { EdgeDetails, GraphNode, RelationshipStatus } from '../types/api';
import { ScoreBadge } from './ScoreBadge';
import { StatusPill } from './StatusPill';
import { SourceBadge } from './SourceBadge';
import { EvidenceRow } from './EvidenceRow';

export interface EvidenceInspectorProps {
  selectedEdge: EdgeDetails | null;
  selectedNode: GraphNode | null;
  loadingEdge: boolean;
  updatingStatus: boolean;
  onUpdateStatus: (newStatus: RelationshipStatus) => Promise<void>;
  onViewArtifact: (artifactId: string) => void;
  onSelectEdgeById?: (edgeId: string) => void;
  className?: string;
}

export const EvidenceInspector: React.FC<EvidenceInspectorProps> = ({
  selectedEdge,
  selectedNode,
  loadingEdge,
  updatingStatus,
  onUpdateStatus,
  onViewArtifact,
  className = '',
}) => {
  const navigate = useNavigate();

  // 1. LOADING STATE
  if (loadingEdge) {
    return (
      <div className={`p-6 bg-surface border border-border rounded-lg h-full flex flex-col justify-center items-center text-text-tertiary space-y-3 ${className}`}>
        <Loader2 size={24} className="animate-spin text-accent-cyan" />
        <span className="text-xs font-mono">Retrieving evidence trail from API...</span>
      </div>
    );
  }

  // 2. EDGE SELECTED: RENDER COMPLETE EVIDENCE PROVENANCE (UI_SPEC.md §5)
  if (selectedEdge) {
    const isProposed = selectedEdge.status === 'proposed';
    const isConfirmed = selectedEdge.status === 'confirmed';
    const isRejected = selectedEdge.status === 'rejected';

    return (
      <div className={`p-5 bg-surface border border-border rounded-lg h-full flex flex-col overflow-y-auto space-y-5 ${className}`}>
        {/* Header: Link Pair & Type Badge */}
        <div className="space-y-2 border-b border-border pb-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-text-tertiary">
              Cross-Source Linkage
            </span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-base border border-border text-text-secondary">
              {selectedEdge.type}
            </span>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="flex items-center gap-1.5">
              <SourceBadge source={selectedEdge.from_persona.source_id} size="sm" />
              <button
                type="button"
                onClick={() => navigate(`/dossier/${selectedEdge.from_persona.persona_id}`)}
                className="font-mono text-base font-bold text-text-primary hover:text-accent-cyan transition-colors"
                title="View dossier"
              >
                {selectedEdge.from_persona.handle}
              </button>
            </div>
            <span className="text-text-tertiary font-mono">➔</span>
            <div className="flex items-center gap-1.5">
              <SourceBadge source={selectedEdge.to_persona.source_id} size="sm" />
              <button
                type="button"
                onClick={() => navigate(`/dossier/${selectedEdge.to_persona.persona_id}`)}
                className="font-mono text-base font-bold text-text-primary hover:text-accent-cyan transition-colors"
                title="View dossier"
              >
                {selectedEdge.to_persona.handle}
              </button>
            </div>
          </div>
        </div>

        {/* Confidence Score & Status Pill (SECURITY.md §5: NEVER PERCENTAGE) */}
        <div className="bg-base p-4 rounded-lg border border-border space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">
              Confidence Score
            </span>
            <StatusPill status={selectedEdge.status} size="sm" variant="pill" />
          </div>

          <div className="flex items-center justify-between">
            <ScoreBadge score={selectedEdge.score} size="lg" showLabel={true} />
            <span className="text-[11px] font-mono text-text-tertiary">
              {selectedEdge.evidence.length} Verifiable Signals
            </span>
          </div>
        </div>

        {/* Analyst Review Actions (UX_SPEC.md §10) */}
        <div className="space-y-2">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-text-tertiary">
            Attribution Decision
          </div>

          <div className="grid grid-cols-2 gap-2">
            {/* Confirm Button */}
            <button
              type="button"
              disabled={!isProposed || updatingStatus}
              onClick={() => onUpdateStatus('confirmed')}
              className={`flex items-center justify-center gap-1.5 px-3 py-2 rounded text-xs font-semibold transition-colors ${
                isConfirmed
                  ? 'bg-emerald-950/60 border border-emerald-700 text-emerald-300 opacity-90 cursor-default'
                  : isProposed
                  ? 'bg-emerald-900/40 hover:bg-emerald-800/60 border border-emerald-600 text-emerald-300 hover:text-white'
                  : 'bg-surface-raised border border-border text-text-tertiary opacity-40 cursor-not-allowed'
              }`}
              title={
                !isProposed
                  ? 'Relationship already reviewed. Use reset below to change status.'
                  : 'Confirm cross-source attribution'
              }
            >
              {updatingStatus ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <CheckCircle2 size={14} />
              )}
              <span>{isConfirmed ? 'Confirmed' : 'Confirm Link'}</span>
            </button>

            {/* Reject Button */}
            <button
              type="button"
              disabled={!isProposed || updatingStatus}
              onClick={() => onUpdateStatus('rejected')}
              className={`flex items-center justify-center gap-1.5 px-3 py-2 rounded text-xs font-semibold transition-colors ${
                isRejected
                  ? 'bg-red-950/60 border border-red-700 text-red-300 opacity-90 cursor-default'
                  : isProposed
                  ? 'bg-red-900/40 hover:bg-red-800/60 border border-red-600 text-red-300 hover:text-white'
                  : 'bg-surface-raised border border-border text-text-tertiary opacity-40 cursor-not-allowed'
              }`}
              title={
                !isProposed
                  ? 'Relationship already reviewed. Use reset below to change status.'
                  : 'Dismiss linkage as rejected'
              }
            >
              {updatingStatus ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <XCircle size={14} />
              )}
              <span>{isRejected ? 'Rejected' : 'Reject Link'}</span>
            </button>
          </div>

          {/* Reset to Proposed affordance for demonstration purposes (UX_SPEC.md §10) */}
          {!isProposed && (
            <button
              type="button"
              disabled={updatingStatus}
              onClick={() => onUpdateStatus('proposed')}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded text-[11px] font-mono text-text-tertiary hover:text-text-primary bg-base border border-border hover:bg-surface-raised transition-colors"
              title="Reset status back to proposed for demonstration testing"
            >
              <RotateCcw size={11} />
              <span>Reset State to Proposed (Demo Affordance)</span>
            </button>
          )}
        </div>

        {/* Complete Evidence List (SECURITY.md §4: NEVER SUMMARIZE OR SUPPRESS CONTRADICTIONS) */}
        <div className="space-y-2.5 flex-1">
          <div className="border-b border-border pb-1.5">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-text-tertiary">
              Cryptographic Evidence Trail
            </span>
          </div>

          <div className="space-y-2">
            {selectedEdge.evidence.map((ev) => (
              <EvidenceRow
                key={ev.evidence_id}
                evidence={ev}
                onViewArtifact={onViewArtifact}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // 3. NODE SELECTED: CHECK FOR DECOY EXPLANATION (UX_SPEC.md §7)
  if (selectedNode) {
    const isDecoy = selectedNode.handle.toLowerCase() === 'nightjarr';

    if (isDecoy) {
      return (
        <div className={`p-5 bg-surface border border-border rounded-lg h-full flex flex-col space-y-4 ${className}`}>
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h2 className="text-sm font-display font-bold text-text-primary">
              Adversarial Decoy Analysis
            </h2>
            <SourceBadge source={selectedNode.source_id} size="sm" />
          </div>

          {/* Core UX Moment: System Restraint Explained */}
          <div className="p-4 rounded-lg bg-amber-950/30 border border-amber-800/60 text-amber-200 text-xs space-y-2">
            <div className="flex items-center gap-2 font-semibold">
              <Info size={14} className="shrink-0" />
              <span>Attribution Restraint · Verified Decoy Node</span>
            </div>
            <p className="leading-relaxed text-[11px] text-amber-200/90">
              <strong>No relationship proposed.</strong> Nearest candidate:{' '}
              <span className="font-mono font-bold text-text-primary">nightjar</span> (forum-alpha).
              Handle similarity detected, but conflicting cryptographic keys and concurrent
              activity windows trigger active contradiction penalties.
            </p>
          </div>

          {/* Evaluated Signals Comparison */}
          <div className="space-y-2 text-xs">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-text-tertiary">
              Candidate Signal Evaluation
            </span>

            <div className="p-3 rounded bg-base border border-border space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-emerald-400 font-medium">
                  +0.15 handle_similarity
                </span>
                <span className="text-[10px] text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/50">
                  Supporting
                </span>
              </div>
              <p className="text-[11px] text-text-secondary">
                nightjar ≈ nightjarr (Levenshtein distance 1, typosquatting pattern)
              </p>
            </div>

            <div className="p-3 rounded bg-base border border-border space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-red-400 font-medium">
                  −0.30 identity_contradiction
                </span>
                <span className="text-[10px] text-red-400 bg-red-950/40 px-1.5 py-0.5 rounded border border-red-800/50">
                  Contradicting
                </span>
              </div>
              <p className="text-[11px] text-text-secondary">
                Conflicting PGP fingerprint (7D19F4... vs 9F2A4C...) and distinct Bitcoin wallet
                during overlapping activity window.
              </p>
            </div>

            <div className="p-3 rounded bg-base border border-border flex items-center justify-between">
              <span className="text-text-tertiary text-xs">Net Evaluated Score</span>
              <span className="font-mono font-bold text-gray-400">0.00 (&lt; 0.30 Floor)</span>
            </div>
          </div>

          <div className="pt-2 border-t border-border flex justify-end">
            <button
              type="button"
              onClick={() => navigate(`/dossier/${selectedNode.id}`)}
              className="flex items-center gap-1.5 text-xs text-accent-primary hover:text-accent-cyan font-mono"
            >
              <span>View nightjarr Dossier</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      );
    }

    // General Connected Node Details
    return (
      <div className={`p-5 bg-surface border border-border rounded-lg h-full flex flex-col space-y-4 ${className}`}>
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div>
            <span className="text-[10px] uppercase font-semibold text-text-tertiary block">
              Observed Persona
            </span>
            <h3 className="text-base font-mono font-bold text-text-primary">
              {selectedNode.handle}
            </h3>
          </div>
          <SourceBadge source={selectedNode.source_id} size="md" />
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs bg-base p-3.5 rounded border border-border">
          <div>
            <span className="text-text-tertiary block text-[10px] uppercase">First Observed</span>
            <span className="font-mono text-text-secondary text-[11px]">
              {selectedNode.first_seen ? new Date(selectedNode.first_seen).toLocaleDateString() : 'Unknown'}
            </span>
          </div>
          <div>
            <span className="text-text-tertiary block text-[10px] uppercase">Last Activity</span>
            <span className="font-mono text-text-secondary text-[11px]">
              {selectedNode.last_seen ? new Date(selectedNode.last_seen).toLocaleDateString() : 'Unknown'}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-text-tertiary block text-[10px] uppercase">Recorded Posts</span>
            <span className="font-mono text-text-primary text-sm font-bold">
              {selectedNode.post_count} posts & listings
            </span>
          </div>
        </div>

        <div className="p-3 bg-surface-raised rounded border border-border text-xs text-text-secondary leading-relaxed">
          Select any connected link in the graph canvas to inspect complete cryptographic provenance and signal weights.
        </div>

        <div className="pt-2 border-t border-border flex justify-end mt-auto">
          <button
            type="button"
            onClick={() => navigate(`/dossier/${selectedNode.id}`)}
            className="flex items-center gap-1.5 text-xs text-accent-primary hover:text-accent-cyan font-mono"
          >
            <span>Open Complete Actor Dossier</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>
    );
  }

  // 4. DEFAULT EMPTY STATE (UX_CORRECTION.md §7)
  return (
    <div className={`p-8 bg-surface border border-border rounded-lg h-full flex flex-col items-center justify-center text-center space-y-2 text-text-tertiary ${className}`}>
      <h3 className="text-sm font-semibold text-text-primary">
        Evidence Inspector
      </h3>
      <p className="text-xs text-text-secondary">
        Select a link or persona in the graph to inspect evidence and signals.
      </p>
    </div>
  );
};

export default EvidenceInspector;
