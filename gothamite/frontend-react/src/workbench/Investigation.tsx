import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowRight, Download, RefreshCw } from "lucide-react";
import { api, downloadReport, useResource } from "./api";
import {
  Badge,
  EntityLink,
  EvidenceList,
  Heading,
  Panel,
  ResourceState,
  RiskPanel,
} from "./ui";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { RelationshipGraph } from "./RelationshipGraph";
import {
  AnalysisPanel,
  NotesPanel,
  NistPanel,
  ResponsePanel,
  TimelinePanel,
} from "./CasePanels";
import type { Analysis, CaseData, DashboardData } from "./types";

const tabs = [
  ["evidence", "Evidence"],
  ["graph", "Graph"],
  ["analysis", "Analysis"],
  ["nist", "NIST alignment"],
  ["response", "Response"],
  ["timeline", "Timeline"],
  ["report", "Report"],
];

function ReportPreview({ caseData }: { caseData: CaseData }) {
  const { id } = caseData;
  const { data, loading, error, reload } = useResource<string>(
    `/cases/${id}/report`,
  );
  const sections =
    data
      ?.split(/^## /m)
      .slice(1)
      .map((section) => {
        const [title, ...body] = section.trim().split("\n");
        // The export escapes Markdown/HTML in analyst text; React renders the preview as plain text.
        const text = body
          .join("\n")
          .trim()
          .replace(/\\([[\]#])/g, "$1")
          .replaceAll("&lt;", "<")
          .replaceAll("&gt;", ">");
        return { title, body: text.split(/\n\n+/) };
      }) || [];
  return (
    <Panel
      title="Investigation report"
      meta={<Badge value="Synthetic exercise" tone="demo" />}
    >
      {data ? (
        <div className="wb-report-preview">
          <div className="wb-report-cover">
            <span className="wb-eyebrow">
              {id} / INVESTIGATION RECORD / V{caseData.version}
            </span>
            <h3>{caseData.title}</h3>
            <p>
              Generated from the saved investigation trail: observations,
              correlated context, interpretation and analyst decisions.
            </p>
            <div className="wb-inline">
              <Badge value={caseData.status} />
              <span>
                {caseData.evidence.length} observations ·{" "}
                {caseData.audit.length} analyst events
              </span>
            </div>
          </div>
          <div className="wb-report-body">
            <nav className="wb-report-index" aria-label="Report sections">
              {sections.map((section, i) => (
                <a key={section.title} href={`#report-section-${i}`}>
                  <small>{String(i + 1).padStart(2, "0")}</small>
                  {section.title.replace(/\s*\(.+\)/, "")}
                </a>
              ))}
              <p>
                Automated interpretation uses offline evidence rules; no
                language model is involved. Response actions are simulations.
              </p>
            </nav>
            <div>
              {sections.map((section, i) => (
                <section
                  className="wb-report-section"
                  id={`report-section-${i}`}
                  key={section.title}
                >
                  <h3>
                    <span>{String(i + 1).padStart(2, "0")}</span>
                    {section.title}
                  </h3>
                  {section.body.map((paragraph, j) =>
                    paragraph.startsWith("### ") ? (
                      <h4 key={j}>{paragraph.slice(4)}</h4>
                    ) : (
                      <p
                        className={
                          paragraph.startsWith("- ") ? "wb-report-item" : ""
                        }
                        key={j}
                      >
                        {paragraph}
                      </p>
                    ),
                  )}
                </section>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <ResourceState loading={loading} error={error} retry={reload} />
      )}
    </Panel>
  );
}

export function Investigation() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = params.get("view") || "evidence";
  const { data, loading, error, reload, setData } = useResource<CaseData>(
    `/cases/${encodeURIComponent(id)}`,
  );
  const [inspect, setInspect] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{
    text: string;
    error: boolean;
  } | null>(null);
  const [analyst, setAnalyst] = useState("");
  if (!data)
    return <ResourceState loading={loading} error={error} retry={reload} />;
  const current = data;
  const next = current.advance.next;
  const blocked = Boolean(next && !current.advance.ready);
  // Every stage prerequisite is resolved from response review (plus the notebook).
  const resolveView = "response";
  function openView(view: string) {
    window.scrollTo(0, 0);
    setParams({ view });
  }
  async function mutate(
    path: string,
    body: Record<string, unknown>,
    method = "POST",
  ) {
    setBusy(true);
    setMessage(null);
    try {
      const updated = await api<CaseData>(`/cases/${id}${path}`, {
        method,
        body: JSON.stringify({ ...body, version: current.version }),
      });
      setData(updated);
      setMessage({
        text: "Case updated. Decision saved to the audit trail.",
        error: false,
      });
      return true;
    } catch (e) {
      setMessage({
        text: e instanceof Error ? e.message : "Could not save your change.",
        error: true,
      });
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function exportReport() {
    setBusy(true);
    try {
      await downloadReport(id);
      setMessage({ text: "Investigation report downloaded.", error: false });
    } catch (e) {
      setMessage({
        text: e instanceof Error ? e.message : "Report download failed.",
        error: true,
      });
    } finally {
      setBusy(false);
    }
  }
  async function runAnalysis() {
    setBusy(true);
    try {
      const analysis = await api<Analysis>("/analysis", {
        method: "POST",
        body: JSON.stringify({ entity_id: id }),
      });
      setData({ ...current, analysis });
      setMessage({
        text: "Evidence rules evaluated. Findings reference only the attached observations.",
        error: false,
      });
    } catch (e) {
      setMessage({
        text: e instanceof Error ? e.message : "Analysis failed.",
        error: true,
      });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Link className="wb-back" to="/investigations">
        ← Investigation queue
      </Link>
      <Heading
        eyebrow={`Investigation / ${id}`}
        title={current.title}
        subtitle="Supporting observations, correlated context and accountable response decisions."
      >
        <button
          className="wb-icon-button"
          aria-label="Refresh case"
          disabled={busy}
          onClick={reload}
        >
          <RefreshCw size={16} />
        </button>
        <button
          className={`wb-button ${tab === "report" ? "primary" : ""}`}
          disabled={busy}
          onClick={exportReport}
        >
          <Download size={14} />
          Export report
        </button>
        {next && (
          <button
            className={`wb-button ${blocked ? "" : "primary"}`}
            disabled={busy || blocked}
            title={blocked ? current.advance.requirement : undefined}
            onClick={() => mutate("", { status: next }, "PATCH")}
          >
            Advance to {next.toLowerCase()} <ArrowRight size={14} />
          </button>
        )}
      </Heading>
      <div className="wb-case-meta">
        <Badge value={current.status} />
        <label>
          Severity{" "}
          <select
            aria-label="Case severity"
            disabled={busy}
            value={current.severity}
            onChange={(e) => mutate("", { severity: e.target.value }, "PATCH")}
          >
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (analyst.trim()) void mutate("", { analyst }, "PATCH");
          }}
        >
          <label>
            Assigned to{" "}
            <input
              aria-label="Assigned analyst"
              placeholder={current.analyst}
              value={analyst}
              onChange={(e) => setAnalyst(e.target.value)}
              maxLength={80}
            />
          </label>
          <button
            type="submit"
            className="wb-text-button"
            disabled={busy || !analyst.trim()}
          >
            Assign
          </button>
        </form>
        <span className="wb-mono">VERSION {current.version}</span>
        <Badge value="Synthetic" tone="demo" />
      </div>
      <div className="wb-case-stages">
        {current.states.map((s, i) => (
          <span
            key={s}
            className={
              s === current.status
                ? "current"
                : i < current.states.indexOf(current.status)
                  ? "complete"
                  : ""
            }
          >
            <i>
              {i < current.states.indexOf(current.status)
                ? "✓"
                : String(i + 1).padStart(2, "0")}
            </i>
            {s.toLowerCase()}
          </span>
        ))}
      </div>
      {blocked && next && (
        <div className="wb-stage-gate" role="note">
          <span className="wb-eyebrow">Next stage · {next.toLowerCase()}</span>
          <p>{current.advance.requirement}</p>
          {tab !== resolveView && (
            <button
              className="wb-text-button"
              onClick={() => openView(resolveView)}
            >
              Review response recommendations →
            </button>
          )}
        </div>
      )}
      {message && (
        <div
          className={`wb-message ${message.error ? "error" : "success"}`}
          role={message.error ? "alert" : "status"}
        >
          {message.text}
          {message.error && (
            <button className="wb-text-button" onClick={reload}>
              Refresh case
            </button>
          )}
        </div>
      )}
      <div className="wb-tabs" aria-label="Investigation sections">
        {tabs.map(([value, label]) => (
          <button
            key={value}
            className={tab === value ? "selected" : ""}
            onClick={() => setParams({ view: value })}
          >
            {label}
            {value === "evidence" && <small>{current.evidence.length}</small>}
          </button>
        ))}
      </div>
      {tab === "graph" ? (
        <RelationshipGraph key={id} root={id} onInspect={setInspect} />
      ) : (
        <div
          className={`wb-investigation-grid ${tab === "report" ? "wb-report-layout" : ""}`}
        >
          <div className="wb-stack">
            {tab === "evidence" && (
              <>
                <Panel
                  title="Observed evidence"
                  meta={
                    <span className="wb-mono">
                      {current.evidence.length} OBSERVATIONS
                    </span>
                  }
                >
                  <p className="wb-panel-intro">
                    Inspect the recorded observation and its integrity hash
                    before interpreting the activity.
                  </p>
                  <EvidenceList
                    evidence={current.evidence}
                    onInspect={setInspect}
                  />
                </Panel>
                <Panel
                  title="Investigation scope"
                  meta={
                    <button
                      className="wb-text-button"
                      onClick={() => setParams({ view: "graph" })}
                    >
                      Explore relationships →
                    </button>
                  }
                >
                  <div className="wb-scope-grid">
                    {current.entities
                      .filter((e) =>
                        [
                          "asset",
                          "ip",
                          "domain",
                          "threat_actor",
                          "campaign",
                          "malware",
                        ].includes(e.kind),
                      )
                      .map((e) => (
                        <EntityLink key={e.id} entity={e} />
                      ))}
                  </div>
                </Panel>
              </>
            )}
            {tab === "analysis" && (
              <AnalysisPanel
                analysis={current.analysis}
                onInspect={setInspect}
                onRun={runAnalysis}
                busy={busy}
              />
            )}
            {tab === "nist" && (
              <NistPanel
                mapping={current.nist}
                onInspect={setInspect}
                onOpenResponse={() => {
                  window.scrollTo(0, 0);
                  setParams({ view: "response" });
                }}
              />
            )}
            {tab === "response" && (
              <ResponsePanel
                data={current}
                busy={busy}
                onDecision={(rule, decision, reason) => {
                  void mutate(`/actions/${rule}`, { decision, reason });
                }}
                onInspect={setInspect}
              />
            )}
            {tab === "timeline" && (
              <TimelinePanel data={current} onInspect={setInspect} />
            )}
            {tab === "report" && (
              <ReportPreview
                key={`${id}-${current.version}`}
                caseData={current}
              />
            )}
          </div>
          {tab !== "report" && (
            <aside className="wb-stack">
              <RiskPanel risk={current.risk} onInspect={setInspect} />
              <NotesPanel
                data={current}
                busy={busy}
                onAdd={(kind, text) => mutate("/notes", { kind, text })}
              />
            </aside>
          )}
        </div>
      )}
      {tab !== "report" && (
        <div className="wb-continuation">
          <div>
            <span className="wb-eyebrow">Continue the investigation</span>
            <p>
              {tab === "analysis"
                ? "Review the cited risk factors, then inspect the framework mapping."
                : tab === "response"
                  ? "The report includes every approval, simulation and analyst entry recorded here."
                  : tab === "nist"
                    ? "Review the evidence behind each response recommendation before approval."
                    : "Follow the recorded observations through correlated context and interpretation."}
            </p>
          </div>
          <button
            className="wb-button"
            onClick={() => {
              window.scrollTo(0, 0);
              setParams({
                view:
                  tab === "evidence"
                    ? "graph"
                    : tab === "graph"
                      ? "analysis"
                      : tab === "analysis"
                        ? "nist"
                        : tab === "nist"
                          ? "response"
                          : "report",
              });
            }}
          >
            {tab === "evidence"
              ? "Open correlation graph"
              : tab === "graph"
                ? "Continue to analysis"
                : tab === "analysis"
                  ? "Review NIST alignment"
                  : tab === "nist"
                    ? "Review response recommendations"
                    : "Review investigation report"}{" "}
            <ArrowRight size={14} />
          </button>
        </div>
      )}
      {inspect && (
        <EvidenceDrawer id={inspect} onClose={() => setInspect(null)} />
      )}
    </>
  );
}

export function Reports() {
  const { data, loading, error, reload } =
    useResource<DashboardData>("/dashboard");
  const [errorMessage, setError] = useState("");
  if (!data)
    return <ResourceState loading={loading} error={error} retry={reload} />;
  return (
    <>
      <Heading
        eyebrow="Output / analyst reporting"
        title="Investigation reports"
        subtitle="Reports assembled from saved evidence, correlated context, risk factors and analyst approvals."
      />
      {errorMessage && (
        <div className="wb-message error" role="alert">
          {errorMessage}
        </div>
      )}
      <Panel title="Case reports" meta={<Badge value="Markdown export" />}>
        <div className="wb-report-list">
          {data.cases.map((c) => (
            <article key={c.id}>
              <div>
                <small className="wb-mono">{c.id}</small>
                <h3>{c.title}</h3>
                <Badge value={c.status} />
              </div>
              <div className="wb-inline">
                <Link
                  className="wb-button"
                  to={`/investigations/${c.id}?view=report`}
                >
                  View report
                </Link>
                <button
                  className="wb-button"
                  onClick={() =>
                    downloadReport(c.id).catch((e) => setError(e.message))
                  }
                >
                  <Download size={14} />
                  Download
                </button>
              </div>
            </article>
          ))}
        </div>
      </Panel>
    </>
  );
}

export function NistOverview() {
  const { data, loading, error, reload } =
    useResource<DashboardData>("/dashboard");
  if (!data)
    return <ResourceState loading={loading} error={error} retry={reload} />;
  return (
    <>
      <Heading
        eyebrow="Governance / NIST CSF 2.0"
        title="Framework alignment"
        subtitle="Follow each case from accountable ownership to documented recovery."
      />
      <div className="wb-callout">
        Case activities map to Govern, Identify, Protect, Detect, Respond and
        Recover. This is an investigation aid, not a compliance assessment.
      </div>
      <Panel title="Case-level alignment">
        <div className="wb-report-list">
          {data.cases.map((c) => (
            <article key={c.id}>
              <div>
                <small className="wb-mono">{c.id}</small>
                <h3>{c.title}</h3>
                <Badge value={c.status} />
              </div>
              <Link
                className="wb-button"
                to={`/investigations/${c.id}?view=nist`}
              >
                Inspect NIST mapping <ArrowRight size={14} />
              </Link>
            </article>
          ))}
        </div>
      </Panel>
    </>
  );
}
