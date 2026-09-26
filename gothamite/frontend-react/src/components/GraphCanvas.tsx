import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from 'd3-force';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import type { GraphNode, GraphEdge } from '../types/api';
import { getScoreBand, getSourceColor } from '../utils/formatters';

export interface SimNode extends SimulationNodeDatum, GraphNode {
  x: number;
  y: number;
}

export interface SimEdge extends SimulationLinkDatum<SimNode>, GraphEdge {
  source: SimNode;
  target: SimNode;
}

export interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedEdgeId: string | null;
  selectedNodeId: string | null;
  onSelectEdge: (edgeId: string) => void;
  onSelectNode: (nodeId: string) => void;
  onClearSelection: () => void;
  className?: string;
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes,
  edges,
  selectedEdgeId,
  selectedNodeId,
  onSelectEdge,
  onSelectNode,
  onClearSelection,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [, setTickCount] = useState(0);

  // Measure container dimensions
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({
          width: Math.max(clientWidth, 400),
          height: Math.max(clientHeight, 400),
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Prepare simulation data
  const { simNodes, simEdges } = useMemo(() => {
    // Initial deterministic positions arranged in two balanced columns based on source
    const nodeMap = new Map<string, SimNode>();
    const cx = dimensions.width / 2;
    const cy = dimensions.height / 2;
    const radius = Math.min(dimensions.width, dimensions.height) * 0.28;

    nodes.forEach((n, idx) => {
      const angle = (idx / Math.max(nodes.length, 1)) * 2 * Math.PI;
      nodeMap.set(n.id, {
        ...n,
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
      });
    });

    const validEdges: SimEdge[] = [];
    edges.forEach((e) => {
      const src = nodeMap.get(e.from_node);
      const tgt = nodeMap.get(e.to_node);
      if (src && tgt) {
        validEdges.push({
          ...e,
          source: src,
          target: tgt,
        });
      }
    });

    return {
      simNodes: Array.from(nodeMap.values()),
      simEdges: validEdges,
    };
  }, [nodes, edges, dimensions.width, dimensions.height]);

  // Run d3 force simulation
  useEffect(() => {
    if (simNodes.length === 0) return;

    const simulation = forceSimulation<SimNode>(simNodes)
      .force(
        'link',
        forceLink<SimNode, SimEdge>(simEdges)
          .id((d) => d.id)
          .distance(150)
      )
      .force('charge', forceManyBody().strength(-200).distanceMax(250))
      .force('center', forceCenter(dimensions.width / 2, dimensions.height / 2).strength(0.8))
      .force('collide', forceCollide().radius(50));

    const pad = 60;
    simulation.on('tick', () => {
      simNodes.forEach((node) => {
        node.x = Math.max(pad, Math.min(dimensions.width - pad, node.x));
        node.y = Math.max(pad, Math.min(dimensions.height - pad, node.y));
      });
      setTickCount((t) => t + 1);
    });

    simulation.alpha(1).restart();

    return () => {
      simulation.stop();
    };
  }, [simNodes, simEdges, dimensions.width, dimensions.height]);


  // Pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === containerRef.current || (e.target as HTMLElement).tagName === 'svg') {
      setIsPanning(true);
      setPanStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setTransform((prev) => ({
        ...prev,
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      }));
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  // Wheel zoom handler
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setTransform((prev) => {
      const newK = Math.min(Math.max(prev.k * zoomFactor, 0.4), 3.0);
      return { ...prev, k: newK };
    });
  };

  // Zoom control actions
  const zoomIn = () => setTransform((prev) => ({ ...prev, k: Math.min(prev.k * 1.2, 3.0) }));
  const zoomOut = () => setTransform((prev) => ({ ...prev, k: Math.max(prev.k / 1.2, 0.4) }));
  const resetView = useCallback(() => setTransform({ x: 0, y: 0, k: 1 }), []);

  // Node Dragging handlers
  const draggingNodeRef = useRef<SimNode | null>(null);

  const handleNodeMouseDown = (node: SimNode, e: React.MouseEvent) => {
    e.stopPropagation();
    draggingNodeRef.current = node;
    node.fx = node.x;
    node.fy = node.y;

    let didMove = false;

    const handleWindowMouseMove = (moveEvent: MouseEvent) => {
      didMove = true;
      if (draggingNodeRef.current) {
        // Compute new coordinates in SVG space
        const svgElement = containerRef.current?.querySelector('svg');
        if (svgElement) {
          const rect = svgElement.getBoundingClientRect();
          const svgX = (moveEvent.clientX - rect.left - transform.x) / transform.k;
          const svgY = (moveEvent.clientY - rect.top - transform.y) / transform.k;
          draggingNodeRef.current.fx = svgX;
          draggingNodeRef.current.fy = svgY;
          draggingNodeRef.current.x = svgX;
          draggingNodeRef.current.y = svgY;
          setTickCount((t) => t + 1);
        }
      }
    };

    const handleWindowMouseUp = () => {
      if (!didMove && draggingNodeRef.current) {
        onSelectNode(draggingNodeRef.current.id);
      }
      if (draggingNodeRef.current) {
        draggingNodeRef.current.fx = null;
        draggingNodeRef.current.fy = null;
        draggingNodeRef.current = null;
      }
      window.removeEventListener('mousemove', handleWindowMouseMove);
      window.removeEventListener('mouseup', handleWindowMouseUp);
    };

    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', handleWindowMouseUp);
  };

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      className={`relative w-full h-full bg-base border border-border rounded-lg overflow-hidden select-none cursor-grab active:cursor-grabbing ${className}`}
    >
      {/* Canvas Controls Overlay (top right) */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-surface/90 border border-border rounded-md p-1 shadow-lg backdrop-blur-sm">
        <button
          type="button"
          onClick={zoomIn}
          className="p-1.5 rounded text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors"
          title="Zoom In"
        >
          <ZoomIn size={15} />
        </button>
        <button
          type="button"
          onClick={zoomOut}
          className="p-1.5 rounded text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors"
          title="Zoom Out"
        >
          <ZoomOut size={15} />
        </button>
        <div className="w-[1px] h-4 bg-border mx-0.5" />
        <button
          type="button"
          onClick={resetView}
          className="p-1.5 rounded text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors"
          title="Reset View"
        >
          <RotateCcw size={15} />
        </button>
      </div>

      {/* Source Legend Overlay (bottom left) */}
      <div className="absolute bottom-4 left-4 z-20 bg-surface/90 border border-border rounded-md px-3 py-2 text-xs font-mono shadow-lg backdrop-blur-sm space-y-1.5">
        <div className="text-[10px] uppercase font-semibold text-text-tertiary tracking-wider">
          Node Sources
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-text-secondary">
            <span className="w-2 h-2 rounded-full bg-[#3498db]" /> forum-alpha
          </span>
          <span className="flex items-center gap-1.5 text-text-secondary">
            <span className="w-2 h-2 rounded-full bg-[#e67e22]" /> marketplace-beta
          </span>
          <span className="flex items-center gap-1.5 text-text-secondary">
            <span className="w-2 h-2 rounded-full bg-[#2ecc71]" /> forum-gamma
          </span>
        </div>
        <div className="text-[10px] uppercase font-semibold text-text-tertiary tracking-wider pt-1 border-t border-border/50">
          Link Types
        </div>
        <div className="flex items-center gap-3 text-[11px] text-text-secondary">
          <span className="flex items-center gap-1.5">
            <svg width="18" height="6">
              <line x1="0" y1="3" x2="18" y2="3" stroke="#3B82F6" strokeWidth="2" />
            </svg>
            Same Actor
          </span>
          <span className="flex items-center gap-1.5">
            <svg width="18" height="6">
              <line
                x1="0"
                y1="3"
                x2="18"
                y2="3"
                stroke="#F59E0B"
                strokeWidth="2"
                strokeDasharray="3,2"
              />
            </svg>
            Transacted
          </span>
        </div>
      </div>

      {/* Main SVG Graph Canvas */}
      <svg
        width="100%"
        height="100%"
        className="w-full h-full"
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            onClearSelection();
          }
        }}
      >
        <defs>
          {/* Subtle grid pattern */}
          <pattern id="graph-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="var(--border-subtle)"
              strokeWidth="0.6"
            />
          </pattern>
        </defs>

        <rect width="100%" height="100%" fill="url(#graph-grid)" />

        <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.k})`}>
          {/* 1. EDGES LAYER */}
          {simEdges.map((edge) => {
            const isSelected = selectedEdgeId === edge.id;
            const isHovered = hoveredEdgeId === edge.id;
            const hasAnySelection = selectedEdgeId !== null;
            const isRejected = edge.status === 'rejected';

            // Visual specifications from UI_SPEC.md §5
            const isTransacted = edge.type === 'transacted_with';
            const strokeDash = isTransacted ? '6,4' : undefined;

            // Edge thickness scales with score (UI_SPEC.md §5): 2px base, up to 6px for 0.95
            const strokeWidth = Math.max(2, Math.round(2 + edge.score * 4));

            // Color follows score band (UI_SPEC.md §2)
            const bandInfo = getScoreBand(edge.score);
            let strokeColor = '#3B82F6';
            if (bandInfo.band === 'very-strong') strokeColor = '#10B981';
            else if (bandInfo.band === 'strong') strokeColor = '#3B82F6';
            else if (bandInfo.band === 'moderate') strokeColor = '#F59E0B';
            else strokeColor = '#6B7280';

            if (isSelected) {
              strokeColor = '#22D3EE'; // --accent-cyan
            }

            // Opacity: rejected renders at ~15%; non-selected dims to 40% when another edge is selected
            let opacity = 0.85;
            if (isRejected) {
              opacity = 0.15;
            } else if (hasAnySelection && !isSelected) {
              opacity = 0.35;
            } else if (isHovered) {
              opacity = 1.0;
            }

            return (
              <g
                key={edge.id}
                className="cursor-pointer transition-opacity duration-150"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectEdge(edge.id);
                }}
                onMouseEnter={() => setHoveredEdgeId(edge.id)}
                onMouseLeave={() => setHoveredEdgeId(null)}
              >
                {/* Thick invisible hitbox for easy clicking */}
                <line
                  x1={edge.source.x}
                  y1={edge.source.y}
                  x2={edge.target.x}
                  y2={edge.target.y}
                  stroke="transparent"
                  strokeWidth="24"
                />

                {/* Visible styled edge */}
                <line
                  x1={edge.source.x}
                  y1={edge.source.y}
                  x2={edge.target.x}
                  y2={edge.target.y}
                  stroke={strokeColor}
                  strokeWidth={isSelected ? strokeWidth + 2 : strokeWidth}
                  strokeDasharray={strokeDash}
                  strokeOpacity={opacity}
                  strokeLinecap="round"
                />

                {/* Midpoint score pill */}
                <g
                  transform={`translate(${(edge.source.x + edge.target.x) / 2}, ${
                    (edge.source.y + edge.target.y) / 2
                  })`}
                  opacity={opacity}
                >
                  <rect
                    x="-18"
                    y="-9"
                    width="36"
                    height="18"
                    rx="4"
                    fill="var(--bg-surface)"
                    stroke={isSelected ? '#22D3EE' : 'var(--border)'}
                    strokeWidth={isSelected ? '1.5' : '1'}
                  />
                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill={isSelected ? '#22D3EE' : strokeColor}
                    fontFamily="var(--font-mono)"
                    fontSize="10"
                    fontWeight="bold"
                  >
                    {edge.score.toFixed(2)}
                  </text>
                </g>
              </g>
            );
          })}

          {/* 2. NODES LAYER */}
          {simNodes.map((node) => {
            const isSelected = selectedNodeId === node.id;
            const isHovered = hoveredNodeId === node.id;
            const colors = getSourceColor(node.source_id);

            // Determine if node is part of selected edge
            let isConnectedToSelected = false;
            if (selectedEdgeId) {
              const selEdge = simEdges.find((e) => e.id === selectedEdgeId);
              if (selEdge && (selEdge.source.id === node.id || selEdge.target.id === node.id)) {
                isConnectedToSelected = true;
              }
            }

            const nodeRadius = isSelected || isConnectedToSelected ? 22 : 18;

            return (
              <g
                key={node.id}
                data-node-handle={node.handle}
                transform={`translate(${node.x}, ${node.y})`}
                className="cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectNode(node.id);
                }}
                onMouseDown={(e) => handleNodeMouseDown(node, e)}
                onMouseEnter={() => setHoveredNodeId(node.id)}
                onMouseLeave={() => setHoveredNodeId(null)}
              >
                {/* Selection ring */}
                {(isSelected || isConnectedToSelected) && (
                  <circle
                    r={nodeRadius + 6}
                    fill="none"
                    stroke="#22D3EE"
                    strokeWidth="2"
                    strokeDasharray="4,2"
                    className="animate-spin-slow"
                  />
                )}

                {/* Outer shadow / hover ring */}
                {isHovered && !isSelected && (
                  <circle
                    r={nodeRadius + 4}
                    fill="none"
                    stroke="var(--accent-primary)"
                    strokeWidth="1.5"
                    opacity="0.6"
                  />
                )}

                {/* Node Main Circle colored by source */}
                <circle
                  r={nodeRadius}
                  fill="var(--bg-surface)"
                  stroke={isSelected || isConnectedToSelected ? '#22D3EE' : colors.dot.replace('bg-[', '').replace(']', '')}
                  strokeWidth={isSelected ? '3' : '2.5'}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectNode(node.id);
                  }}
                />

                {/* Inner dot with source tint */}
                <circle
                  r={nodeRadius - 8}
                  fill={colors.dot.replace('bg-[', '').replace(']', '')}
                  opacity="0.85"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectNode(node.id);
                  }}
                />

                {/* Monospace handle label beneath node (UI_SPEC.md §5) */}
                <g
                  transform={`translate(0, ${nodeRadius + 15})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectNode(node.id);
                  }}
                >
                  <rect
                    x={-(node.handle.length * 4.2 + 8)}
                    y="-8"
                    width={node.handle.length * 8.4 + 16}
                    height="16"
                    rx="3"
                    fill="var(--bg-surface-raised)"
                    stroke={isSelected ? '#22D3EE' : 'var(--border)'}
                    strokeWidth="0.8"
                    opacity="0.95"
                  />
                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill={isSelected ? '#22D3EE' : 'var(--text-primary)'}
                    fontFamily="var(--font-mono)"
                    fontSize="11"
                    fontWeight="600"
                  >
                    {node.handle}
                  </text>
                </g>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
};

export default GraphCanvas;
