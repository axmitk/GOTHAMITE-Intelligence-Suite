import { useId, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Minus, Plus, RotateCcw, ArrowUpRight } from "lucide-react";
import { useResource } from "./api";
import { Badge, Panel, ResourceState, EvidenceRefs } from "./ui";
import { human, kindLabel, plural, entityUrl } from "./formatters";
import type { GraphData, Relationship } from "./types";

const kinds = [
  "threat_actor",
  "campaign",
  "malware",
  "hash",
  "domain",
  "ip",
  "asset",
  "incident",
];
const laneFor: Record<string, number> = {
  threat_actor: 0,
  darkweb_mention: 0,
  campaign: 1,
  malware: 2,
  hash: 2,
  vulnerability: 2,
  domain: 3,
  ip: 3,
  url: 3,
  email: 3,
  asset: 4,
  organization: 4,
  incident: 5,
};
const lanes = [
  "Threat actor",
  "Campaign",
  "Malware / hash",
  "Domain / IP",
  "Asset",
  "Incident",
];
const WIDTH = 176;
const STEP = 206;

// Choose a continuous, evidence-backed path. Do not infer absent edges.
function investigationPath(data: GraphData, root: string) {
  const paths: string[][] = [];
  function walk(path: string[], index: number) {
    const last = path[path.length - 1];
    const next = data.nodes.filter(
      (n) =>
        n.kind === kinds[index + 1] &&
        data.edges.some(
          (e) =>
            (e.source_id === last && e.target_id === n.id) ||
            (e.target_id === last && e.source_id === n.id),
        ),
    );
    if (!next.length) {
      paths.push(path);
      return;
    }
    for (const n of next) walk([...path, n.id], index + 1);
  }
  for (const n of data.nodes) {
    const index = kinds.indexOf(n.kind);
    if (index >= 0) walk([n.id], index);
  }
  paths.sort(
    (a, b) =>
      (b.includes(root) ? 100 : 0) +
      b.length -
      ((a.includes(root) ? 100 : 0) + a.length),
  );
  const path = paths[0] || [root];
  const ids = new Set(path);
  ids.add(root);
  const edges = data.edges.filter((e) =>
    path.some(
      (id, i) =>
        i > 0 &&
        ((path[i - 1] === e.source_id && id === e.target_id) ||
          (path[i - 1] === e.target_id && id === e.source_id)),
    ),
  );
  // Keep direct, strongly supported observations visible without adding branches.
  for (const e of data.edges) {
    if (
      e.confidence >= 0.9 &&
      ids.has(e.source_id) &&
      ids.has(e.target_id) &&
      !edges.includes(e)
    )
      edges.push(e);
  }
  return { ids, edges: new Set(edges.map((e) => e.id)) };
}

type Point = { x: number; y: number };
type Route = { d: string; inverse: boolean; label: Point };
const HEIGHT = 64;
const ROW = 108;

// Orthogonal routing on the lane grid. Vertical runs use the gutters between
// lanes and horizontal runs use the gaps between rows, so a relationship never
// passes behind an unrelated entity. Shared gutters/gaps get separate slots,
// and ports are spread along each node side so arrowheads do not stack.
function routeEdges(
  edges: Relationship[],
  positions: Map<string, Point>,
  kindOf: Map<string, string>,
  full: boolean,
) {
  type Plan = {
    e: Relationship;
    a: Point;
    b: Point;
    inverse: boolean;
    kind: "vertical" | "curve" | "gutter" | "orthogonal";
    exit: "left" | "right";
    enter: "left" | "right";
  };
  const plans: Plan[] = [];
  for (const e of edges) {
    // Display the inverse AFFECTS relation in the left-to-right path.
    // The inspector and full graph preserve the stored direction.
    const inverse =
      !full &&
      e.relation === "AFFECTS" &&
      kindOf.get(e.source_id) === "incident";
    const a = positions.get(inverse ? e.target_id : e.source_id);
    const b = positions.get(inverse ? e.source_id : e.target_id);
    if (!a || !b) continue;
    const dx = b.x - a.x,
      dy = Math.abs(b.y - a.y);
    const forward = dx >= 0;
    const kind =
      dx === 0
        ? dy <= ROW
          ? "vertical"
          : "gutter"
        : Math.abs(dx) <= STEP && dy <= ROW
          ? "curve"
          : "orthogonal";
    plans.push({
      e,
      a,
      b,
      inverse,
      kind,
      exit: kind === "gutter" || forward ? "right" : "left",
      enter: kind === "gutter" || !forward ? "right" : "left",
    });
  }
  // Spread ports along each node side, ordered by the far endpoint's height.
  const sides = new Map<
    string,
    { plan: Plan; end: "a" | "b"; other: number }[]
  >();
  for (const plan of plans) {
    if (plan.kind === "vertical") continue;
    for (const end of ["a", "b"] as const) {
      const p = plan[end];
      const side = end === "a" ? plan.exit : plan.enter;
      const key = `${p.x}:${p.y}:${side}`;
      const list = sides.get(key) || [];
      list.push({ plan, end, other: (end === "a" ? plan.b : plan.a).y });
      sides.set(key, list);
    }
  }
  const ports = new Map<string, number>();
  for (const list of sides.values()) {
    list.sort((m, n) => m.other - n.other);
    list.forEach(({ plan, end }, i) => {
      const offset = (i - (list.length - 1) / 2) * 9;
      ports.set(
        `${plan.e.id}:${end}`,
        (end === "a" ? plan.a : plan.b).y +
          HEIGHT / 2 +
          Math.max(-22, Math.min(22, offset)),
      );
    });
  }
  const gutterSlots = new Map<number, number>();
  const gapSlots = new Map<number, number>();
  // Gutter to the right of a lane whose nodes start at x.
  const gutter = (x: number) => {
    const slot = gutterSlots.get(x) || 0;
    gutterSlots.set(x, slot + 1);
    return x + WIDTH + 7 + (slot % 4) * 5;
  };
  const gap = (y: number) => {
    const slot = gapSlots.get(y) || 0;
    gapSlots.set(y, slot + 1);
    return y + ((slot % 5) - 2) * 6;
  };
  const routes = new Map<string, Route>();
  for (const plan of plans) {
    const { a, b, e, inverse } = plan;
    const sy = ports.get(`${e.id}:a`) ?? a.y + HEIGHT / 2,
      ty = ports.get(`${e.id}:b`) ?? b.y + HEIGHT / 2;
    const sx = plan.exit === "right" ? a.x + WIDTH : a.x,
      tx = plan.enter === "right" ? b.x + WIDTH : b.x;
    let d: string;
    // Labels sit above the node row so entities never cover them.
    let label = { x: (sx + tx) / 2, y: Math.min(a.y, b.y) - 10 };
    if (plan.kind === "vertical") {
      const down = b.y > a.y;
      d = `M${a.x + WIDTH / 2} ${a.y + (down ? HEIGHT : 0)} L${b.x + WIDTH / 2} ${b.y + (down ? 0 : HEIGHT)}`;
    } else if (plan.kind === "curve") {
      const mx = (sx + tx) / 2;
      d = `M${sx} ${sy} C${mx} ${sy},${mx} ${ty},${tx} ${ty}`;
    } else if (plan.kind === "gutter") {
      const gx = gutter(a.x);
      d = `M${sx} ${sy} H${gx} V${ty} H${tx}`;
    } else {
      // Leave through the gutter beside the source lane, travel along the row
      // gap adjacent to the target row, then enter through the target's gutter.
      const forward = b.x > a.x;
      const gxA = forward ? gutter(a.x) : gutter(a.x - STEP);
      if (Math.abs(b.x - a.x) === STEP) {
        d = `M${sx} ${sy} H${gxA} V${ty} H${tx}`;
      } else {
        const gy =
          b.y > a.y
            ? gap(b.y - (ROW - HEIGHT) / 2)
            : b.y < a.y
              ? gap(b.y + HEIGHT + (ROW - HEIGHT) / 2)
              : gap(a.y + HEIGHT + (ROW - HEIGHT) / 2);
        const gxB = forward ? gutter(b.x - STEP) : gutter(b.x);
        d = `M${sx} ${sy} H${gxA} V${gy} H${gxB} V${ty} H${tx}`;
        label = { x: (gxA + gxB) / 2, y: gy - 6 };
      }
    }
    routes.set(e.id, { d, inverse, label });
  }
  return routes;
}

export function RelationshipGraph({
  root,
  caseId,
  onInspect,
}: {
  root: string;
  caseId?: string;
  onInspect: (id: string) => void;
}) {
  const [focus, setFocus] = useState(caseId || root);
  const [depth, setDepth] = useState(3);
  const [zoom, setZoom] = useState(1);
  const [full, setFull] = useState(false);
  const [selected, setSelected] = useState<string | null>(root);
  const [edgeId, setEdgeId] = useState<string | null>(null);
  const marker = useId().replaceAll(":", "");
  const inspector = useRef<HTMLElement>(null);
  const { data, loading, error, reload } = useResource<GraphData>(
    `/graph/${encodeURIComponent(focus)}?depth=${depth}&limit=60`,
  );
  const view = useMemo(() => {
    if (!data) return null;
    const primary = investigationPath(data, root);
    const selectedEdge = data.edges.find((e) => e.id === edgeId);
    const shown = new Set(primary.ids);
    if (selectedEdge) {
      shown.add(selectedEdge.source_id);
      shown.add(selectedEdge.target_id);
    }
    const nodes = data.nodes.filter((n) => full || shown.has(n.id));
    const edges = data.edges.filter(
      (e) => full || primary.edges.has(e.id) || e.id === edgeId,
    );
    const positions = new Map<string, { x: number; y: number }>();
    const counts = [0, 0, 0, 0, 0, 0];
    // Primary path forms a staircase: artifact and infrastructure pairs stay together.
    for (const n of nodes.filter((n) => primary.ids.has(n.id))) {
      const lane = laneFor[n.kind] ?? 0;
      const row =
        n.kind === "hash" || n.kind === "domain"
          ? 1
          : ["ip", "asset", "incident"].includes(n.kind)
            ? 2
            : 0;
      const y = 76 + row * 108;
      positions.set(n.id, { x: 20 + lane * STEP, y });
      counts[lane] = Math.max(counts[lane], row + 1);
    }
    for (const n of nodes.filter((n) => !primary.ids.has(n.id))) {
      const lane = laneFor[n.kind] ?? 0;
      counts[lane] = Math.max(counts[lane], 3);
      positions.set(n.id, {
        x: 20 + lane * STEP,
        y: 76 + counts[lane]++ * 108,
      });
    }
    const base = Math.max(3, ...counts) * 108 + 50;
    const kindOf = new Map(data.nodes.map((n) => [n.id, n.kind]));
    return {
      primary,
      nodes,
      edges,
      positions,
      routes: routeEdges(edges, positions, kindOf, full),
      height: base + 40,
    };
  }, [data, root, full, edgeId]);
  if (!data || !view)
    return <ResourceState loading={loading} error={error} retry={reload} />;
  const node = data.nodes.find((n) => n.id === selected);
  const edge = data.edges.find((e) => e.id === edgeId);
  const connected = data.edges
    .filter((e) => e.source_id === selected || e.target_id === selected)
    .sort((a, b) => b.confidence - a.confidence);
  const labels = new Map(data.nodes.map((n) => [n.id, n.label]));
  const hidden = data.edges.filter((e) => !view.primary.edges.has(e.id));
  const groupFor = (e: Relationship) =>
    e.confidence < 0.65
      ? "Source claims"
      : e.relation === "RESOLVES_TO" || e.relation === "HOSTED_ON"
        ? "Infrastructure context"
        : "Supporting context";
  const groups = [
    "Supporting context",
    "Infrastructure context",
    "Source claims",
  ]
    .map((label) => ({
      label,
      edges: hidden.filter((e) => groupFor(e) === label),
    }))
    .filter((g) => g.edges.length);
  function selectNode(id: string) {
    setSelected(id);
    setEdgeId(null);
  }
  function reset() {
    setZoom(1);
    setDepth(3);
    setFull(false);
    setFocus(caseId || root);
    selectNode(root);
  }
  return (
    <Panel
      title="Evidence relationship graph"
      meta={
        <span className="wb-mono">
          {view.nodes.length} / {data.nodes.length} ENTITIES ·{" "}
          {view.edges.length} / {data.edges.length} LINKS
        </span>
      }
    >
      <div className="wb-graph-toolbar">
        <div className="wb-segmented" aria-label="Graph presentation">
          <button
            aria-pressed={!full}
            onClick={() => {
              setFull(false);
              setEdgeId(null);
            }}
          >
            Investigation path
          </button>
          <button aria-pressed={full} onClick={() => setFull(true)}>
            Full graph
          </button>
        </div>
        <div>
          <label>
            Depth{" "}
            <select
              aria-label="Graph depth"
              value={depth}
              onChange={(e) => {
                setDepth(Number(e.target.value));
                setEdgeId(null);
              }}
            >
              <option value={1}>1 hop</option>
              <option value={2}>2 hops</option>
              <option value={3}>3 hops</option>
              <option value={5}>5 hops</option>
            </select>
          </label>
          <button
            className="wb-icon-button"
            aria-label="Zoom out"
            onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
          >
            <Minus size={15} />
          </button>
          <button
            className="wb-icon-button"
            aria-label="Zoom in"
            onClick={() => setZoom((z) => Math.min(2, z + 0.2))}
          >
            <Plus size={15} />
          </button>
          <button
            className="wb-icon-button"
            aria-label="Reset graph"
            onClick={reset}
          >
            <RotateCcw size={15} />
          </button>
        </div>
      </div>
      <div className="wb-graph-caption">
        <span>
          <i className="wb-line-key" /> Primary path{" "}
          <i className="wb-line-key observed" /> High-confidence observation
        </span>
        <span>
          {focus} ·{" "}
          {full
            ? "All relationships in scope"
            : "Secondary associations grouped below"}
        </span>
      </div>
      <div className="wb-graph-layout">
        <div className="wb-graph-scroll">
          <svg
            viewBox={`0 0 1240 ${view.height}`}
            style={{ width: `${zoom * 100}%`, minWidth: `${zoom * 880}px` }}
            aria-label="Evidence-backed entity relationships"
          >
            <defs>
              <marker
                id={marker}
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="5"
                markerHeight="5"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" />
              </marker>
            </defs>
            {lanes.map((l, i) => (
              <g key={l}>
                <text x={20 + i * STEP} y={29} className="wb-graph-lane">
                  {String(i + 1).padStart(2, "0")} / {l.toUpperCase()}
                </text>
                <line
                  x1={12 + i * STEP}
                  x2={12 + i * STEP}
                  y1={47}
                  y2={view.height - 20}
                  stroke="var(--wb-border)"
                  strokeDasharray="2 8"
                />
              </g>
            ))}
            {view.edges.map((e) => {
              const route = view.routes.get(e.id);
              if (!route) return null;
              const { d: path, inverse, label } = route;
              const primary = view.primary.edges.has(e.id),
                active = edgeId === e.id,
                // In the full graph, a selected entity keeps its own relationships
                // in focus and recedes the rest; nothing is hidden.
                muted =
                  full &&
                  !edgeId &&
                  !!selected &&
                  e.source_id !== selected &&
                  e.target_id !== selected;
              return (
                <g
                  key={e.id}
                  data-from={e.source_id}
                  data-to={e.target_id}
                  role="button"
                  tabIndex={0}
                  aria-label={`${labels.get(e.source_id)} ${human(e.relation)} ${labels.get(e.target_id)}`}
                  onClick={() => setEdgeId(e.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setEdgeId(e.id);
                    }
                  }}
                  className={`wb-graph-edge ${primary ? "primary" : "secondary"} ${e.confidence >= 0.9 ? "observed" : ""} ${active ? "selected" : ""} ${muted ? "muted" : ""}`}
                >
                  <path
                    d={path}
                    fill="none"
                    stroke="transparent"
                    strokeWidth={14}
                  />
                  <path
                    d={path}
                    fill="none"
                    className="wb-edge-line"
                    markerEnd={`url(#${marker})`}
                  />
                  <title>
                    {inverse ? "Affected in (inverse of AFFECTS) · " : ""}
                    {human(e.relation)} · confidence {e.confidence.toFixed(2)} ·{" "}
                    {e.evidence_id}
                  </title>
                  {inverse && (
                    <text
                      x={label.x}
                      y={label.y}
                      textAnchor="middle"
                      className="wb-edge-label"
                    >
                      affected in
                    </text>
                  )}
                </g>
              );
            })}
            {view.nodes.map((n) => {
              const p = view.positions.get(n.id)!;
              const label =
                n.kind === "hash"
                  ? `SHA-256 · ${n.label.slice(0, 12)}…`
                  : n.label;
              const splitAt =
                label.lastIndexOf(" ", 23) > 8
                  ? label.lastIndexOf(" ", 23)
                  : 23;
              const lines =
                label.length > 25
                  ? [label.slice(0, splitAt), label.slice(splitAt).trim()]
                  : [label];
              return (
                <g
                  key={n.id}
                  data-node={n.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`Select ${n.label}`}
                  transform={`translate(${p.x} ${p.y})`}
                  onClick={() => selectNode(n.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      selectNode(n.id);
                    }
                  }}
                  className={`wb-graph-node ${selected === n.id ? "selected" : ""} ${view.primary.ids.has(n.id) ? "" : "secondary"}`}
                >
                  <rect width={WIDTH} height="64" rx="4" />
                  <text x="11" y="21" className="wb-node-kind">
                    {kindLabel(n.kind).toUpperCase()}
                  </text>
                  <text
                    x="11"
                    y={lines.length > 1 ? 38 : 43}
                    className="wb-node-label"
                  >
                    {lines.map((line, index) => (
                      <tspan key={index} x="11" dy={index ? 14 : 0}>
                        {line.length > 25 ? line.slice(0, 23) + "…" : line}
                      </tspan>
                    ))}
                  </text>
                  <title>
                    {n.label} · {n.summary}
                  </title>
                </g>
              );
            })}
          </svg>
        </div>
        <aside
          className="wb-graph-inspector"
          ref={inspector}
          tabIndex={-1}
          aria-label="Relationship inspector"
        >
          {edge ? (
            <>
              <div>
                <span className="wb-eyebrow">Selected relationship</span>
                <h3>{human(edge.relation)}</h3>
                <p className="wb-break">
                  {labels.get(edge.source_id)} → {labels.get(edge.target_id)}
                </p>
                <Badge
                  value={
                    edge.confidence >= 0.9
                      ? "High confidence"
                      : "Synthetic association"
                  }
                  tone="demo"
                />
                <p>Confidence annotation: {edge.confidence.toFixed(2)}</p>
              </div>
              <div>
                <h4>Supporting observation</h4>
                <EvidenceRefs ids={[edge.evidence_id]} onInspect={onInspect} />
                <p className="wb-footnote">
                  An association is not proof of identity or compromise. The
                  inspector shows the recorded direction; the primary path uses
                  “affected in” for the inverse incident relationship.
                </p>
              </div>
            </>
          ) : node ? (
            <>
              <div>
                <span className="wb-eyebrow">Selected entity</span>
                <h3 className="wb-break">{node.label}</h3>
                <Badge
                  value={node.kind}
                  label={kindLabel(node.kind)}
                  tone="kind"
                />
                <p>{node.summary}</p>
                <Link className="wb-button full" to={entityUrl(node)}>
                  Open {node.kind === "incident" ? "investigation" : "profile"}{" "}
                  <ArrowUpRight size={14} />
                </Link>
                <button
                  className="wb-text-button wb-graph-refocus"
                  onClick={() => {
                    setFocus(node.id);
                    setEdgeId(null);
                  }}
                >
                  Explore from this entity →
                </button>
              </div>
              <div>
                <h4>{plural(connected.length, "supporting relationship")}</h4>
                <div className="wb-connection-list">
                  {connected.map((e) => (
                    <button key={e.id} onClick={() => setEdgeId(e.id)}>
                      <small>
                        {human(e.relation)} · {e.confidence.toFixed(2)}
                      </small>
                      <span>
                        {labels.get(
                          e.source_id === node.id ? e.target_id : e.source_id,
                        )}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p>Select an entity or relationship to inspect its evidence.</p>
          )}
        </aside>
      </div>
      {groups.length > 0 && (
        <div className="wb-relationship-groups">
          <div className="wb-eyebrow">
            Secondary relationships · expand to inspect
          </div>
          {groups.map((group) => (
            <details key={group.label}>
              <summary>
                {group.label}
                <span>{plural(group.edges.length, "relationship")}</span>
              </summary>
              <div>
                {group.edges.map((e) => (
                  <button
                    key={e.id}
                    className="wb-relationship-row"
                    onClick={() => {
                      setEdgeId(e.id);
                      inspector.current?.focus({ preventScroll: true });
                      inspector.current?.scrollIntoView({ block: "nearest" });
                    }}
                  >
                    <span>
                      {labels.get(e.source_id)}{" "}
                      <small>{human(e.relation).toLowerCase()}</small>{" "}
                      {labels.get(e.target_id)}
                    </span>
                    <span className="wb-mono">
                      {e.confidence.toFixed(2)} · {e.evidence_id} ↗
                    </span>
                  </button>
                ))}
              </div>
            </details>
          ))}
        </div>
      )}
      <div className="wb-panel-footer">
        <span>
          {data.truncated
            ? "Bounded to 60 entities. Explore an entity or change depth to inspect additional connections."
            : "No relationships removed. Full graph and grouped observations retain the evidence."}
        </span>
        <span>Tab + Enter to inspect</span>
      </div>
    </Panel>
  );
}
