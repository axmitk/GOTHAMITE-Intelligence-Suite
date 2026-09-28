import { useState } from "react";
import { Check, ArrowRight } from "lucide-react";
import { Badge, EvidenceRefs, Panel } from "./ui";
import { human, time } from "./formatters";
import type { Action, Analysis, CaseData, NistMapping } from "./types";

export function AnalysisPanel({
  analysis,
  onInspect,
  onRun,
  busy,
}: {
  analysis: Analysis;
  onInspect: (id: string) => void;
  onRun: () => void;
  busy: boolean;
}) {
  return (
    <div className="wb-stack">
      <Panel
        title="Evidence analysis · offline rules"
        meta={
          <button className="wb-button" disabled={busy} onClick={onRun}>
            {busy ? "Analyzing…" : "Run evidence analysis"}
          </button>
        }
      >
        <div className="wb-analysis-summary">
          <span className="wb-eyebrow">
            AUTOMATED INTERPRETATION / OFFLINE RULES
          </span>
          <p>{analysis.summary}</p>
          <small>{analysis.provider}</small>
        </div>
      </Panel>
      {analysis.findings.map((f) => (
        <Panel
          key={f.id}
          title={f.title}
          meta={
            <Badge value={`${f.confidence} confidence`} tone={f.confidence} />
          }
        >
          <div className="wb-finding">
            <p>{f.interpretation}</p>
            <div className="wb-finding-grid">
              <div>
                <h4>Reasoning factors</h4>
                <ul>
                  {f.reasoning.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>Supporting evidence</h4>
                <EvidenceRefs ids={f.evidence_ids} onInspect={onInspect} />
              </div>
            </div>
            <div className="wb-next-investigation">
              <ArrowRight size={16} />
              <span>
                <strong>Recommended next step</strong>
                {f.next_step}
              </span>
            </div>
          </div>
        </Panel>
      ))}
      {!analysis.findings.length && (
        <p className="wb-empty">
          Insufficient evidence. No rule produced a finding for this case.
        </p>
      )}
      <div className="wb-callout">
        <strong>What remains uncertain</strong>
        <ul>
          {analysis.uncertainties.map((u) => (
            <li key={u}>{u}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ResponseCard({
  action,
  busy,
  onDecision,
  onInspect,
  closed,
}: {
  action: Action;
  busy: boolean;
  closed: boolean;
  onDecision: (rule: string, decision: string, reason: string) => void;
  onInspect: (id: string) => void;
}) {
  const [reason, setReason] = useState("");
  return (
    <div className="wb-response-card">
      <div className="wb-spread">
        <div className="wb-inline">
          <span className="wb-mono wb-muted">{action.priority}</span>
          <h3>{action.title}</h3>
        </div>
        <Badge value={action.status} />
      </div>
      <p>{action.reason}</p>
      <dl className="wb-response-meta">
        <div>
          <dt>Expected effect</dt>
          <dd>{action.effect}</dd>
        </div>
        <div>
          <dt>NIST mapping</dt>
          <dd className="wb-mono">{action.nist}</dd>
        </div>
      </dl>
      <EvidenceRefs ids={action.evidence_ids} onInspect={onInspect} />
      {action.status === "simulated" ? (
        <div className="wb-simulation-done">
          <Check size={15} />
          <span>Simulation recorded. No external system was changed.</span>
        </div>
      ) : closed ? (
        <p className="wb-footnote">
          Case closed. Response simulations are locked.
        </p>
      ) : (
        <>
          <label className="wb-field">
            Review note{" "}
            {action.status === "pending" ? "(required to reject)" : ""}
            <input
              aria-label={`Review note for ${action.title}`}
              maxLength={1000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Record your decision and any operational constraints…"
            />
          </label>
          <div className="wb-response-controls">
            {action.status === "approved" ? (
              <button
                className="wb-button primary"
                disabled={busy}
                onClick={() => onDecision(action.rule, "simulated", reason)}
              >
                Run simulation <ArrowRight size={14} />
              </button>
            ) : (
              <button
                className="wb-button"
                disabled={busy}
                onClick={() => onDecision(action.rule, "approved", reason)}
              >
                Approve recommendation
              </button>
            )}
            {action.status !== "rejected" && (
              <button
                className="wb-button quiet"
                disabled={busy || !reason.trim()}
                onClick={() => onDecision(action.rule, "rejected", reason)}
              >
                Reject
              </button>
            )}
            <small>Analyst approval required · simulation only</small>
          </div>
        </>
      )}
      {action.decision_note && (
        <p className="wb-footnote">Last review: {action.decision_note}</p>
      )}
    </div>
  );
}

export function ResponsePanel({
  data,
  busy,
  onDecision,
  onInspect,
}: {
  data: CaseData;
  busy: boolean;
  onDecision: (rule: string, decision: string, reason: string) => void;
  onInspect: (id: string) => void;
}) {
  const count = (status: string) =>
    data.actions.filter((a) => a.status === status).length;
  const trail = data.audit
    .filter(
      (e) => e.action.startsWith("response_") || e.action === "case_updated",
    )
    .slice()
    .reverse();
  return (
    <>
      <Panel
        title="Response recommendations"
        meta={<Badge value="Simulation only" tone="demo" />}
      >
        <div
          className="wb-decision-summary"
          aria-label="Response decision summary"
        >
          {[
            ["pending", "Awaiting review"],
            ["approved", "Approved"],
            ["simulated", "Simulated"],
            ["rejected", "Rejected"],
          ].map(([status, label]) => (
            <div key={status} className={count(status) ? "has-value" : ""}>
              <strong>{String(count(status)).padStart(2, "0")}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>
        <div className="wb-callout inset">
          <strong>Recommendation → analyst approval → simulation</strong>
          <p>
            Every recommendation comes from case evidence. Approving an action
            enables its simulation; neither step executes commands on real
            systems.
          </p>
        </div>
        {data.actions.map((a) => (
          <ResponseCard
            key={a.id}
            action={a}
            busy={busy}
            onDecision={onDecision}
            onInspect={onInspect}
            closed={data.status === "CLOSED"}
          />
        ))}
        {!data.actions.length && (
          <p className="wb-empty">
            Insufficient evidence to recommend a response.
          </p>
        )}
      </Panel>
      <Panel
        title="Decision audit trail"
        meta={<span className="wb-mono">{trail.length} EVENTS</span>}
      >
        <div className="wb-audit-list">
          {trail.map((e) => (
            <article key={e.id}>
              <time>{time(e.created_at)}</time>
              <div>
                <strong>{auditLabel(e.action)}</strong>
                <p>{e.detail}</p>
              </div>
              <small>{e.actor}</small>
            </article>
          ))}
          {!trail.length && (
            <p className="wb-empty">
              No response decisions recorded yet. Approvals, rejections and
              simulations appear here with the reviewing analyst.
            </p>
          )}
        </div>
      </Panel>
    </>
  );
}

const auditLabels: Record<string, string> = {
  response_approved: "Analyst approval",
  response_rejected: "Recommendation rejected",
  response_simulated: "Simulated action recorded",
  case_updated: "Case updated",
  note_added: "Notebook entry",
};
const auditLabel = (action: string) => auditLabels[action] || human(action);

export function NistPanel({
  mapping,
  onInspect,
  onOpenResponse,
}: {
  mapping: NistMapping[];
  onInspect: (id: string) => void;
  onOpenResponse: () => void;
}) {
  return (
    <Panel
      title="NIST CSF 2.0 alignment"
      meta={<span className="wb-mono">WORKFLOW MAPPING</span>}
    >
      <p className="wb-panel-intro">
        Each function cites the observations and response decisions behind it.
        Status updates as the analyst approves and simulates actions.
      </p>
      <div className="wb-nist-grid">
        {mapping.map((n, i) => (
          <article key={n.function}>
            <div className="wb-spread">
              <span className="wb-eyebrow">
                {String(i + 1).padStart(2, "0")} / {n.function}
              </span>
              <Badge value={n.status} />
            </div>
            <h3>{n.title}</h3>
            <code>{n.category}</code>
            <p>{n.activity}</p>
            <p className="wb-nist-basis">{n.basis}</p>
            {n.evidence_ids.length > 0 && (
              <div className="wb-nist-links">
                <h4>Supporting evidence</h4>
                <EvidenceRefs ids={n.evidence_ids} onInspect={onInspect} />
              </div>
            )}
            {n.actions.length > 0 && (
              <div className="wb-nist-links">
                <h4>Response activity</h4>
                <ul className="wb-nist-actions">
                  {n.actions.map((a) => (
                    <li key={a.rule}>
                      <button
                        className="wb-text-button"
                        onClick={onOpenResponse}
                      >
                        {a.title}
                      </button>
                      <Badge value={a.status} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        ))}
      </div>
      <p className="wb-footnote">
        These activities map to framework categories; they do not establish
        compliance.{" "}
        <a
          href="https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf"
          target="_blank"
          rel="noreferrer"
        >
          Official NIST CSF 2.0 Core ↗
        </a>
      </p>
    </Panel>
  );
}

export function TimelinePanel({
  data,
  onInspect,
}: {
  data: CaseData;
  onInspect: (id: string) => void;
}) {
  const [filter, setFilter] = useState("all");
  const entries = [
    ...data.evidence.map((e) => ({
      id: e.id,
      at: e.observed_at,
      title: e.title,
      detail: e.source,
      kind: "observation",
    })),
    ...data.audit.map((e) => ({
      id: e.id,
      at: e.created_at,
      title: human(e.action),
      detail: e.detail,
      kind: "analyst",
    })),
  ]
    .filter((e) => filter === "all" || e.kind === filter)
    .sort((a, b) => a.at.localeCompare(b.at));
  return (
    <Panel
      title="Investigation timeline"
      meta={<span className="wb-mono">UTC / CHRONOLOGICAL</span>}
    >
      <div className="wb-filterbar">
        {["all", "observation", "analyst"].map((f) => (
          <button
            key={f}
            className={filter === f ? "selected" : ""}
            onClick={() => setFilter(f)}
          >
            {f === "all"
              ? "All activity"
              : f === "analyst"
                ? "Analyst decisions"
                : "Observations"}
          </button>
        ))}
      </div>
      <div className="wb-timeline">
        {entries.map((e) => (
          <article key={e.id}>
            <span className="wb-timeline-dot" />
            <time>{time(e.at)}</time>
            <div>
              <h3>{e.title}</h3>
              <p>{e.detail}</p>
              {e.kind === "observation" ? (
                <button
                  className="wb-evidence-ref"
                  onClick={() => onInspect(e.id)}
                >
                  {e.id}
                </button>
              ) : (
                <Badge value="Analyst activity" />
              )}
            </div>
          </article>
        ))}
        {!entries.length && (
          <p className="wb-empty">No activity in this category yet.</p>
        )}
      </div>
    </Panel>
  );
}

export function NotesPanel({
  data,
  busy,
  onAdd,
}: {
  data: CaseData;
  busy: boolean;
  onAdd: (kind: string, text: string) => Promise<boolean>;
}) {
  const [text, setText] = useState("");
  const [kind, setKind] = useState("note");
  return (
    <Panel
      title="Analyst notebook"
      meta={<span className="wb-count">{data.notes.length}</span>}
    >
      <form
        className="wb-note-form"
        onSubmit={async (e) => {
          e.preventDefault();
          if (await onAdd(kind, text)) setText("");
        }}
      >
        <label className="wb-field">
          Entry type
          <select
            aria-label="Entry type"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            <option value="note">Analyst note</option>
            <option value="hypothesis">Hypothesis</option>
            <option value="recovery">Recovery validation</option>
            <option value="lesson">Lesson learned</option>
          </select>
        </label>
        <label className="wb-field">
          Investigation note
          <textarea
            aria-label="Investigation note"
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={4000}
            rows={4}
            placeholder="Record what you know, what is uncertain, and what to validate next…"
            required
          />
        </label>
        <button
          className="wb-button full"
          disabled={busy || !text.trim()}
          type="submit"
        >
          Save entry
        </button>
      </form>
      <div className="wb-notes">
        {[...data.notes].reverse().map((n) => (
          <article key={n.id}>
            <div className="wb-spread">
              <Badge value={n.kind} />
              <small>{time(n.created_at)}</small>
            </div>
            <p>{n.text}</p>
            <small>{n.author}</small>
          </article>
        ))}
        {!data.notes.length && (
          <p className="wb-empty">
            No analyst conclusions yet. Add your first observation or
            hypothesis.
          </p>
        )}
      </div>
    </Panel>
  );
}
