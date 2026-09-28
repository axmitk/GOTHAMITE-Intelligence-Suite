import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { ArrowUpRight, RefreshCw } from "lucide-react";
import type {
  DatasetRecord,
  Entity,
  Evidence,
  Provenance,
  Risk,
} from "./types";

import { isTorExit, human, kindLabel, time, entityUrl } from "./formatters";

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
const provenanceLabel: Record<Provenance, string> = {
  synthetic: "Synthetic",
  dataset_derived: "Dataset-derived",
  reference_derived: "Reference reconstruction",
};
// Three provenance classes that must never be shown as the same thing.
export function ProvenanceBadge({ value }: { value?: string }) {
  const p = (value || "synthetic") as Provenance;
  return (
    <span className={`wb-badge wb-prov ${p}`}>
      {provenanceLabel[p] || value}
    </span>
  );
}
// Tor Project Onionoo observations carry relay context in their dataset record.
export function TorBadge() {
  return <span className="wb-badge wb-tor">TOR exit node</span>;
}
const yesNo = (v: unknown) => (v ? "Yes" : "No");
export function TorContext({ record }: { record?: DatasetRecord | null }) {
  const d = record?.details;
  if (!record || record.dataset !== "tor_project_onionoo" || !d) return null;
  return (
    <dl className="wb-metadata two-col wb-tor-context">
      <div>
        <dt>Exit node</dt>
        <dd>{yesNo(d.exit)}</dd>
      </div>
      <div>
        <dt>Running at snapshot</dt>
        <dd>{yesNo(d.running)}</dd>
      </div>
      <div>
        <dt>Relay</dt>
        <dd>
          {String(d.nickname)}{" "}
          <span className="wb-mono wb-break">{String(d.fingerprint)}</span>
        </dd>
      </div>
      <div>
        <dt>AS</dt>
        <dd>{String(d.as_name || "Not published")}</dd>
      </div>
      <div>
        <dt>First observed</dt>
        <dd>{d.first_seen ? time(String(d.first_seen)) : "Not published"}</dd>
      </div>
      <div>
        <dt>Last observed</dt>
        <dd>{d.last_seen ? time(String(d.last_seen)) : "Not published"}</dd>
      </div>
      <div>
        <dt>Source</dt>
        <dd>Tor Project Onionoo</dd>
      </div>
      <div>
        <dt>Snapshot</dt>
        <dd>{String(d.snapshot)}</dd>
      </div>
    </dl>
  );
}
export function DatasetProvenance({
  record,
}: {
  record?: DatasetRecord | null;
}) {
  if (!record) return null;
  return (
    <dl className="wb-metadata wb-dataset-record">
      <div>
        <dt>Dataset</dt>
        <dd>{record.dataset_name}</dd>
      </div>
      <div>
        <dt>Source record</dt>
        <dd className="wb-mono wb-break">{record.source_record_id}</dd>
      </div>
      <div>
        <dt>Dataset version</dt>
        <dd>{record.dataset_version}</dd>
      </div>
      <div>
        <dt>Licence</dt>
        <dd>
          {record.license}
          {record.doi ? ` · DOI ${record.doi}` : ""}
        </dd>
      </div>
      <div>
        <dt>Transformation</dt>
        <dd className="wb-mono">{record.transformation_version}</dd>
      </div>
      <div>
        <dt>Imported</dt>
        <dd>{time(record.imported_at)}</dd>
      </div>
    </dl>
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
              <span>
                {f.label}
                {f.dimension && (
                  <small className="wb-factor-dimension">{f.dimension}</small>
                )}
              </span>
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
                <ProvenanceBadge value={e.provenance} />
                {isTorExit(e) && <TorBadge />} {e.source}{" "}
                <span className="wb-dot">·</span> {time(e.observed_at)}
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
