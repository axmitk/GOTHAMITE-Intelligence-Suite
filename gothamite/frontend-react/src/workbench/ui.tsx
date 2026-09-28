import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { ArrowUpRight, RefreshCw } from "lucide-react";
import type { Entity, Evidence, Risk } from "./types";

import { human, kindLabel, time, entityUrl } from "./formatters";

// Badges use sentence case ("Pending review") so status language reads consistently.
export function Badge({
  value,
  tone,
  label,
}: {
  value: string;
  tone?: string;
  label?: string;
}) {
  const text = label ?? human(value);
  return (
    <span className={`wb-badge ${tone || value.toLowerCase()}`}>
      {text.charAt(0).toUpperCase() + text.slice(1)}
    </span>
  );
}
export function Heading({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children?: ReactNode;
}) {
  return (
    <div className="wb-heading">
      <div>
        <div className="wb-eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="wb-heading-actions">{children}</div>
    </div>
  );
}
export function Panel({
  title,
  meta,
  children,
  className = "",
}: {
  title: string;
  meta?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`wb-panel ${className}`}>
      <div className="wb-panel-head">
        <h2>{title}</h2>
        {meta}
      </div>
      {children}
    </section>
  );
}
export function ResourceState({
  loading,
  error,
  retry,
}: {
  loading?: boolean;
  error?: string;
  retry: () => void;
}) {
  return (
    <div
      className={`wb-resource ${error ? "is-error" : ""}`}
      role={error ? "alert" : "status"}
    >
      {error ? (
        <>
          <h2>Unable to load this view</h2>
          <p>{error}</p>
          <button className="wb-button" onClick={retry}>
            <RefreshCw size={14} /> Retry connection
          </button>
        </>
      ) : loading ? (
        <>
          <span className="wb-loader" />
          <p>Loading investigation data…</p>
        </>
      ) : (
        <p>No data available.</p>
      )}
    </div>
  );
}
export function EntityLink({ entity }: { entity: Entity }) {
  return (
    <Link className="wb-entity-link" to={entityUrl(entity)}>
      <span>
        <small>{kindLabel(entity.kind)}</small>
        <strong
          className={
            ["ip", "domain", "hash", "url", "email"].includes(entity.kind)
              ? "wb-mono"
              : ""
          }
        >
          {entity.label}
        </strong>
      </span>
      <ArrowUpRight size={14} />
    </Link>
  );
}
export function EvidenceRefs({
  ids,
  onInspect,
}: {
  ids: string[];
  onInspect: (id: string) => void;
}) {
  return (
    <div className="wb-refs">
      {ids.map((id) => (
        <button
          key={id}
          onClick={() => onInspect(id)}
          className="wb-evidence-ref"
        >
          {id}
        </button>
      ))}
    </div>
  );
}
export function RiskPanel({
  risk,
  onInspect,
}: {
  risk: Risk;
  onInspect: (id: string) => void;
}) {
  return (
    <Panel
      title="Risk factors"
      meta={<span className="wb-mono">BASELINE PRIORITY</span>}
    >
      <div className="wb-risk-summary">
        <span className={`wb-risk-value ${risk.level}`}>
          {risk.score}
          <small>/100</small>
        </span>
        <div>
          <Badge value={risk.level} />
          <p>Evidence-based priority</p>
        </div>
      </div>
      <div className="wb-risk-track">
        <span style={{ width: `${risk.score}%` }} />
      </div>
      <div className="wb-risk-factors">
        {risk.factors.map((f) => (
          <details key={f.label}>
            <summary>
              <span>{f.label}</span>
              <b>+{f.points}</b>
            </summary>
            <p>{f.reason}</p>
            <EvidenceRefs ids={f.evidence_ids} onInspect={onInspect} />
          </details>
        ))}
      </div>
      <p className="wb-footnote">{risk.method}</p>
      <p className="wb-footnote">{risk.limitation}</p>
    </Panel>
  );
}
export function EvidenceList({
  evidence,
  onInspect,
}: {
  evidence: Evidence[];
  onInspect: (id: string) => void;
}) {
  return (
    <div className="wb-evidence-list">
      {evidence.length ? (
        evidence.map((e, i) => (
          <button
            key={e.id}
            className="wb-evidence-row"
            onClick={() => onInspect(e.id)}
          >
            <span className="wb-row-number">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="wb-evidence-main">
              <strong>{e.title}</strong>
              <span>
                {e.source} <span className="wb-dot">·</span>{" "}
                {time(e.observed_at)}
              </span>
              <small className="wb-mono">{e.id}</small>
            </span>
            <ArrowUpRight size={15} />
          </button>
        ))
      ) : (
        <p className="wb-empty">
          Insufficient evidence. No observations are attached.
        </p>
      )}
    </div>
  );
}
