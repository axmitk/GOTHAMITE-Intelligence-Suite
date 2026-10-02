# GOTHAMITE investigation workbench

## Inspection and decisions (2026-09-28)

The active implementation is `gothamite/` in this release repository. The sibling
`../gothamite` is an older standalone checkout and is left untouched.

Existing: React 18 + TypeScript + Vite, React Router, D3 graph, FastAPI,
SQLAlchemy/SQLite, immutable hashed persona artifacts, deterministic cross-source
persona correlation, Streamlit workbench, six backend test suites. Existing React
routes are overview, graph, dossier and timeline. No working LLM service,
authentication, incident model, IOC catalog or response lifecycle was found.
The previous root README overstated several capabilities.

## Implementation sequence

1. Add normalized intelligence entities, evidence, relationships and case state.
2. Seed coherent synthetic scenarios with documentation IPs and `.example` domains.
3. Implement bounded search/graph APIs, transparent risk, evidence analysis,
   NIST mapping, analyst review, persistent notes and reports.
4. Extend React with a command center, global search and connected case workspace.
5. Verify backend invariants, regression tests, build and browser demo flow.
6. Document runnable commands, limitations and the handoff.

## Architecture

```text
React analyst workbench (existing Vite project)
  -> /api/v1/workbench (FastAPI; local demo session)
    -> intelligence / risk / evidence analysis / response / report services
      -> SQLAlchemy entities + directed, evidence-backed relationships
        -> existing SQLite engine (new wb_* tables, additive schema)

Existing /api/v1 persona APIs and legacy React/Streamlit views remain available.
```

SQLite keeps the prototype installable without database services. Relationships
are first-class rows; graph traversal is bounded. An additive schema avoids
rewriting the tested persona subsystem. Case changes and audit entries commit in
one transaction. Synthetic data is idempotently seeded and never replaces notes
or analyst decisions on restart.

The default analysis provider is a deterministic evidence-rule engine, explicitly
labelled as such. It is not an LLM. Findings reference evidence IDs, distinguish
observation from interpretation and expose uncertainty. A provider interface
keeps future model integration separate from attribution and response approval.
No API credentials, external feed calls or real containment operations are used.

## Collection model

Implemented prototype versus deployment architecture:

| Stage | Implemented prototype | Deployment architecture |
| --- | --- | --- |
| Source adapters | Companion `darkweb-sandbox`: scraper agent fetches mock hidden-service pages over a simulated multi-hop relay network (no real Tor, no real services) | One adapter per authorised source type |
| Ingestion | Sandbox posts artifacts to `/api/v1/ingest`; the 8042 workbench loads equivalent synthetic fixtures from an idempotent seed | Scheduled or continuous collection workers |
| Raw observations | Immutable artifacts with SHA-256 content hashes | Same, plus collection time and source health |
| Normalization / extraction | Deterministic extraction of handles, PGP fingerprints and wallet identifiers | Same rules, versioned |
| Correlation | Documented evidence weights (PGP +0.70, wallet +0.25, succession +0.15, handle +0.05, overlap −0.30, lexical similarity +0.25), capped at 0.95; hand-set priors, see [scoring_rationale](scoring_rationale.md) | Same, with evaluation against labelled cases |
| Analyst review | Confirm / reject candidate linkages; approve and simulate responses | Same, with authenticated identities and roles |

### Offline dataset pipeline (`gothamite/backend/data_sources/`)

```text
Public dataset (local file) ─▶ scripts/prepare_datasets.py ─▶ transform.py
  (normalize · safety filter · defensive entity extraction) ─▶ bundled snapshot + manifest.json
  ─▶ importer.py at startup (idempotent, offline) ─▶ wb_entities / wb_evidence /
  wb_relationships + wb_dataset_records ─▶ graph · case · NIST · report
```

Dataset records are first-class rows in the existing model, not a second model.
Provenance classes: `synthetic`, `dataset_derived`, `reference_derived`.
Entity ids derive from normalized values (cross-source correlation key). Edges
are created only from a supporting record (`OBSERVED_IN`, `MENTIONS`,
`INVESTIGATES`). The Command Center's exercise timeline stays synthetic-only;
its metrics show synthetic and dataset-derived counts separately. See
DATA_SOURCES.md.

### TOR exit-node intelligence (`data_sources/tor/`, `importer.import_tor`)

```text
Prototype:  bundled Onionoo snapshot ─▶ normalize_onionoo_relay ─▶ tor_relay + ip entities,
            tor_context / tor_relay observations (dataset_derived, CC0)
            ─▶ tor-exact-ip-v1 correlation ─▶ IOC profile · evidence drawer · graph · case · NIST · report
Deployment: scheduled Onionoo details fetch (outbound HTTPS to the Tor Project only)
            ─▶ the same normalizer and importer, versioned snapshots, expiry of stale relays
```

The prototype runs only the first line: no network, no Tor process. Order at
startup: exercise seed → case library → dataset import, so the exact-IP rule sees
every IP already known. Tor context is its own risk dimension (+5), separate from
reputation, observed behavior and source corroboration.

### Synthetic case library (`services/workbench_library.py`)

INC-1047 to INC-1052 reuse the exercise model, rules and workflow (no separate
case renderer). `CASE_STATES` presets each case's workflow position by replaying
the audit events the live workflow would record. INC-1049/INC-1050 are created by
the importer from dataset records. INC-1042 to INC-1045 are untouched.

### Source adapter layer (`gothamite/backend/collection/`)

```text
Source adapter ─▶ Scheduler* ─▶ Collection worker* ─▶ Raw observation ─▶ Normalization
  ─▶ Deduplication ─▶ Entity resolution ─▶ Correlation ─▶ Evidence store ─▶ Investigation
(* architecture only: no scheduler or worker runs in this build)
```

- `base.py`: `CollectionAdapter`, `EnrichmentAdapter`, `SourceRegistryAdapter`;
  the normalized `Observation` (source, source type, observed_at, collection
  status, provenance, confidence, entity type/value, relationship type,
  synthetic flag, stable content id); `SourceState` = synthetic / connected /
  available / unavailable / error; `dedupe()`.
- `adapters/synthetic.py`: deterministic MailAccess-, TorBot- and horus-shaped
  adapters used by the demo.
- `adapters/isolated.py`: process-isolated adapters for the real tools. Off
  unless `GOTHAMITE_LIVE_COLLECTION=1` **and** `GOTHAMITE_ADAPTER_<NAME>=1`.
  TorBot also needs an approved target. horus and MailAccess live calls are
  deliberately not wired (see THIRD_PARTY_NOTICES.md).
- `sources.py`: deepdarkCTI catalogue parser → `Source` records (registry
  metadata, not intelligence) plus a small synthetic registry.
- `registry.py`: picks the live adapter only when available, otherwise the
  synthetic one; captures adapter exceptions as `error` results.
- API (session-protected): `GET /workbench/sources/adapters`,
  `GET /workbench/sources/registry`, `GET /workbench/enrichment?value=`,
  `POST /workbench/collection` (one target, `approved` required).
- UI: a "Source observations" panel on the existing IOC profile shows each
  adapter's collection status and its normalized observations.

Adapter observations are returned to the analyst; they are **not yet persisted
into the evidence store or graph**. That step (plus scheduling) is the next
increment.

Nothing in either repository connects to the live dark web. "Lexical similarity" is
a bag-of-words term-frequency cosine; it is not a trained or language model. It compares
the raw HTML of each persona's first artifact, fires on no pair in the scenario set and has
no test of its own.

NIST mapping uses CSF 2.0 categories, checked against the official Core:
https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf
This is a workflow mapping, not a compliance certification.

## Implemented boundaries

The production frontend and API share one loopback origin at port 8042. Vite
bundles use `/static` so the `/assets` inventory route remains refreshable. Dev
Vite on 5173 proxies to the same backend. Lazy route chunks keep the initial
JavaScript bundle about 218 KB (71 KB gzip).

Demo sessions are signed, expire after 12 hours, and use HttpOnly/SameSite cookies.
Writes require an origin check and a CSRF token. Valid sessions are reused across
tabs so opening another tab does not invalidate an in-progress notebook save.
Request limits and signing keys are in memory; restarting renews the demo seat.
This provides local browser protections, not identity verification or enterprise
authorization. The demo entrypoint also guards legacy API routes. The separate
original development entrypoint does not apply that legacy-route guard.

Case versions implement optimistic concurrency: stale mutations return conflicts.
Response approval and simulation are distinct, audited decisions. Containment
requires a recorded relevant simulation; closure requires recovery and lessons
entries plus recovery simulation. Simulations never claim to reduce the observed
baseline risk. Graphs are bounded by depth and node limits, and incident graphs
stay within the evidence scope. Graph edges reference their source evidence.

Evidence hashes detect content differences; they are not signatures or an
external chain-of-custody guarantee. Synthetic records use reserved IP ranges,
`.example` names and explicitly fictional vulnerability identifiers; the one
exception is INC-1047's source IP, a real Tor exit address from the bundled
Onionoo snapshot, named by a synthetic log. No live
external enrichment is performed. Existing data is preserved by sentinel-based
idempotent seed logic; future seed/schema revisions will need explicit migrations.

## Validation and deployment assumptions

Verified on Windows x64, Python 3.12.7 and project-local Node 22.22. Production
build passes, 98 backend tests pass, and 12 isolated Edge browser checks pass with
zero console/page errors (2026-09-29). Re-verified 2026-10-03 after the wallet-weight change
(0.45 to 0.25): 100 backend tests pass plus 2 strict expected failures, 12/12 browser checks,
164 sandbox tests. Six pre-existing lint warnings remain in legacy React
views; new workbench code has no lint warnings. Verification screenshots and an
example exported report are in `gothamite/verification/`.

SQLite, single-worker sessions and explicitly installed Windows native bindings
are intentional local-demo choices. Deployment, multi-user RBAC, shared durable
sessions/rate limits, schema migrations, scheduled ingestion (including Onionoo refresh) and a model-backed
analysis provider are separate future work. No production deployment was made.
