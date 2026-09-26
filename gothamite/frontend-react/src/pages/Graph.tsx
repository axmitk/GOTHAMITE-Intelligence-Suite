import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  RefreshCw,
  Search,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import {
  getGraph,
  getEdgeDetails,
  updateEdgeStatus,
  searchEntities,
} from '../api/client';
import type {
  GraphNode,
  GraphEdge,
  EdgeDetails,
  RelationshipStatus,
  EntitySearchMatch,
} from '../types/api';
import {
  GraphCanvas,
  EvidenceInspector,
  ArtifactModal,
  SourceBadge,
} from '../components';

export const Graph: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialEdgeId = searchParams.get('edge');

  // Graph Data
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Selection state
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(initialEdgeId);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeDetails, setSelectedEdgeDetails] = useState<EdgeDetails | null>(null);
  const [loadingEdge, setLoadingEdge] = useState<boolean>(false);
  const [updatingStatus, setUpdatingStatus] = useState<boolean>(false);

  // Filter state
  const [showTransacted, setShowTransacted] = useState<boolean>(true);

  // Search state (UX_SPEC.md §8)
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<EntitySearchMatch[]>([]);
  const [searching, setSearching] = useState<boolean>(false);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  // Modal state
  const [inspectArtifactId, setInspectArtifactId] = useState<string | null>(null);

  /**
   * Load graph payload from GET /api/v1/graph
   */
  const loadGraphData = useCallback(async () => {
    try {
      setErrorBanner(null);
      const graph = await getGraph();
      setNodes(graph.nodes);
      setEdges(graph.edges);

      // If initialEdgeId exists, ensure it's selected
      if (initialEdgeId && graph.edges.some((e) => e.id === initialEdgeId)) {
        setSelectedEdgeId(initialEdgeId);
      }
    } catch (err) {
      console.error('[Graph] Error loading graph payload:', err);
      const apiBase =
        (typeof import.meta !== 'undefined' &&
          import.meta.env &&
          import.meta.env.VITE_API_BASE_URL) ||
        'http://localhost:8000/api/v1';
      setErrorBanner(`Cannot reach GOTHAMITE backend at ${apiBase}. Ensure Docker backend is running.`);
    } finally {
      setLoading(false);
    }
  }, [initialEdgeId]);

  useEffect(() => {
    loadGraphData();
  }, [loadGraphData]);

  /**
   * Fetch complete evidence trail when selectedEdgeId changes
   */
  useEffect(() => {
    if (!selectedEdgeId) {
      setSelectedEdgeDetails(null);
      return;
    }

    let isMounted = true;
    setLoadingEdge(true);

    getEdgeDetails(selectedEdgeId)
      .then((details) => {
        if (isMounted) {
          setSelectedEdgeDetails(details);
          setLoadingEdge(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('[Graph] Failed loading edge details:', err);
          setSelectedEdgeDetails(null);
          setLoadingEdge(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedEdgeId]);

  /**
   * Edge Selection Handler
   */
  const handleSelectEdge = (edgeId: string) => {
    console.log('[Graph] Selecting edge:', edgeId);
    setSelectedEdgeId(edgeId);
    setSelectedNodeId(null);
    setSearchParams({ edge: edgeId }, { replace: true });
  };

  /**
   * Node Selection Handler
   */
  const handleSelectNode = (nodeId: string) => {
    console.log('[Graph] Selecting node:', nodeId);
    setSelectedNodeId(nodeId);
    setSelectedEdgeId(null);
    setSelectedEdgeDetails(null);
    setSearchParams({}, { replace: true });
  };

  /**
   * Clear all selections
   */
  const handleClearSelection = () => {
    setSelectedEdgeId(null);
    setSelectedNodeId(null);
    setSelectedEdgeDetails(null);
    setSearchParams({}, { replace: true });
  };

  /**
   * Confirm / Reject review action handler (UX_SPEC.md §10)
   */
  const handleUpdateStatus = async (newStatus: RelationshipStatus) => {
    if (!selectedEdgeId) return;

    setUpdatingStatus(true);
    setErrorBanner(null);
    setSuccessBanner(null);

    try {
      const updated = await updateEdgeStatus(selectedEdgeId, newStatus);
      setSelectedEdgeDetails(updated);

      // Synchronize edge list in client state
      setEdges((prev) =>
        prev.map((e) => (e.id === selectedEdgeId ? { ...e, status: newStatus } : e))
      );

      const statusLabels = {
        confirmed: 'Confirmed cross-source attribution link.',
        rejected: 'Rejected attribution link. Edge dimmed to low opacity.',
        proposed: 'Reset attribution link state back to proposed.',
      };
      setSuccessBanner(statusLabels[newStatus] || `Updated status to ${newStatus}.`);
    } catch (err) {
      console.error('[Graph] Status update failed:', err);
      setErrorBanner('Failed to update relationship status on backend.');
    } finally {
      setUpdatingStatus(false);
    }
  };

  /**
   * Quick search handler (UX_SPEC.md §8)
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
      console.error('[Graph] Search failed:', err);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  // Filtered edges
  const displayEdges = edges.filter((e) => {
    if (!showTransacted && e.type === 'transacted_with') return false;
    return true;
  });

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;

  return (
    <div className="flex flex-col h-[calc(100vh-61px)] overflow-hidden bg-base">
      {/* Top Toolbar / Action Bar */}
      <div className="border-b border-border bg-surface px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 shrink-0 z-30">
        <div className="flex items-center gap-3">
          <h1 className="text-text-primary font-semibold text-sm">
            Graph
          </h1>
          <span className="text-xs font-mono text-text-tertiary">
            {nodes.length} Nodes · {edges.length} Links
          </span>
        </div>

        {/* Quick Search on Graph (UX_CORRECTION.md §4) */}
        <div className="relative flex-1 max-w-md">
          <form onSubmit={handleSearch} className="relative">
            <div className="flex items-center rounded bg-base border border-border focus-within:border-accent-cyan px-2.5 py-1 text-xs">
              <Search size={14} className="text-text-tertiary mr-2 shrink-0" />
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
                  className="text-text-tertiary hover:text-text-primary text-[10px] px-1"
                >
                  ✕
                </button>
              )}
              <button
                type="submit"
                disabled={searching}
                className="ml-1.5 px-2 py-0.5 rounded bg-surface-raised border border-border text-text-secondary hover:text-text-primary text-[11px] font-mono"
              >
                {searching ? '...' : 'Find'}
              </button>
            </div>
          </form>

          {/* Search Dropdown */}
          {hasSearched && searchQuery.trim() !== '' && (
            <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-surface border border-border rounded-md shadow-2xl p-1.5 max-h-60 overflow-y-auto space-y-1">
              {searchResults.length === 0 ? (
                <div className="p-2 text-center text-xs text-text-tertiary font-mono">
                  No matches for "{searchQuery}"
                </div>
              ) : (
                searchResults.map((match) => (
                  <button
                    key={`${match.persona_id}-${match.match_reason}`}
                    type="button"
                    onClick={() => {
                      handleSelectNode(match.persona_id);
                      setSearchQuery('');
                      setSearchResults([]);
                      setHasSearched(false);
                    }}
                    className="w-full text-left p-2 rounded bg-base hover:bg-surface-raised border border-transparent hover:border-border transition-colors flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <SourceBadge source={match.source_id} size="sm" />
                      <span className="font-mono font-bold text-text-primary">{match.handle}</span>
                      <span className="text-[10px] font-mono text-text-tertiary">
                        ({match.match_reason})
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-accent-cyan">Focus</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* View Filters & Refresh */}
        <div className="flex items-center gap-2.5">
          <label className="flex items-center gap-1.5 text-xs font-mono text-text-secondary cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showTransacted}
              onChange={(e) => setShowTransacted(e.target.checked)}
              className="rounded bg-base border-border text-accent-primary focus:ring-0"
            />
            <span>Show Transacted Edges</span>
          </label>

          <button
            type="button"
            onClick={loadGraphData}
            disabled={loading}
            className="flex items-center gap-1 px-2.5 py-1 rounded text-xs bg-surface-raised border border-border text-text-secondary hover:text-text-primary hover:border-accent-cyan transition-colors disabled:opacity-50"
            title="Reload graph data"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>Reload</span>
          </button>
        </div>
      </div>

      {/* Notification Toasts / Banners */}
      {successBanner && (
        <div className="px-6 py-2 bg-emerald-950/50 border-b border-emerald-800/60 text-emerald-300 text-xs flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={14} className="text-emerald-400" />
            <span className="font-mono">{successBanner}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessBanner(null)}
            className="text-text-tertiary hover:text-text-primary"
          >
            ✕
          </button>
        </div>
      )}

      {errorBanner && (
        <div className="px-6 py-2 bg-red-950/50 border-b border-red-800/60 text-red-300 text-xs flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <AlertCircle size={14} className="text-red-400" />
            <span>{errorBanner}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorBanner(null)}
            className="text-text-tertiary hover:text-text-primary"
          >
            ✕
          </button>
        </div>
      )}

      {/* Two-Pane Layout: Left = 65% Canvas, Right = 35% Inspector (UI_SPEC.md §5) */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left Pane: Canvas (65%) */}
        <div className="flex-1 lg:w-[65%] h-full p-4 overflow-hidden relative">
          <GraphCanvas
            nodes={nodes}
            edges={displayEdges}
            selectedEdgeId={selectedEdgeId}
            selectedNodeId={selectedNodeId}
            onSelectEdge={handleSelectEdge}
            onSelectNode={handleSelectNode}
            onClearSelection={handleClearSelection}
            className="h-full"
          />
        </div>

        {/* Right Pane: Evidence Inspector (35%) */}
        <div className="lg:w-[35%] w-full h-full p-4 lg:pl-0 overflow-y-auto">
          <EvidenceInspector
            selectedEdge={selectedEdgeDetails}
            selectedNode={selectedNode}
            loadingEdge={loadingEdge}
            updatingStatus={updatingStatus}
            onUpdateStatus={handleUpdateStatus}
            onViewArtifact={(artifactId) => setInspectArtifactId(artifactId)}
            onSelectEdgeById={handleSelectEdge}
            className="h-full"
          />
        </div>
      </div>

      {/* Source Artifact Modal */}
      <ArtifactModal
        artifactId={inspectArtifactId}
        onClose={() => setInspectArtifactId(null)}
      />
    </div>
  );
};

export default Graph;
