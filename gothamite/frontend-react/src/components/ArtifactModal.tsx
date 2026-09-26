import React, { useEffect, useState } from 'react';
import { X, ShieldCheck, Copy, Check, ExternalLink } from 'lucide-react';
import { getArtifact } from '../api/client';
import type { Artifact } from '../types/api';
import { SourceBadge } from './SourceBadge';
import { MonoValue } from './MonoValue';

export interface ArtifactModalProps {
  artifactId: string | null;
  onClose: () => void;
}

/**
 * Immutable Artifact Viewer Modal (UI_SPEC.md §5, UX_SPEC.md §6, SECURITY.md §2).
 * Displays raw scraped artifact text with cryptographic hash and relay path.
 * Raw content is rendered verbatim as escaped plain text — NEVER rendered as HTML.
 */
export const ArtifactModal: React.FC<ArtifactModalProps> = ({ artifactId, onClose }) => {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!artifactId) {
      setArtifact(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    getArtifact(artifactId)
      .then((data) => {
        if (isMounted) {
          setArtifact(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('[GOTHAMITE] Error fetching artifact:', err);
          setError(`Unable to load artifact ${artifactId}`);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [artifactId]);

  if (!artifactId) return null;

  const handleCopyRaw = async () => {
    if (!artifact) return;
    try {
      await navigator.clipboard.writeText(artifact.raw_content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="bg-surface border border-border rounded-lg shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-surface-raised">
          <div className="flex items-center gap-2.5">
            <ShieldCheck size={18} className="text-emerald-400" />
            <span className="font-display font-semibold text-sm text-text-primary">
              Evidence Locker · Immutable Artifact
            </span>
            {artifact && <SourceBadge source={artifact.source_id} size="sm" />}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-tertiary hover:text-text-primary p-1 rounded hover:bg-surface transition-colors"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto flex-1 space-y-4">
          {loading && (
            <div className="space-y-3 animate-pulse py-8">
              <div className="h-4 bg-surface-raised rounded w-3/4" />
              <div className="h-4 bg-surface-raised rounded w-1/2" />
              <div className="h-32 bg-surface-raised rounded w-full" />
            </div>
          )}

          {error && (
            <div className="p-4 rounded bg-red-950/40 border border-red-800/60 text-red-300 text-sm">
              {error}
            </div>
          )}

          {artifact && !loading && (
            <>
              {/* Provenance Metadata */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-base p-3.5 rounded border border-border">
                <div>
                  <span className="text-text-tertiary block mb-0.5">Artifact UUID</span>
                  <MonoValue value={artifact.artifact_id} className="text-xs" />
                </div>
                <div>
                  <span className="text-text-tertiary block mb-0.5">Collected At</span>
                  <span className="font-mono text-text-secondary">
                    {artifact.collected_at ? new Date(artifact.collected_at).toUTCString() : 'Unknown'}
                  </span>
                </div>
                <div className="md:col-span-2">
                  <span className="text-text-tertiary block mb-0.5">Onion Target URL</span>
                  <div className="flex items-center gap-1.5 font-mono text-xs text-accent-cyan">
                    <ExternalLink size={12} />
                    <span className="truncate">{artifact.url}</span>
                  </div>
                </div>
                <div className="md:col-span-2">
                  <span className="text-text-tertiary block mb-0.5">SHA-256 Content Hash (Cryptographic Integrity)</span>
                  <MonoValue
                    value={artifact.content_hash}
                    truncateLength={48}
                    truncateMiddle={true}
                    className="text-xs text-emerald-400"
                  />
                </div>
                {artifact.relay_path && artifact.relay_path.length > 0 && (
                  <div className="md:col-span-2">
                    <span className="text-text-tertiary block mb-0.5">Tor Relay Path (Audit Hop Chain)</span>
                    <span className="font-mono text-xs text-text-secondary">
                      {artifact.relay_path.join(' ➔ ')}
                    </span>
                  </div>
                )}
              </div>

              {/* Raw Content Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium uppercase tracking-wider text-text-tertiary">
                    Verbatim Raw Scraped Content (HTML Escaped)
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyRaw}
                    className="flex items-center gap-1 text-xs font-mono text-text-secondary hover:text-text-primary px-2 py-1 rounded bg-surface-raised border border-border transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check size={12} className="text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy size={12} />
                        <span>Copy Raw</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="font-mono text-xs text-text-secondary bg-base p-4 rounded border border-border overflow-x-auto whitespace-pre-wrap break-all max-h-72 select-text">
                  {artifact.raw_content}
                </pre>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-border bg-surface-raised flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded text-xs font-medium bg-surface border border-border text-text-secondary hover:text-text-primary hover:bg-base transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ArtifactModal;
