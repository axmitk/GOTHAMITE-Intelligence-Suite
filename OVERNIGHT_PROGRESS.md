# GOTHAMITE progress — 2026-09-28

## TOR exit-node intelligence and case library (2026-09-29)

TOR snapshot → TOR adapter → normalized observation → IOC enrichment → evidence →
correlation → graph → case → NIST → response → report, fully offline.

- **Snapshot:** Tor Project Onionoo `details`, relays published 2026-09-28
  17:00:00 UTC, retrieved 2026-09-28, 18 relays (16 exit, 12 running, 11 AS names).
  CC0. Fetched once during development; runtime never contacts Onionoo or starts Tor.
- **Imported:** 18 relay entities, 15 new IP entities (one address matched the
  existing INC-1047 IP), 18 observations (16 `tor_context` exit, 2 `tor_relay`),
  18 `ASSOCIATED_WITH` edges, each with a dataset record (rule, snapshot, relay fields).
- **Correlation:** `tor-exact-ip-v1`, exact normalized IPv4 only. No ASN/range match.
- **Risk:** new "TOR exit-node context" factor, +5, dimension "TOR context"; every
  factor now names its dimension (reputation, observed behavior, TOR context, source
  corroboration, asset impact, exposure). Method label is now `risk-v1.1`. INC-1042
  still scores 100.
- **UI:** "TOR exit node" text badge (IOC heading, evidence rows), TOR infrastructure
  section in the IOC profile and evidence drawer, `tor_relay` graph nodes in the
  Domain / IP lane, case headers show every provenance class present. Graphs for
  cases outside the actor chain no longer start with empty rows.
- **Case library:** INC-1047 to INC-1052 (see DATA_SOURCES.md). The queue has 11
  cases. The campaign-context finding now appears only when a campaign is in scope,
  so inventory-only cases do not claim a campaign link.
- **Tests:** backend **98 passed** (82 + 16 in `tests/test_tor_library.py`, run with
  non-loopback sockets and subprocesses forbidden). Browser **12/12**, 0 console
  errors, three consecutive runs. New check: TOR IOC → enrichment → evidence →
  risk → graph → report → library case states. Updated expectations, no assertion
  removed: queue 5 → 11 rows, exposure mentions 4 → 5 (INC-1051 bulletin), the
  dataset-edge test accepts `ASSOCIATED_WITH` and any case's `INVESTIGATES` scope,
  and the `imported` fixture seeds the library as the app does. Two checks gained
  explicit waits for their panel (they counted elements before render).
- **Offline:** cold start on an empty database with outbound sockets blocked: 0
  connection attempts, 11 cases, 18 relays.
- **Unresolved:** none for Tor (CC0). DWData and MailAccess licensing unchanged.

## Public CTI dataset integration

Real public data now flows through the existing model:
PUBLIC DATASET → dataset adapter → normalized observation → evidence →
correlation → graph → case → NIST → report. Full detail: DATA_SOURCES.md.

- **Datasets added:** DarkForums Safe Corpus (Zenodo 10.5281/zenodo.21991378,
  CC BY 4.0) and Infoblox Threat Intelligence (@5b5a12d, CC BY 4.0), as filtered
  offline snapshots. DWData: **not added** (no licence); schema projection plus six
  labelled reference reconstructions only.
- **Imported:** 462 entities, 498 evidence rows, 312 relationships. Forum: 200
  threads and 153 posts (1 thread dropped). Infoblox: 140 listings of 121
  indicators across 7 reports. Import takes about 1.2 s on first start and is
  skipped afterwards.
- **Filtered:** 110 of 153 posts had their text withheld (redacted personal
  data, credential references, phone-like numbers, encoded blobs, financial
  data); 1 thread dropped; 1 Infoblox row rejected. No raw post text is bundled.
- **Findings that limit the demonstration (stated, not hidden):** the corpus is a
  single "Leaks" sub-forum with no CVE/ATT&CK content, and the two datasets share
  **no** entity. Multi-observation support is real within Infoblox (14 domains
  in more than one report) and within the forum; cross-dataset corroboration is
  implemented and proven with a test fixture only.
- **Case:** INC-1046 "Decoy Dog DNS infrastructure review" (50 dataset-derived
  observations). Existing risk/NIST rules only; report has an "Evidence sources"
  block and per-observation provenance. INC-1042 is untouched and synthetic.
- **UI:** one provenance badge (Synthetic / Dataset-derived / Reference
  reconstruction) in search, catalogs, evidence rows, the drawer, case headers and
  reports; dataset-record details (dataset, record id, version, licence/DOI,
  transformation, import time); dark-web view tabs for exposure mentions, forum
  threads and marketplace listings; the graph shows direct relationships for
  entities outside the exercise chain; dates show the year outside 2026.
- **Tests:** backend **82 passed** (56 + 26 in `tests/test_datasets.py`), also
  run with external network blocked (0 connection attempts). Browser **11/11**
  (new check: dataset search → provenance → evidence drawer → graph → forum and
  marketplace tabs → INC-1046 report → canonical IOC still synthetic), 0 console
  errors. Two existing expectations were updated because INC-1046 exists: the
  queue now has 5 rows (all five ids asserted), and catalog pagination asserts
  "Page 2 of N" instead of a fixed total. No test was removed.
- **Unresolved licensing:** DWData redistribution; MailAccess has no LICENSE file.

## Source adapter pass (defensive CTI integration)

Audited four repositories and added a common observation model. No module
was replaced and the synthetic demo is unchanged and works offline.

Audit result (full table in THIRD_PARTY_NOTICES.md):

- **deepdarkCTI** (GPL-3.0): source catalogue. **Integrated** as a source
  registry parser that reads a local clone; never fetched, never vendored.
- **TorBot** (GPL-3.0): onion collection adapter over a process boundary,
  **disabled by default**, one approved target per call. Not run live here.
- **horus** (GPL-3.0): mixes passive lookups with active scanning. Live call
  **not wired**; synthetic passive-metadata adapter only.
- **MailAccess** (MIT declared, no LICENSE file): findings shape used. Its active
  account probing, mailbox verification and proxy egress are **out of scope and
  not invoked**; live call not wired.

What was built (`gothamite/backend/collection/`): adapter interfaces;
`Observation` with source, source type, observed_at, collection status,
provenance, confidence, entity type/value, relationship type and synthetic flag;
`SourceState` (synthetic / connected / available / unavailable / error);
content-id deduplication; synthetic fallback; per-adapter error capture; four
session-protected endpoints; and a "Source observations" panel on the existing
IOC profile.

Integrated versus architectural:

| Capability | State |
| --- | --- |
| Observation model, dedup, state model, registry parser | Implemented and tested |
| Synthetic MailAccess / horus / TorBot adapters | Implemented; used by the demo |
| Live TorBot adapter | Wired, off by default, not exercised live |
| Live horus / MailAccess adapters | Not wired (safety guard) |
| Scheduler, collection worker, persisting observations into evidence/graph | Architecture only |

Verification after the final change: `pytest tests -q` **56 passed** (44
existing + 12 new, run with `subprocess.run` forbidden to prove no adapter
launches a tool by default); build passed; lint exit 0 (six pre-existing
warnings); `npm run test:e2e` **10/10, 0 browser errors**, now also asserting the
IOC profile shows adapter observations with "collection status: synthetic";
canonical 203.0.113.42 → INC-1042 path unchanged. Demo server restarted.

## Content and realism pass

A copy and claims audit across the React workbench, the persona toolkit, the
legacy Streamlit views, backend labels, reports and documentation. No modules,
routes or architecture changed. The aim was that every claim matches what the
code does.

Fabricated or overstated content removed (the most important fixes):

- **Legacy Streamlit views invented output.** There is no Ollama/LLM integration
  anywhere in the repository, yet the views displayed "Powered by Ollama",
  "OLLAMA THREAT INFERENCE: Stylometric analysis confirms a 94% linguistic
  match", "LLM Engine (Ollama): ONLINE", "Dark Web Scrapers: ONLINE", hardcoded
  counts ("12 investigations", "45 Ollama inferences"), invented pipeline events,
  per-handle hardcoded aliases, an email address and risk scores (92/75/45),
  synthetic risk rows (`95 - i*12`), a timeline with invented events (including a
  real Bitcoin address), and a dead "Export (PDF)" button. `overview.py`,
  `investigation_view.py`, `timeline_view.py` and `dossier_view.py` now compute
  everything from the loaded dataset: personas, artifacts, candidate linkages,
  review status, the real identifier timeline and dossier links. The "risk" page
  is now **linkage priority** (strongest evidence-weight score, explicitly not a
  probability or incident risk). Wrong NIST names ("Analyze", "Report") were
  replaced with real CSF categories (DE.AE, ID.AM, RS.AN).
- **"AI Stylometric Behavioral Match"** in the correlation service is a
  bag-of-words term-frequency cosine, not TF-IDF and not a trained model. It is
  now `lexical_similarity` ("corroborating only"). Its weight (+0.25) and
  behaviour are unchanged.
- **Workbench AI wording.** "AI analysis" → "Evidence analysis · offline rules".
  The report index states "no language model is involved".
- **Implied live collection.** Persona source cards showed status "up" with a
  green dot; they now read "Simulated collection". The dark-web catalog and
  ARCHITECTURE.md separate the **implemented prototype** (synthetic seed; the
  companion darkweb-sandbox scraper collects mock hidden-service pages over a
  simulated relay) from the **deployment architecture** (source adapters →
  scheduled ingestion → raw observations → normalization → entity extraction →
  correlation → analyst review).

Technical specificity added:

- Every Command Center number now states what it counts: open investigations
  (not closed), open critical cases, indicators (IOCs) by type, and
  evidence-backed relationships (each cites a recorded observation).
  "Observations by source" says it counts recorded observations per synthetic
  source.
- The persona toolkit shows its pipeline: Source → Artifact extraction →
  Normalization → Entity resolution → Cross-source correlation → Confidence →
  Analyst review. Metric labels say what is counted. Identity-overstating labels
  were corrected ("Same Actor" → "Candidate same actor", "Select Actor" →
  "Persona"). The succession callout now gives the actual score composition
  (wallet +0.45, succession +0.15) instead of crediting succession alone.
- The catalog adds a **Last observed** column, so each record shows source,
  observation date, confidence and provenance/corroboration.
- The report now has the nine requested sections: Executive summary (generated
  from case data), Observed evidence, Correlated context, Automated
  interpretation, Risk assessment, NIST alignment, Response recommendations,
  Analyst decisions, Audit trail.

Kept deliberately: `signal_type` and "signal" in the persona correlation model
(it is the data model's term for a weighted evidence row); "engine" where it
means the SQLAlchemy engine; honest "not an LLM" disclaimers; and in-fiction
taglines on darkweb-sandbox mock marketplace pages (they are the scraped content
itself, not product copy).

Verification after the final change:

- `pytest tests -q`: **44 passed**. The report test now asserts nine ordered
  sections and the analyst-decision line.
- `npm run build` passed. `npm run lint`: exit 0 (six pre-existing legacy warnings).
- `npm run test:e2e`: **10/10 passed, 0 browser errors**. Report-section
  assertions were updated to the nine sections.
- All seven Streamlit pages were rendered headlessly with `streamlit.testing`
  AppTest against a freshly seeded temporary database: no exceptions, and none
  of the removed wording (Ollama/LLM/94%/ONLINE/genesis address).
- Visual check on http://127.0.0.1:8042: Command Center, dark-web catalog,
  persona toolkit. The demo server was restarted for the backend label and
  report changes. The persistent demo case was not modified.

Known limitation: Docs/ contains older design documents with historical
planning language. Their claims are about intent and are marked as such in
gothamite/README.md. They were not rewritten.


## Second polish pass (Claude Opus 5.5 handoff)

Continuation of the existing product. No modules were added; the canonical
203.0.113.42 → INC-1042 path was audited end to end, then deepened where the
workflow was thin. The Command Center was left unchanged.

What changed:

- **NIST alignment is traceable, not decorative.** Each CSF 2.0 function now shows
  its basis, the observations that support it, and the linked response
  recommendations with live status (pending / approved / simulated). Action links
  open Response. The exported report carries the same basis, evidence and actions.
- **Stage gating explains itself.** "Advance to containment" no longer returns a
  409 when clicked too early. It stays disabled, and a bar under the stage strip
  states the prerequisite and links to Response. Backend gating logic was
  consolidated into one `advance_requirement()` used by both the UI payload and
  the PATCH endpoint.
- **Response review shows the decision record.** There is a pending / approved /
  simulated / rejected summary and a decision audit trail: analyst approval,
  simulated action recorded, and case updates with actor and UTC time.
- **Analysis findings use a fixed anatomy:** finding → confidence → reasoning
  factors → supporting evidence → recommended next step. When no rule fires, the
  panel states "Insufficient evidence".
- **Graph readability.** Edges are routed orthogonally through lane gutters and
  row gaps, so no relationship line passes behind an unrelated entity (the old
  full graph drew lines through the vulnerability, email and URL cards). Ports
  are spread per node side. In Full graph, selecting an entity recedes unrelated
  relationships; nothing is hidden. The browser test asserts zero crossings.
- **Consistency.** Entity types use analyst labels (IP address, File hash,
  Threat actor, Dark-web mention) instead of "ip"/"Ip". Badges are sentence
  case. Counts are pluralized correctly ("1 result", "1 relationship"). Dates
  use one UTC format ("28 Sep, 08:35 UTC", previously "Sept"). IOC reputation
  renders as a severity badge. The heavy green "next step" boxes are quieter.
- **Report.** Section 03 is now "Automated interpretation (offline evidence
  rules)", matching the brief's Observed → Context → Interpretation → Risk →
  NIST → Response → Approval order. The preview shows analyst text without
  Markdown escape characters; the export stays escaped.
- **Persona toolkit.** Aligned to the page gutter. Sentence-case section heads,
  no doubled rule under the tabs, and a smaller inner title ("Correlation
  overview"). Source colors moved from saturated blue/orange/green to the
  restrained palette (still distinguishable). Microcopy: "Run correlation pass",
  "Synthetic source fixtures".

Verification (all run after the final change):

- `pytest tests -q`: **44 passed** (43 original + 1 new NIST traceability and
  stage-gate test).
- `npm run build`: passed. `npm run lint`: exit 0, with only the six
  pre-existing legacy warnings.
- `npm run test:e2e`: **10/10 checks passed, 0 browser errors**. New assertions
  cover no graph edge crossings, NIST basis/evidence/actions, the disabled Advance
  button and stage-gate text, and audit-trail entries. Screenshots regenerated in
  `gothamite/verification/`.
- Manual walk-through on http://127.0.0.1:8042 of Command Center → Reference IOC →
  IOC profile → graph (path and full) → INC-1042 → Evidence → Analysis → NIST →
  Response → Report, plus the persona toolkit. Approval and simulation were
  exercised only in the isolated test database. The persistent demo case was
  left untouched.
- The demo server on 8042 was restarted to load the backend changes (PID in
  `gothamite/.local/server.pid`).

Known limitations are unchanged (see below). New ones:

- The "affected in" label on the collapsed path sits above the incident row
  rather than on the arrow.
- Other persona sub-pages (graph, dossiers, timeline) only get the shared token,
  palette and heading overrides. They were not individually redesigned.

Canonical demo path (unchanged): **Command Center → Reference IOC 203.0.113.42 →
IOC profile → supporting observations → Relationship graph → Finance gateway
beaconing → Open investigation (INC-1042) → Analysis → Risk factors → NIST
alignment → Response: approve + simulate "Isolate affected endpoint" → Advance to
containment → Report → Export.**

## Product polish pass

The existing product was refined without adding major modules or expanding the
feature surface. The Command Center layout and its eight-stage process remain:
COLLECT → ENRICH → CORRELATE → ANALYZE → PRIORITIZE → INVESTIGATE → RESPOND → LEARN.

- Shared surface, border, typography, control, badge and navigation tokens now
  carry through the first-party screens and the retained persona capability.
  Persona correlation is explicitly framed as **Existing toolkit / integrated
  capability**, with its own restrained subnavigation and return to investigations.
- The Command Center has a subtle **Reference IOC · 203.0.113.42** link. Search,
  profile evidence, correlation graph, incident, analysis, NIST, response review
  and report now have contextual continuation links. Transitions return to the
  top of the target view; relationship groups bring their inspector into view.
- The graph defaults to the strongest continuous investigation path: actor →
  campaign → malware/hash → domain/IP → asset → incident. For INC-1042 this shows
  **8 entities and 8 relationships**, instead of all 14 entities / 16 relationships.
  High-confidence observations have a subtle blue emphasis. Secondary context,
  infrastructure and source claims are expandable; **Full graph** preserves every
  relationship in the bounded scope. No underlying relationships were removed.
  The final incident step displays the inverse AFFECTS relation as “affected in”;
  the inspector and full graph retain the stored direction.
- Dark-web intelligence remains a restrained table with synthetic source labels,
  confidence annotations, unverified-claim status and explicit corroboration copy.
- The report preview is a readable investigation record with a section index,
  using the same report endpoint as the export. Its order is **Observed evidence →
  Correlated context → Automated interpretation → Risk assessment → NIST mapping →
  Response decision → Analyst / approval record**. Interpretation is explicitly
  offline evidence rules, not LLM inference. Context includes evidence-linked
  relationships, and the final record includes approval events and analyst notes.
- New microcopy uses concrete analyst language. No dashboard widgets, live feeds,
  model integrations or response capabilities were added.

Verification retains all **43 backend tests** and the **10 browser check groups**.
Assertions now also cover collapsed/full graph access, expandable evidence,
continuation links, the preserved eight-stage process, toolkit framing and report
section order. Screenshots include investigation-path.png, ioc-profile.png,
persona-toolkit.png, dark-web-intelligence.png and investigation-report.png.

## What was already present

React/TypeScript/Vite frontend, FastAPI/SQLAlchemy backend, SQLite persona and
artifact models, deterministic cross-source persona correlation, legacy D3 graph,
dossier/timeline pages, Streamlit interface and 37 backend tests. The original
README described several capabilities that were not actually implemented.

## What you implemented

- Connected command center, global search, IOC profiles, intelligence catalogs,
  asset inventory, actor and synthetic dark-web views.
- Four coherent synthetic cases with 252 indicators, 291 evidence-backed
  relationships, 134 evidence records and 8 assets; restart-safe seeding.
- Bounded interactive relationship graph, node/edge inspectors and raw evidence
  drawer with SHA-256 integrity hashes.
- Persistent investigation notebook, ownership/severity editing, case stages,
  optimistic concurrency and transactional audit events.
- Offline evidence analysis with citations, uncertainty and recommended next
  steps; transparent baseline risk and six NIST CSF 2.0 workflow mappings.
- Separate approval and response simulation; closure requires recovery and
  lessons documentation. Markdown report preview/export includes analyst decisions.
- Local demo session, CSRF/origin checks, request limits, security headers and
  HTML escaping. Migrated 107 legacy Streamlit HTML calls to sanitized rendering.
- Same-origin launcher, setup/start scripts, updated READMEs, architecture notes,
  Claude context export and isolated browser verification with screenshots.
- Retained persona routes. Formatted new React/CSS code, fixed asset inventory
  refresh routing and preserved CSRF tokens when opening additional tabs.

## What is functional

Search → IOC profile → evidence graph → case → cited rule analysis → NIST →
approved simulation → report works end to end. Notes persist across reloads.
Case progression and closure enforce their prerequisites. All response operations
are local simulation records. Source labels and uncertainty stay visible.

Final verification:

- Production TypeScript/Vite build passed.
- **43 backend tests passed**, including six new integration tests.
- **10 Edge browser checks passed**, with zero console or page errors. Checks
  include notebook HTML inertness, report download, direct-route refresh,
  pagination, empty results, legacy graph and 1024-pixel tablet layout.
- Lint exited successfully with six pre-existing warnings in legacy persona
  components; no new-workbench warnings.
- Screenshots and an example report: `gothamite/verification/`.

## How to run it

```powershell
cd 'C:\Users\aadik\sih 2026\Gothamite-Release'
.\START_GOTHAMITE.ps1
```

Open **http://127.0.0.1:8042**. If already running, open it directly. Ctrl+C stops
a foreground launch. Existing dependencies and the production build are ready.
For a fresh Windows x64 setup, install Python 3.12+ and Node 22.22+, then run
`SETUP_GOTHAMITE.ps1` before the start script. See README for verification commands.

Analyst state lives in `gothamite/workbench-demo.db`, ignored by Git. Seeding does
not reset cases or notes. Use a separate `GOTHAMITE_DB_PATH` for a new exercise.
The browser test always creates and removes its own temporary database.

## Demo path

**COMMAND CENTER → search `203.0.113.42` → IOC PROFILE → supporting Evidence →
Correlation Graph → Related Incident (Finance gateway beaconing / INC-1042) →
Investigation → AI Analysis (offline evidence rules) → Risk Factors →
NIST Alignment → Response Recommendation → Analyst Approval → Report Export.**

The Reference IOC link beside the Command Center header starts the same search.
Open a supporting observation on the IOC profile before following its correlation
graph. Select the incident node and Open investigation. Use the continuation links
to move through analysis, NIST and response; inspect the cited Risk factors beside
the analysis. Review the final report sections before exporting.

In Graph, select Grey Moth and open evidence on a connection. In the notebook,
save a hypothesis. In Response, approve Isolate affected endpoint, then run its
simulation and advance to containment. Export the Markdown report. On subsequent
visits, the case retains those actions; already completed steps cannot repeat.

## Known limitations

- Analysis is a deterministic evidence-rule provider, **not LLM inference**.
  No model credential, model request or live enrichment is involved.
- All threat data, assets and dark-web excerpts are synthetic. Attribution and
  baseline risk are exercise interpretations, not real-world conclusions.
- No endpoint/network control is executed. Approval means demo analyst review;
  the session does not authenticate a real person.
- Single-process SQLite and in-memory security state are not production multi-user
  infrastructure. No SSO/RBAC, live feeds, uploads or arbitrary case creation.
- NIST alignment is a workflow aid, not a compliance assessment.
- Setup targets Windows x64. Python dependency ranges are not a fully locked
  reproducible environment; fresh-machine setup has not been independently tested.
- Original Streamlit can be run separately but the full new workflow is React;
  this session's end-to-end verification covered React, not every Streamlit view.
- The working changes are local and uncommitted. Nothing was pushed or deployed.

## Next recommended development steps

These are deferred backlog items. The current instruction is product polish only;
do not implement major new modules without a new scope request.

1. Add user-created cases and validated evidence ingestion with explicit provenance,
   schema migrations and duplicate handling.
2. If model-backed analysis is wanted, add a provider behind the existing interface,
   validate evidence references and measure output quality against the seeded cases.
3. Add production identity/roles, shared sessions and PostgreSQL before multi-user use.
4. Lock Python dependencies, exercise clean-machine setup and add CI checks.
5. Review the six legacy React effect warnings and add broader keyboard/mobile
   accessibility coverage without rewriting the working persona subsystem.

For another agent, begin with [CLAUDE_CONTEXT.md](CLAUDE_CONTEXT.md).
