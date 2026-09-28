import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowRight, ArrowUpRight, Search } from "lucide-react";
import { useResource } from "./api";
import {
  Badge,
  Heading,
  Panel,
  ResourceState,
  EntityLink,
  EvidenceList,
  ProvenanceBadge,
  DatasetProvenance,
  TorBadge,
  TorContext,
} from "./ui";
import {
  human,
  kindLabel,
  plural,
  time,
  entityUrl,
  isTorExit,
} from "./formatters";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { RelationshipGraph } from "./RelationshipGraph";
import type { Profile, SearchResult } from "./types";

const catalogs: Record<
  string,
  { title: string; subtitle: string; kind: string }
> = {
  intelligence: {
    title: "Threat intelligence",
    subtitle:
      "Indicators and correlated entities with supporting observations and provenance.",
    kind: "",
  },
  actors: {
    title: "Threat actors",
    subtitle:
      "Fictional activity clusters with visible campaign associations and uncertainty.",
    kind: "threat_actor",
  },
  assets: {
    title: "Asset inventory",
    subtitle:
      "Business context and affected services, connected to their investigations.",
    kind: "asset",
  },
  darkweb: {
    title: "Dark-web intelligence",
    subtitle:
      "Dark-web source observations: synthetic exposure mentions, dataset-derived forum threads and marketplace listings, each with source, confidence, provenance and corroboration status.",
    kind: "darkweb_mention",
  },
};

export function Intelligence({
  catalog = "intelligence",
}: {
  catalog?: string;
}) {
  const config = catalogs[catalog];
  const [params, setParams] = useSearchParams();
  const query = params.get("q") || "";
  // The dark-web view offers its own source-type tabs over one observation model.
  const kind =
    (catalog === "darkweb" ? params.get("kind") : null) ||
    config.kind ||
    params.get("kind") ||
    "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [draft, setDraft] = useState(query);
  const { data, loading, error, reload } = useResource<SearchResult>(
    `/search?q=${encodeURIComponent(query)}&kind=${kind}&page=${page}`,
  );
  function change(values: Record<string, string>) {
    setParams({ q: query, kind, ...values });
  }
  return (
    <>
      <Heading
        eyebrow="Intelligence / entity catalog"
        title={config.title}
        subtitle={config.subtitle}
      >
        <Badge value="Synthetic and dataset-derived" tone="demo" />
      </Heading>
      <form
        className="wb-catalog-search"
        onSubmit={(e) => {
          e.preventDefault();
          change({ q: draft.trim(), page: "1" });
        }}
      >
        <Search size={18} />
        <input
          aria-label="Search intelligence"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="IP, domain, hash, actor, campaign, asset or incident…"
        />
        <button className="wb-button primary" type="submit">
          Search
        </button>
      </form>
      {catalog === "darkweb" && (
        <div className="wb-callout">
          <strong>Source claims require corroboration.</strong> Confidence
          describes the synthetic source annotation, not proof of exposure or
          compromise. Open a record to inspect its provenance and supporting
          observations.
          <dl className="wb-collection-model">
            <div>
              <dt>Implemented prototype</dt>
              <dd>
                Synthetic source observations loaded from a reproducible seed.
                No dark-web network is contacted. The companion darkweb-sandbox
                collects mock hidden-service pages over a simulated relay
                network.
              </dd>
            </div>
            <div>
              <dt>Deployment architecture</dt>
              <dd>
                Source adapters → scheduled ingestion → raw observations →
                normalization → entity extraction → correlation → analyst
                review.
              </dd>
            </div>
          </dl>
        </div>
      )}
      <div className="wb-catalog-toolbar">
        <div className="wb-filterbar">
          {catalog === "darkweb" &&
            [
              ["darkweb_mention", "Exposure mentions"],
              ["forum_thread", "Forum threads"],
              ["market_listing", "Marketplace listings"],
            ].map(([v, l]) => (
              <button
                key={v}
                className={kind === v ? "selected" : ""}
                onClick={() => change({ kind: v, page: "1" })}
              >
                {l}
              </button>
            ))}
          {!config.kind &&
            [
              ["", "All entities"],
              ["indicator", "Indicators"],
              ["campaign", "Campaigns"],
              ["asset", "Assets"],
              ["vulnerability", "Vulnerabilities"],
            ].map(([v, l]) => (
              <button
                key={v}
                className={kind === v ? "selected" : ""}
                onClick={() => change({ kind: v, page: "1" })}
              >
                {l}
              </button>
            ))}
        </div>
        <span className="wb-muted">
          {data ? plural(data.total, "result") : "Searching…"}
        </span>
      </div>
      {!data ? (
        <ResourceState loading={loading} error={error} retry={reload} />
      ) : (
        <Panel
          title={query ? `Results for “${query}”` : "Intelligence catalog"}
          meta={<span className="wb-mono">{data.total} ENTITIES</span>}
        >
          <div className="wb-table-wrap">
            <table className="wb-table">
              <thead>
                <tr>
                  <th>Entity / indicator</th>
                  <th>Type</th>
                  <th>Source</th>
                  <th>Last observed</th>
                  <th>Confidence annotation</th>
                  <th>
                    {catalog === "darkweb" ? "Corroboration" : "Provenance"}
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <Link to={entityUrl(e)} className="wb-case-link">
                        <strong className="wb-truncate wb-mono">
                          {e.label}
                        </strong>
                        <small>{e.id}</small>
                      </Link>
                    </td>
                    <td>{kindLabel(e.kind)}</td>
                    <td>{e.source}</td>
                    <td className="wb-mono wb-nowrap">{time(e.last_seen)}</td>
                    <td>
                      <span className="wb-confidence">
                        <i style={{ width: `${e.confidence * 56}px` }} />
                        {e.confidence.toFixed(2)}
                      </span>
                    </td>
                    <td className="wb-prov-cell">
                      <ProvenanceBadge value={e.provenance} />
                      {catalog === "darkweb" && (
                        <Badge value="Unverified claim" tone="demo" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data.results.length && (
            <div className="wb-empty">
              <h3>No matching intelligence</h3>
              <p>
                This indicator is not in the exercise dataset. Unknown does not
                mean benign.
              </p>
              <Link to="/intelligence?q=203.0.113.42">
                Inspect reference IOC: 203.0.113.42 <ArrowRight size={13} />
              </Link>
            </div>
          )}
          <div className="wb-pagination">
            <span>
              Page {page} of {Math.max(1, Math.ceil(data.total / data.limit))}
            </span>
            <div>
              <button
                className="wb-button"
                disabled={page <= 1}
                onClick={() => change({ page: String(page - 1) })}
              >
                Previous
              </button>
              <button
                className="wb-button"
                disabled={page * data.limit >= data.total}
                onClick={() => change({ page: String(page + 1) })}
              >
                Next
              </button>
            </div>
          </div>
        </Panel>
      )}
    </>
  );
}

export function EntityProfile() {
  const { id = "" } = useParams();
  const { data, loading, error, reload } = useResource<Profile>(
    `/entities/${encodeURIComponent(id)}`,
  );
  const [tab, setTab] = useState("overview");
  const [inspect, setInspect] = useState<string | null>(null);
  function showTab(value: string) {
    setTab(value);
    window.scrollTo(0, 0);
  }
  if (!data)
    return <ResourceState loading={loading} error={error} retry={reload} />;
  const { entity } = data;
  const tor = data.evidence.filter(
    (e) => e.dataset_record?.dataset === "tor_project_onionoo",
  );
  return (
    <>
      <Link to="/intelligence" className="wb-back">
        ← Intelligence catalog
      </Link>
      <Heading
        eyebrow={`Intelligence / ${kindLabel(entity.kind)} / ${entity.id}`}
        title={entity.label}
        subtitle={entity.summary}
      >
        <ProvenanceBadge value={entity.provenance} />
        {entity.kind === "ip" && tor.some(isTorExit) && <TorBadge />}
      </Heading>
      <div className="wb-tabs">
        {["overview", "relationships"].map((t) => (
          <button
            key={t}
            className={tab === t ? "selected" : ""}
            onClick={() => showTab(t)}
          >
            {t === "overview" ? "Intelligence profile" : "Relationship graph"}
          </button>
        ))}
      </div>
      {tab === "relationships" ? (
        <RelationshipGraph
          key={id}
          root={id}
          caseId={data.related_cases[0]?.id}
          onInspect={setInspect}
        />
      ) : (
        <div className="wb-profile-grid">
          <div className="wb-stack">
            <Panel
              title="Enrichment"
              meta={<span className="wb-mono">EXERCISE CONTEXT</span>}
            >
              <dl className="wb-metadata two-col">
                {Object.entries(entity.attributes).map(([k, v]) => (
                  <div key={k}>
                    <dt>{human(k)}</dt>
                    <dd>
                      {k === "reputation" ? (
                        <Badge
                          value={String(v)}
                          tone={v === "malicious" ? "critical" : "medium"}
                        />
                      ) : (
                        String(v)
                      )}
                    </dd>
                  </div>
                ))}
                <div>
                  <dt>First observed</dt>
                  <dd>{time(entity.first_seen)}</dd>
                </div>
                <div>
                  <dt>Last observed</dt>
                  <dd>{time(entity.last_seen)}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{entity.source}</dd>
                </div>
                <div>
                  <dt>Confidence annotation</dt>
                  <dd>{entity.confidence.toFixed(2)} / 1.00</dd>
                </div>
              </dl>
            </Panel>
            {entity.kind === "ip" && tor.length > 0 && (
              <Panel
                title="TOR infrastructure"
                meta={<span className="wb-mono">CONTEXT, NOT A VERDICT</span>}
              >
                {tor.map((e) => (
                  <TorContext key={e.id} record={e.dataset_record} />
                ))}
                <p className="wb-footnote">
                  Tor Project Onionoo snapshot, matched on the exact IP. A Tor
                  exit relay carries traffic for many users; judge the activity
                  by its observed behavior.
                </p>
              </Panel>
            )}
            {entity.dataset_record && (
              <Panel
                title="Evidence provenance"
                meta={<ProvenanceBadge value={entity.provenance} />}
              >
                <DatasetProvenance record={entity.dataset_record} />
              </Panel>
            )}
            <Panel
              title="Supporting observations"
              meta={
                <button
                  className="wb-text-button"
                  onClick={() => showTab("relationships")}
                >
                  Correlate in graph →
                </button>
              }
            >
              <EvidenceList evidence={data.evidence} onInspect={setInspect} />
            </Panel>
          </div>
          <aside className="wb-stack">
            <Panel title="Continue the investigation">
              <div className="wb-next-step">
                <p>
                  Inspect the supporting observations, then follow the
                  correlated entities into the related incident.
                </p>
                <button
                  className="wb-button full"
                  onClick={() => showTab("relationships")}
                >
                  Explore correlation graph →
                </button>
                <h4>Related incident</h4>
                {data.related_cases.map((c) => (
                  <Link
                    key={c.id}
                    className="wb-case-cta"
                    to={`/investigations/${c.id}`}
                  >
                    <small className="wb-mono">{c.id}</small>
                    <strong>{c.label}</strong>
                    <span>
                      Open investigation <ArrowUpRight size={14} />
                    </span>
                  </Link>
                ))}
                {!data.related_cases.length && (
                  <p className="wb-muted">
                    No related incident has been established.
                  </p>
                )}
                <p className="wb-footnote">
                  A campaign association does not prove this specific IOC was
                  observed on every affected asset.
                </p>
              </div>
            </Panel>
            <Panel
              title="Direct connections"
              meta={
                <button
                  className="wb-text-button"
                  onClick={() => showTab("relationships")}
                >
                  Explore graph →
                </button>
              }
            >
              <div className="wb-entity-list">
                {data.neighbors.map((e) => (
                  <EntityLink key={e.id} entity={e} />
                ))}
              </div>
            </Panel>
            <SourceObservations value={entity.label} />
          </aside>
        </div>
      )}
      {inspect && (
        <EvidenceDrawer id={inspect} onClose={() => setInspect(null)} />
      )}
    </>
  );
}

type EnrichmentResult = {
  kind: string | null;
  results: {
    adapter: string;
    state: string;
    error: string | null;
    count: number;
  }[];
  observations: {
    id: string;
    source: string;
    source_type: string;
    entity_kind: string;
    value: string;
    confidence: number;
    provenance: string;
    relationship: string;
    collection_status: string;
    summary: string;
  }[];
};

// Adapter enrichment for this indicator. Synthetic unless live collection is
// explicitly enabled server-side; each row states its collection status.
function SourceObservations({ value }: { value: string }) {
  const { data } = useResource<EnrichmentResult>(
    `/enrichment?value=${encodeURIComponent(value)}`,
  );
  if (!data || !data.results.length) return null;
  return (
    <Panel
      title="Source observations"
      meta={<span className="wb-mono">ADAPTER ENRICHMENT</span>}
    >
      <div className="wb-source-obs">
        {data.results.map((r) => (
          <div key={r.adapter} className="wb-spread">
            <span className="wb-mono">{r.adapter.toUpperCase()}</span>
            <Badge
              value={r.state}
              label={`Collection status: ${r.state}`}
              tone={r.state === "connected" ? "simulated" : "demo"}
            />
          </div>
        ))}
        {data.observations.map((o) => (
          <article key={o.id}>
            <small>
              {kindLabel(o.entity_kind)} · {o.relationship.replaceAll("_", " ")}
            </small>
            <strong className="wb-mono wb-break">
              {o.value.split("#")[0]}
            </strong>
            <p>{o.summary}</p>
            <small>
              Source: {o.source} · Confidence {o.confidence.toFixed(2)} ·{" "}
              {o.provenance}
            </small>
          </article>
        ))}
      </div>
    </Panel>
  );
}
