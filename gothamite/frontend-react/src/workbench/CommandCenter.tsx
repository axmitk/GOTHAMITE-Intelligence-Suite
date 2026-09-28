import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ArrowUpRight, RefreshCw } from "lucide-react";
import { useResource } from "./api";
import { Badge, Heading, Panel, ResourceState } from "./ui";
import { time } from "./formatters";
import { EvidenceDrawer } from "./EvidenceDrawer";
import type { DashboardData, CaseSummary } from "./types";

export function CaseTable({ cases }: { cases: CaseSummary[] }) {
  return (
    <div className="wb-table-wrap">
      <table className="wb-table">
        <thead>
          <tr>
            <th>Investigation</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Scope</th>
            <th className="wb-align-right">Risk</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id}>
              <td>
                <Link className="wb-case-link" to={`/investigations/${c.id}`}>
                  <small className="wb-mono">{c.id}</small>
                  <strong>{c.title}</strong>
                </Link>
              </td>
              <td>
                <Badge value={c.severity} />
              </td>
              <td>
                <span className="wb-status">
                  <i />
                  {c.status.replaceAll("_", " ").toLowerCase()}
                </span>
              </td>
              <td>
                <span className="wb-nowrap">{c.asset_count} assets</span>
                <small>{c.evidence_count} observations</small>
              </td>
              <td className="wb-align-right">
                <span className={`wb-score ${c.risk.level}`}>
                  {c.risk.score}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!cases.length && (
        <p className="wb-empty">No investigations match this filter.</p>
      )}
    </div>
  );
}

export function CommandCenter({ listOnly = false }: { listOnly?: boolean }) {
  const { data, loading, error, reload } =
    useResource<DashboardData>("/dashboard");
  const [filter, setFilter] = useState("all");
  const [inspect, setInspect] = useState<string | null>(null);
  if (!data)
    return <ResourceState loading={loading} error={error} retry={reload} />;
  const priority = [...data.cases]
    .filter((c) => c.status !== "CLOSED")
    .sort((a, b) => b.risk.score - a.risk.score)[0];
  const cases = data.cases.filter(
    (c) =>
      filter === "all" ||
      (filter === "active" ? c.status !== "CLOSED" : c.severity === filter),
  );
  const maxActivity = Math.max(1, ...data.activity.map((a) => a.count));
  return (
    <>
      <Heading
        eyebrow={
          listOnly
            ? "Operations / case management"
            : "Workspace / operational overview"
        }
        title={listOnly ? "Investigations" : "Command center"}
        subtitle={
          listOnly
            ? "Review supporting observations, case status and recorded response decisions."
            : "Prioritized investigations, supporting observations and analyst decisions."
        }
      >
        {!listOnly && (
          <Link className="wb-canonical-ioc" to="/intelligence?q=203.0.113.42">
            <small>REFERENCE IOC</small>
            <span className="wb-mono">203.0.113.42 ↗</span>
          </Link>
        )}
        <button className="wb-button" onClick={reload} disabled={loading}>
          <RefreshCw size={14} />
          Refresh
        </button>
        {priority && (
          <Link
            className="wb-button primary"
            to={`/investigations/${priority.id}`}
          >
            Open priority case <ArrowUpRight size={15} />
          </Link>
        )}
      </Heading>
      {!listOnly && (
        <>
          <div className="wb-pipeline">
            {[
              "Collect",
              "Enrich",
              "Correlate",
              "Analyze",
              "Prioritize",
              "Investigate",
              "Respond",
              "Learn",
            ].map((s, i) => (
              <span key={s} className={i === 5 ? "active" : ""}>
                <small>{String(i + 1).padStart(2, "0")}</small>
                {s}
                {i < 7 && <span className="wb-pipeline-arrow">→</span>}
              </span>
            ))}
          </div>
          <div className="wb-metrics">
            <div>
              <span>Open investigations</span>
              <strong>{String(data.active_cases).padStart(2, "0")}</strong>
              <small>Cases not yet closed · synthetic exercise</small>
            </div>
            <div>
              <span>Open critical cases</span>
              <strong className="critical">
                {String(data.critical_cases).padStart(2, "0")}
              </strong>
              <small>Severity critical, awaiting analyst decision</small>
            </div>
            <div>
              <span>Indicators (IOCs)</span>
              <strong>{data.indicators}</strong>
              <small>
                {data.provenance
                  ? `${data.provenance.indicators.synthetic || 0} synthetic · ${data.provenance.indicators.dataset_derived || 0} dataset-derived`
                  : "Synthetic IP, domain, hash, URL and email records"}
              </small>
            </div>
            <div>
              <span>Evidence-backed relationships</span>
              <strong>{data.relationships}</strong>
              <small>
                Each cites one of {data.evidence_count} observations (
                {data.provenance?.evidence.dataset_derived || 0}{" "}
                dataset-derived)
              </small>
            </div>
          </div>
        </>
      )}
      <div className={listOnly ? "" : "wb-dashboard-grid"}>
        <div className="wb-stack">
          <Panel
            title="Investigation queue"
            meta={<span className="wb-count">{cases.length} cases</span>}
          >
            <div className="wb-filterbar" aria-label="Filter investigations">
              {[
                ["all", "All cases"],
                ["active", "Active"],
                ["critical", "Critical"],
                ["high", "High"],
              ].map(([v, l]) => (
                <button
                  key={v}
                  className={filter === v ? "selected" : ""}
                  onClick={() => setFilter(v)}
                >
                  {l}
                </button>
              ))}
            </div>
            <CaseTable cases={cases} />
            <div className="wb-panel-footer">
              <span>
                Baseline risk sums evidenced factors; each factor cites its
                observations.
              </span>
              <Link to="/intelligence">
                Search intelligence <ArrowRight size={13} />
              </Link>
            </div>
          </Panel>
          {!listOnly && (
            <Panel
              title="Observation timeline"
              meta={<span className="wb-mono">EXERCISE / 28 SEP 2026</span>}
            >
              <div className="wb-activity-layout">
                <div className="wb-activity-number">
                  <strong>{data.evidence_count}</strong>
                  <span>recorded observations</span>
                  <small>Fixed scenario timeline · UTC</small>
                </div>
                <div
                  className="wb-bar-chart"
                  aria-label="Observation counts by half-hour"
                >
                  {data.activity.map((a) => (
                    <div key={a.time}>
                      <span>{a.count}</span>
                      <i
                        style={{
                          height: `${Math.max(4, (a.count / maxActivity) * 78)}px`,
                        }}
                      />
                      <small>{a.time}</small>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>
          )}
        </div>
        {!listOnly && (
          <aside className="wb-stack">
            <Panel
              title="Priority briefing"
              meta={<span className="wb-live-label">ANALYST REVIEW</span>}
            >
              {priority ? (
                <div className="wb-briefing">
                  <div className="wb-spread">
                    <span className="wb-mono">{priority.id}</span>
                    <Badge value={priority.severity} />
                  </div>
                  <h3>{priority.title}</h3>
                  <p>
                    {priority.risk.factors
                      .slice(0, 3)
                      .map((f) => f.label)
                      .join(" · ")}
                    .
                  </p>
                  <div className="wb-briefing-score">
                    <span>
                      {priority.risk.score}
                      <small>/100</small>
                    </span>
                    <div>
                      Baseline risk
                      <br />
                      <small>
                        {priority.evidence_count} supporting observations
                      </small>
                    </div>
                  </div>
                  <Link
                    className="wb-button full"
                    to={`/investigations/${priority.id}`}
                  >
                    Continue investigation <ArrowRight size={15} />
                  </Link>
                </div>
              ) : (
                <p className="wb-empty">All investigations are closed.</p>
              )}
            </Panel>
            <Panel
              title="Observations by source"
              meta={<Badge value="Synthetic" tone="demo" />}
            >
              <div className="wb-sources">
                {data.sources.map((s) => (
                  <div key={s.name}>
                    <span>
                      <i />
                      {s.name.replace("Synthetic ", "")}
                    </span>
                    <b className="wb-mono">{s.count}</b>
                  </div>
                ))}
              </div>
              <p className="wb-footnote">
                Counts are synthetic exercise observations per source;
                dataset-derived records are counted above. No live connector is
                attached; a deployment would ingest through scheduled source
                adapters.
              </p>
            </Panel>
          </aside>
        )}
      </div>
      {!listOnly && (
        <Panel
          title="Latest exercise observations"
          meta={
            <Link to="/intelligence">
              Open indicator catalog <ArrowUpRight size={13} />
            </Link>
          }
        >
          <div className="wb-recent">
            {data.recent.slice(0, 3).map((e) => (
              <button key={e.id} onClick={() => setInspect(e.id)}>
                <small className="wb-mono">{time(e.observed_at)}</small>
                <strong>{e.title}</strong>
                <span>
                  {e.source}
                  <ArrowUpRight size={13} />
                </span>
              </button>
            ))}
          </div>
        </Panel>
      )}
      {inspect && (
        <EvidenceDrawer id={inspect} onClose={() => setInspect(null)} />
      )}
    </>
  );
}
