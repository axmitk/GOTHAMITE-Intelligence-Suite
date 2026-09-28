import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Search,
  ArrowRight,
  ExternalLink,
  Calendar,
} from 'lucide-react';
import {
  getGraph,
  getPersonaDossier,
  searchEntities,
} from '../api/client';
import type {
  GraphNode,
  PersonaDossier,
  EntitySearchMatch,
} from '../types/api';
import {
  ScoreBadge,
  StatusPill,
  SourceBadge,
  MonoValue,
  ArtifactModal,
} from '../components';

export const Dossier: React.FC = () => {
  const { personaId } = useParams<{ personaId?: string }>();
  const navigate = useNavigate();

  // Primary states
  const [allPersonas, setAllPersonas] = useState<GraphNode[]>([]);
  const [currentDossier, setCurrentDossier] = useState<PersonaDossier | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingDossier, setLoadingDossier] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Search state (UX_SPEC.md §8)
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<EntitySearchMatch[]>([]);
  const [searching, setSearching] = useState<boolean>(false);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  // Artifact Modal
  const [inspectArtifactId, setInspectArtifactId] = useState<string | null>(null);

  /**
   * Load all available personas for selector
   */
  useEffect(() => {
    let isMounted = true;
    getGraph()
      .then((graph) => {
        if (isMounted) {
          setAllPersonas(graph.nodes);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('[Dossier] Error fetching personas:', err);
          setErrorBanner('Cannot reach GOTHAMITE backend. Ensure Docker backend is running.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  /**
   * Fetch complete dossier when active personaId changes
   */
  const loadDossier = useCallback(async (id: string) => {
    setLoadingDossier(true);
    setErrorBanner(null);
    try {
      const data = await getPersonaDossier(id);
      setCurrentDossier(data);
    } catch (err) {
      console.error(`[Dossier] Failed to load dossier for ${id}:`, err);
      setErrorBanner(`Failed to load dossier for persona ${id}.`);
    } finally {
      setLoadingDossier(false);
    }
  }, []);

  useEffect(() => {
    if (allPersonas.length === 0) return;

    if (personaId) {
      loadDossier(personaId);
    } else {
      // Default to the first persona if none specified in route
      const defaultId = allPersonas[0].id;
      navigate(`/dossier/${defaultId}`, { replace: true });
    }
  }, [personaId, allPersonas, loadDossier, navigate]);

  /**
   * Multi-vector entity search handler
   */
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const q = searchQuery.trim();
    if (!q) {
      setSearchResults([]);
      setHasSearched(false);
      return;
    }

    setSearching(true);
    setHasSearched(true);
    try {
      const res = await searchEntities(q);
      setSearchResults(res.results || []);
    } catch (err) {
      console.error('[Dossier] Search failed:', err);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleSelectPersona = (newId: string) => {
    navigate(`/dossier/${newId}`);
  };

  // Activity span calculation helper
  const getActivitySpan = (first: string | null, last: string | null) => {
    if (!first || !last) return 'Unknown span';
    const d1 = new Date(first);
    const d2 = new Date(last);
    const diffDays = Math.round(Math.abs((d2.getTime() - d1.getTime()) / (1000 * 60 * 60 * 24)));
    return `${diffDays} days active`;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header & Search Bar (UI_CORRECTION.md §3.1, UX_CORRECTION.md §2) */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-xl font-display font-bold text-text-primary tracking-wide">
            Dossier
          </h1>
        </div>

        {/* Persona Select Dropdown */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-mono text-text-tertiary">Persona:</label>
          <select
            value={personaId || ''}
            onChange={(e) => handleSelectPersona(e.target.value)}
            disabled={loading || allPersonas.length === 0}
            className="bg-surface border border-border text-text-primary text-xs font-mono rounded px-3 py-1.5 focus:outline-none focus:border-accent-cyan"
          >
            {allPersonas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.handle} ({p.source_id})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Multi-vector Search (UX_CORRECTION.md §4) */}
      <div className="relative">
        <form onSubmit={handleSearch} className="relative">
          <div className="flex items-center rounded-lg bg-surface border border-border focus-within:border-accent-cyan px-3 py-2 shadow-inner">
            <Search size={16} className="text-text-tertiary mr-2.5 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search handle, PGP fingerprint, or wallet..."
              className="bg-transparent text-text-primary placeholder:text-text-tertiary text-xs font-mono w-full focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                  setHasSearched(false);
                }}
                className="text-text-tertiary hover:text-text-primary text-xs px-2"
              >
                Clear
              </button>
            )}
            <button
              type="submit"
              disabled={searching}
              className="ml-2 px-3 py-1 rounded bg-surface-raised border border-border text-text-secondary hover:text-text-primary hover:border-accent-primary text-xs font-mono transition-colors"
            >
              {searching ? '...' : 'Search'}
            </button>
          </div>
        </form>

        {/* Search Results Dropdown */}
        {hasSearched && searchQuery.trim() !== '' && (
          <div className="absolute top-full left-0 right-0 mt-1.5 z-40 bg-surface border border-border rounded-lg shadow-2xl p-2 max-h-72 overflow-y-auto space-y-1">
            {searchResults.length === 0 ? (
              <div className="p-3 text-center text-xs text-text-tertiary font-mono">
                No matching personas, fingerprints, or wallets found for "{searchQuery}".
              </div>
            ) : (
              searchResults.map((result) => (
                <button
                  key={`${result.persona_id}-${result.match_reason}`}
                  type="button"
                  onClick={() => {
                    handleSelectPersona(result.persona_id);
                    setSearchQuery('');
                    setSearchResults([]);
                    setHasSearched(false);
                  }}
                  className="w-full text-left p-2.5 rounded bg-base/50 hover:bg-surface-raised border border-transparent hover:border-border transition-colors flex items-center justify-between gap-3 text-xs group"
                >
                  <div className="flex items-center gap-2.5">
                    <SourceBadge source={result.source_id} size="sm" />
                    <span className="font-mono font-bold text-text-primary group-hover:text-accent-cyan">
                      {result.handle}
                    </span>
                    <span className="text-text-tertiary text-[11px] font-mono">
                      Matched via <span className="text-accent-primary">{result.match_reason}</span>:{' '}
                      <span className="text-text-secondary">{result.matched_term}</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-text-tertiary group-hover:text-accent-cyan font-mono shrink-0">
                    <span>Open Dossier</span>
                    <ArrowRight size={12} />
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Error Fallback Banner */}
      {errorBanner && (
        <div className="p-4 rounded-lg bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-center justify-between">
          <span>{errorBanner}</span>
          <button
            type="button"
            onClick={() => personaId && loadDossier(personaId)}
            className="px-3 py-1 rounded bg-red-900/60 border border-red-700 text-white hover:bg-red-800 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton State */}
      {loadingDossier && (
        <div className="space-y-4 animate-pulse">
          <div className="h-24 bg-surface rounded-lg border border-border" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="h-64 bg-surface rounded-lg border border-border" />
            <div className="h-64 bg-surface rounded-lg border border-border" />
          </div>
        </div>
      )}

      {/* Main Dossier Content */}
      {!loadingDossier && currentDossier && (
        <div className="space-y-6">
          {/* 1. Persona Profile Header Card (UI_CORRECTION.md §3.4) */}
          <div className="p-5 rounded-lg bg-surface space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-2xl font-mono font-bold text-text-primary">
                    {currentDossier.handle}
                  </h2>
                  <SourceBadge source={currentDossier.source_id} size="md" />
                  <span className="text-xs font-mono text-text-tertiary uppercase">
                    · {currentDossier.source_type}
                  </span>
                </div>
                <p className="text-xs text-text-tertiary mt-1 font-mono">
                  UUID: <MonoValue value={currentDossier.persona_id} copyable={true} />
                </p>
              </div>

              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={() => navigate('/graph')}
                  className="flex items-center gap-1 text-xs font-mono text-accent-primary hover:text-accent-cyan transition-colors"
                >
                  <span>View in Graph</span>
                  <ArrowRight size={12} />
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/timeline')}
                  className="flex items-center gap-1 text-xs font-mono text-accent-primary hover:text-accent-cyan transition-colors"
                >
                  <span>View in Timeline</span>
                  <ArrowRight size={12} />
                </button>
              </div>
            </div>

            {/* Profile Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-base/60 p-3.5 rounded font-mono">
              <div>
                <span className="text-[10px] uppercase text-text-tertiary block">First Seen</span>
                <span className="text-text-secondary text-[11px]">
                  {currentDossier.first_seen ? new Date(currentDossier.first_seen).toUTCString().slice(0, 16) : 'Unknown'}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-text-tertiary block">Last Seen</span>
                <span className="text-text-secondary text-[11px]">
                  {currentDossier.last_seen ? new Date(currentDossier.last_seen).toUTCString().slice(0, 16) : 'Unknown'}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-text-tertiary block">Activity Window</span>
                <span className="text-emerald-400 font-bold text-[11px]">
                  {getActivitySpan(currentDossier.first_seen, currentDossier.last_seen)}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-text-tertiary block">Total Posts</span>
                <span className="text-text-primary font-bold text-sm">
                  {currentDossier.post_count}
                </span>
              </div>
            </div>
          </div>

          {/* 2. Two-Column Layout: Identifiers (Left) & Correlated Links (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column: Digital Identifiers (UI_CORRECTION.md §3.3, §3.4) */}
            <div className="p-5 rounded-lg bg-surface space-y-4">
              <div className="border-b border-border pb-3">
                <h2 className="text-sm font-display font-semibold text-text-primary uppercase tracking-wider">
                  Digital Identifiers ({currentDossier.identifiers?.length || 0})
                </h2>
              </div>

              {(!currentDossier.identifiers || currentDossier.identifiers.length === 0) ? (
                <div className="p-6 text-center text-xs text-text-tertiary font-mono">
                  No explicit identifiers observed for this persona.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {currentDossier.identifiers.map((ident) => {
                    return (
                      <div
                        key={ident.identifier_id}
                        className="p-3.5 rounded bg-base/60 space-y-2 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-mono text-text-secondary uppercase font-semibold">
                            {ident.type.replace('_', ' ')}
                          </span>
                          <span className="text-[10px] font-mono text-text-tertiary">
                            Observed: {ident.observed_at ? new Date(ident.observed_at).toLocaleDateString() : 'N/A'}
                          </span>
                        </div>

                        {/* Exact copyable MonoValue block (UI_SPEC.md §5, UX_CORRECTION.md §6) */}
                        <div className="py-1 text-xs font-mono">
                          <MonoValue
                            value={ident.value}
                            truncateMiddle={true}
                            truncateLength={36}
                            copyable={true}
                            className="text-xs text-text-primary font-medium select-all"
                            title={ident.value}
                          />
                        </div>

                        {/* Originating Artifact Reference */}
                        {ident.artifact_id && (
                          <div className="flex items-center justify-between pt-1 border-t border-border/30 text-[11px]">
                            <span className="text-text-tertiary font-mono">
                              Artifact: {ident.artifact_id.slice(0, 8)}...
                            </span>
                            <button
                              type="button"
                              onClick={() => setInspectArtifactId(ident.artifact_id)}
                              className="flex items-center gap-1 text-accent-primary hover:text-accent-cyan font-mono transition-colors"
                            >
                              <span>View Source</span>
                              <ExternalLink size={11} />
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Right Column: Correlated Cross-Source Linkages (UI_CORRECTION.md §3.3, §3.4) */}
            <div className="p-5 rounded-lg bg-surface space-y-4">
              <div className="border-b border-border pb-3">
                <h2 className="text-sm font-display font-semibold text-text-primary uppercase tracking-wider">
                  Cross-Source Linkages ({currentDossier.correlated_links?.length || 0})
                </h2>
              </div>

              {(!currentDossier.correlated_links || currentDossier.correlated_links.length === 0) ? (
                <div className="p-8 text-center text-xs text-text-tertiary font-mono bg-base/50 rounded space-y-2">
                  <div>No cross-source relationships proposed or confirmed.</div>
                  <p className="text-[11px] text-text-secondary">
                    Check the Graph canvas or trigger correlation on the Overview page.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {currentDossier.correlated_links.map((link) => (
                    <div
                      key={link.relationship_id}
                      className="p-3.5 rounded bg-base/60 space-y-2.5 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-text-tertiary font-mono text-xs">
                            {link.direction === 'outgoing' ? '➔ Outgoing to:' : '⬅ Incoming from:'}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleSelectPersona(link.target_persona_id)}
                            className="font-mono text-sm font-bold text-text-primary hover:text-accent-cyan transition-colors"
                          >
                            {link.target_handle}
                          </button>
                          <SourceBadge source={link.target_source} size="sm" />
                        </div>

                        <StatusPill status={link.status} variant="dot" />
                      </div>

                      <div className="flex items-center justify-between pt-1">
                        <div className="flex items-center gap-2">
                          <ScoreBadge score={link.score} size="sm" />
                        </div>

                        {/* Working link back to Graph view (UX_CORRECTION.md §6) */}
                        <button
                          type="button"
                          onClick={() => navigate(`/graph?edge=${link.relationship_id}`)}
                          className="flex items-center gap-1 text-xs font-mono text-accent-primary hover:text-accent-cyan transition-colors"
                        >
                          <span>Jump to Graph Edge</span>
                          <ArrowRight size={12} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 3. Scraped Observation Timeline & Provenance (UI_CORRECTION.md §3.3, §3.4) */}
          <div className="p-5 rounded-lg bg-surface space-y-4">
            <div className="border-b border-border pb-3">
              <h2 className="text-sm font-display font-semibold text-text-primary uppercase tracking-wider">
                Observation Timeline & Immutable Artifacts ({currentDossier.timeline?.length || 0})
              </h2>
            </div>

            {(!currentDossier.timeline || currentDossier.timeline.length === 0) ? (
              <div className="p-6 text-center text-xs text-text-tertiary font-mono">
                No observation history recorded.
              </div>
            ) : (
              <div className="space-y-2.5">
                {currentDossier.timeline.map((item, idx) => (
                  <div
                    key={`${item.artifact_id}-${idx}`}
                    className="p-3.5 rounded bg-base/60 space-y-2 transition-colors"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <Calendar size={13} className="text-text-tertiary" />
                        <span className="font-mono text-text-secondary text-[11px]">
                          {item.collected_at ? new Date(item.collected_at).toUTCString() : 'N/A'}
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-[11px] font-mono text-text-tertiary truncate max-w-xs">
                          {item.url}
                        </span>
                        <button
                          type="button"
                          onClick={() => setInspectArtifactId(item.artifact_id)}
                          className="flex items-center gap-1 text-[11px] font-mono text-accent-primary hover:text-accent-cyan transition-colors"
                        >
                          <span>Inspect Artifact</span>
                          <ArrowRight size={11} />
                        </button>
                      </div>
                    </div>

                    {/* Escaped raw snippet preview */}
                    <pre className="font-mono text-xs text-text-secondary bg-base p-3 rounded border border-border/60 overflow-x-auto whitespace-pre-wrap break-all max-h-24 select-text">
                      {item.snippet}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Artifact Viewer Modal */}
      <ArtifactModal
        artifactId={inspectArtifactId}
        onClose={() => setInspectArtifactId(null)}
      />
    </div>
  );
};

export default Dossier;
