import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Filter,
  ArrowRight,
} from 'lucide-react';
import { getGraph, getPersonaDossier } from '../api/client';
import type { GraphNode, PersonaDossier } from '../types/api';
import { SourceBadge, ArtifactModal } from '../components';

interface TimelinePersona extends GraphNode {
  startDate: Date;
  endDate: Date;
}

interface TimelineObservationEvent {
  id: string;
  persona_id: string;
  handle: string;
  source_id: string;
  observed_at: string;
  type: string;
  value: string;
  artifact_id: string;
  url?: string;
}

export const Timeline: React.FC = () => {
  const navigate = useNavigate();

  // Data states
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [dossiers, setDossiers] = useState<PersonaDossier[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Interaction states
  const [hoveredHandle, setHoveredHandle] = useState<string | null>(null);
  const [inspectArtifactId, setInspectArtifactId] = useState<string | null>(null);

  // Stream filter states
  const [selectedPersonaFilter, setSelectedPersonaFilter] = useState<string>('all');
  const [selectedSourceFilter, setSelectedSourceFilter] = useState<string>('all');

  // Load graph and dossiers
  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    getGraph()
      .then(async (graph) => {
        if (!isMounted) return;
        setNodes(graph.nodes);

        // Fetch dossiers in parallel for rich observation stream
        const dossierList = await Promise.all(
          graph.nodes.map((n) =>
            getPersonaDossier(n.id).catch((err) => {
              console.warn(`Failed loading dossier for ${n.handle}:`, err);
              return null as unknown as PersonaDossier;
            })
          )
        );

        if (isMounted) {
          setDossiers(dossierList.filter(Boolean));
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('[Timeline] Failed loading data:', err);
          setErrorBanner('Cannot reach GOTHAMITE backend. Ensure Docker backend is running.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Timeline boundaries (Fixed 2026 activity window: Jan 1, 2026 to Sep 1, 2026)
  const timeBounds = useMemo(() => {
    const minTime = new Date('2026-01-01T00:00:00Z').getTime();
    const maxTime = new Date('2026-09-01T00:00:00Z').getTime();
    return { minTime, maxTime, totalMs: maxTime - minTime };
  }, []);

  // Ordered personas so quillfeather and quill_v2 are adjacent lanes
  const orderedPersonas: TimelinePersona[] = useMemo(() => {
    // Custom sort order to highlight the quill migration juxtaposition (UI_SPEC.md §5)
    const lanePriority = [
      'nightjar',
      'n1ghtjar_',
      'quillfeather',
      'quill_v2',
      'nightjarr',
      'bellwether',
    ];

    const sorted = [...nodes].sort((a, b) => {
      const idxA = lanePriority.indexOf(a.handle);
      const idxB = lanePriority.indexOf(b.handle);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      return a.handle.localeCompare(b.handle);
    });

    return sorted.map((n) => ({
      ...n,
      startDate: n.first_seen ? new Date(n.first_seen) : new Date('2026-01-01'),
      endDate: n.last_seen ? new Date(n.last_seen) : new Date('2026-08-31'),
    }));
  }, [nodes]);

  // Aggregate chronological observation events from dossiers
  const observationEvents: TimelineObservationEvent[] = useMemo(() => {
    const events: TimelineObservationEvent[] = [];

    dossiers.forEach((d) => {
      d.identifiers?.forEach((i) => {
        events.push({
          id: i.identifier_id,
          persona_id: d.persona_id,
          handle: d.handle,
          source_id: d.source_id,
          observed_at: i.observed_at || '2026-01-01',
          type: i.type,
          value: i.value,
          artifact_id: i.artifact_id,
        });
      });

      d.timeline?.forEach((t, idx) => {
        events.push({
          id: `${t.artifact_id}-${idx}`,
          persona_id: d.persona_id,
          handle: d.handle,
          source_id: d.source_id,
          observed_at: t.collected_at || '2026-01-01',
          type: 'scraped_post',
          value: t.snippet.slice(0, 140) + '...',
          artifact_id: t.artifact_id,
          url: t.url,
        });
      });
    });

    // Sort ascending by observation timestamp
    return events.sort(
      (a, b) => new Date(a.observed_at).getTime() - new Date(b.observed_at).getTime()
    );
  }, [dossiers]);

  // Filtered observation stream
  const filteredEvents = useMemo(() => {
    return observationEvents.filter((ev) => {
      if (selectedPersonaFilter !== 'all' && ev.handle !== selectedPersonaFilter) return false;
      if (selectedSourceFilter !== 'all' && ev.source_id !== selectedSourceFilter) return false;
      return true;
    });
  }, [observationEvents, selectedPersonaFilter, selectedSourceFilter]);

  // Percentage position calculator on horizontal axis
  const getXPercent = (date: Date) => {
    const t = date.getTime();
    const clamped = Math.max(timeBounds.minTime, Math.min(timeBounds.maxTime, t));
    return ((clamped - timeBounds.minTime) / timeBounds.totalMs) * 100;
  };

  // Month markers for timeline axis
  const months = [
    { label: 'Jan 2026', date: new Date('2026-01-01') },
    { label: 'Feb 2026', date: new Date('2026-02-01') },
    { label: 'Mar 2026', date: new Date('2026-03-01') },
    { label: 'Apr 2026', date: new Date('2026-04-01') },
    { label: 'May 2026', date: new Date('2026-05-01') },
    { label: 'Jun 2026', date: new Date('2026-06-01') },
    { label: 'Jul 2026', date: new Date('2026-07-01') },
    { label: 'Aug 2026', date: new Date('2026-08-01') },
  ];

  // Specific migration dates for quillfeather ➔ quill_v2 visual marker (UI_SPEC.md §5)
  const quillEndPercent = getXPercent(new Date('2026-04-02T19:00:00Z'));
  const quillV2StartPercent = getXPercent(new Date('2026-04-19T14:00:00Z'));

  const isQuillHovered = hoveredHandle === 'quillfeather' || hoveredHandle === 'quill_v2';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header (UI_CORRECTION.md §3.1, UX_CORRECTION.md §2) */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-xl font-display font-bold text-text-primary tracking-wide">
            Timeline
          </h1>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-text-tertiary">
          <span>Observed Window:</span>
          <span className="text-text-primary font-semibold">Jan 2026 – Aug 2026</span>
        </div>
      </div>

      {/* Spotlight Callout Banner: The Quillfeather ➔ Quill_v2 Handoff (Approved Exception: UI_CORRECTION.md §3.6) */}
      <div
        className={`p-4 rounded-lg border transition-all duration-200 ${
          isQuillHovered
            ? 'bg-blue-950/50 border-blue-500/80 shadow-lg shadow-blue-500/10'
            : 'bg-surface border-border'
        }`}
      >
        <div className="flex items-start gap-3 text-xs">
          <Sparkles size={18} className="text-accent-cyan shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-text-primary">
                Rebrand Migration Spotlight:
              </span>
              <span className="font-mono text-accent-cyan">
                quillfeather ➔ quill_v2 (17-day succession gap)
              </span>
            </div>
            <p className="text-text-secondary leading-relaxed text-[11px]">
              <strong className="text-text-primary font-mono">quillfeather</strong> activity ceases abruptly on{' '}
              <span className="font-mono text-amber-400">2026-04-02</span> on <em>forum-alpha</em>. Exactly 17 days later,{' '}
              <strong className="text-text-primary font-mono">quill_v2</strong> surfaces on{' '}
              <span className="font-mono text-emerald-400">2026-04-19</span> on <em>forum-gamma</em> using the identical Bitcoin wallet (
              <span className="font-mono text-text-primary">1Kp7dR3z...</span>). The system attributes this transition at{' '}
              <strong className="text-text-primary font-mono">0.60 confidence</strong> via deterministic temporal succession.
            </p>
          </div>
        </div>
      </div>

      {/* Error Fallback Banner */}
      {errorBanner && (
        <div className="p-4 rounded-lg bg-red-950/40 border border-red-800/60 text-red-300 text-xs">
          {errorBanner}
        </div>
      )}

      {/* 1. Interactive 6-Lane Gantt Chart (UI_SPEC.md §5, UX_SPEC.md §9) */}
      <div className="p-5 rounded-lg bg-surface border border-border space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <span className="text-xs uppercase font-semibold text-text-tertiary tracking-wider font-mono">
            Cross-Source Activity Windows (6 Lanes)
          </span>
          <span className="text-[11px] font-mono text-text-tertiary">
            Hover to inspect window · Click bar to open Dossier
          </span>
        </div>

        {loading ? (
          <div className="h-72 flex items-center justify-center text-xs font-mono text-text-tertiary animate-pulse">
            Calculating temporal spans...
          </div>
        ) : (
          <div className="space-y-6 pt-2 select-none">
            {/* Horizontal Timeline Container */}
            <div className="relative">
              {/* Vertical Month Grid Lines */}
              <div className="absolute inset-0 flex justify-between pointer-events-none opacity-20">
                {months.map((m) => (
                  <div key={m.label} className="border-l border-border h-full flex flex-col justify-end">
                    <span className="text-[9px] font-mono text-text-tertiary transform -translate-x-1/2 translate-y-6">
                      {m.label.slice(0, 3)}
                    </span>
                  </div>
                ))}
              </div>

              {/* Visual Gap Highlight Marker for Quill Succession (UI_SPEC.md §5) */}
              <div
                className={`absolute top-0 bottom-0 pointer-events-none transition-opacity duration-200 border-x border-dashed ${
                  isQuillHovered
                    ? 'bg-blue-500/10 border-accent-cyan opacity-100'
                    : 'bg-amber-500/5 border-amber-500/40 opacity-70'
                }`}
                style={{
                  left: `${quillEndPercent}%`,
                  width: `${quillV2StartPercent - quillEndPercent}%`,
                }}
              >
                <div className="absolute -top-5 left-1/2 transform -translate-x-1/2 whitespace-nowrap text-[10px] font-mono font-semibold text-amber-400 bg-base px-1.5 py-0.5 rounded border border-amber-800/60 shadow">
                  17-Day Gap
                </div>
              </div>

              {/* 6 Persona Lanes */}
              <div className="space-y-3 relative z-10 py-2">
                {orderedPersonas.map((persona) => {
                  const leftPercent = getXPercent(persona.startDate);
                  const rightPercent = getXPercent(persona.endDate);
                  const barWidth = Math.max(rightPercent - leftPercent, 2);

                  const isQuill = persona.handle === 'quillfeather' || persona.handle === 'quill_v2';
                  const isHighlighted =
                    hoveredHandle === persona.handle || (isQuill && isQuillHovered);

                  // Source color mapping
                  const sourceBarColor = {
                    'forum-alpha': 'bg-[#3498db] border-[#5dade2]',
                    'marketplace-beta': 'bg-[#e67e22] border-[#f39c12]',
                    'forum-gamma': 'bg-[#2ecc71] border-[#58d68d]',
                  }[persona.source_id] || 'bg-gray-500 border-gray-400';

                  return (
                    <div
                      key={persona.id}
                      className="flex items-center gap-3 h-9 group"
                      onMouseEnter={() => setHoveredHandle(persona.handle)}
                      onMouseLeave={() => setHoveredHandle(null)}
                    >
                      {/* Left Y-Axis Label: Persona Handle & Source */}
                      <div className="w-40 shrink-0 flex items-center justify-between pr-2 border-r border-border">
                        <button
                          type="button"
                          onClick={() => navigate(`/dossier/${persona.id}`)}
                          className="font-mono text-xs font-semibold text-text-primary hover:text-accent-cyan transition-colors truncate"
                          title="Open persona dossier"
                        >
                          {persona.handle}
                        </button>
                        <SourceBadge source={persona.source_id} size="sm" showDot={false} />
                      </div>

                      {/* Lane Bar Track */}
                      <div className="flex-1 relative h-7 bg-base/40 rounded border border-border/40 overflow-visible">
                        {/* Interactive Activity Bar */}
                        <div
                          onClick={() => navigate(`/dossier/${persona.id}`)}
                          style={{
                            left: `${leftPercent}%`,
                            width: `${barWidth}%`,
                          }}
                          className={`absolute top-1 bottom-1 rounded cursor-pointer transition-all duration-150 border ${sourceBarColor} flex items-center px-2 shadow-sm ${
                            isHighlighted
                              ? 'ring-2 ring-accent-cyan opacity-100 scale-y-105 z-20'
                              : 'opacity-85 hover:opacity-100'
                          }`}
                          title={`${persona.handle} (${persona.source_id}): ${persona.startDate.toISOString().slice(0, 10)} to ${persona.endDate.toISOString().slice(0, 10)} (${persona.post_count} posts)`}
                        >
                          <span className="font-mono text-[10px] text-white font-bold truncate drop-shadow">
                            {persona.post_count} posts
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Horizontal X-Axis Ticks */}
            <div className="pt-4 border-t border-border flex justify-between text-[10px] font-mono text-text-tertiary px-40">
              {months.map((m) => (
                <span key={m.label}>{m.label}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 2. Chronological Observation Stream with Filters (UI_SPEC.md §5) */}
      <div className="p-5 rounded-lg bg-surface border border-border space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-display font-semibold text-text-primary uppercase tracking-wider">
              Chronological Observation Stream ({filteredEvents.length} events)
            </h3>
          </div>

          {/* Stream Filter Controls */}
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <Filter size={12} className="text-text-tertiary" />
              <span className="text-text-tertiary">Persona:</span>
              <select
                aria-label="Filter by persona"
                value={selectedPersonaFilter}
                onChange={(e) => setSelectedPersonaFilter(e.target.value)}
                className="bg-base border border-border text-text-secondary text-xs rounded px-2 py-1 focus:outline-none focus:border-accent-cyan"
              >
                <option value="all">All Personas</option>
                {orderedPersonas.map((p) => (
                  <option key={p.id} value={p.handle}>
                    {p.handle}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-xs font-mono">
              <span className="text-text-tertiary">Source:</span>
              <select
                aria-label="Filter by source"
                value={selectedSourceFilter}
                onChange={(e) => setSelectedSourceFilter(e.target.value)}
                className="bg-base border border-border text-text-secondary text-xs rounded px-2 py-1 focus:outline-none focus:border-accent-cyan"
              >
                <option value="all">All Sources</option>
                <option value="forum-alpha">forum-alpha</option>
                <option value="marketplace-beta">marketplace-beta</option>
                <option value="forum-gamma">forum-gamma</option>
              </select>
            </div>
          </div>
        </div>

        {/* Observation Stream Cards */}
        {filteredEvents.length === 0 ? (
          <div className="p-8 text-center text-xs font-mono text-text-tertiary">
            No observation events match the current filter selection.
          </div>
        ) : (
          <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
            {filteredEvents.map((ev) => (
              <div
                key={ev.id}
                className="p-3 rounded bg-base/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs transition-colors"
              >
                {/* Meta: Persona & Timestamp */}
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-text-tertiary font-mono text-[11px] shrink-0">
                    {ev.observed_at ? ev.observed_at.slice(0, 10) : '2026-01-01'}
                  </span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => navigate(`/dossier/${ev.persona_id}`)}
                      className="font-mono font-bold text-text-primary hover:text-accent-cyan transition-colors"
                    >
                      {ev.handle}
                    </button>
                    <SourceBadge source={ev.source_id} size="sm" />
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface border border-border text-text-tertiary uppercase">
                    {ev.type.replace('_', ' ')}
                  </span>
                </div>

                {/* Content Value */}
                <div className="flex-1 min-w-0 font-mono text-[11px] text-text-secondary px-2 truncate">
                  {ev.value}
                </div>

                {/* Artifact Action */}
                {ev.artifact_id && (
                  <button
                    type="button"
                    onClick={() => setInspectArtifactId(ev.artifact_id)}
                    className="shrink-0 self-end sm:self-center flex items-center gap-1 text-[11px] font-mono text-accent-primary hover:text-accent-cyan transition-colors"
                  >
                    <span>View Artifact</span>
                    <ArrowRight size={11} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Artifact Viewer Modal */}
      <ArtifactModal
        artifactId={inspectArtifactId}
        onClose={() => setInspectArtifactId(null)}
      />
    </div>
  );
};

export default Timeline;
