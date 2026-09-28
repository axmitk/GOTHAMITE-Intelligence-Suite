# GOTHAMITE continuation context

This file exports the current engineering context for Claude. Work is committed
and pushed on branch `gothamite-investigation-workbench` (origin:
axmitk/GOTHAMITE-Intelligence-Suite); read "Latest verified state" first. The original task is an autonomous, demonstrable GOTHAMITE prototype,
not a plan or visual mockup. The connected local demo and final verification are
complete. Preserve working code and analyst data when extending it.

## User brief

Latest scope correction: the primary demo is complete enough. The user requested
product polish only, explicitly prohibiting major modules or feature expansion.
That pass is implemented: shared styling, integrated-toolkit framing, a collapsed
primary graph with expandable secondary relationships/full view, discoverable IOC,
contextual continuation links, restrained source-claim tables and a seven-section
report. See the Product polish pass and canonical Demo path in OVERNIGHT_PROGRESS.md.
Do not interpret the future-work list below as authorization to expand scope.

Read `C:\Users\aadik\Downloads\GOTHAMITE_Master_Build_Prompt_GPT-6_Astra_AUTONOMOUS.md`.
It supersedes the non-autonomous version in the same folder. The user authorizes
reasonable implementation choices without repeated confirmation. The core path:
Dashboard → Search → IOC → Enrichment → Graph → Incident → Evidence analysis →
NIST → Reviewed simulated response → Report. Every record must be honestly
labelled with its provenance (synthetic, dataset-derived, reference-derived). No real destructive cyber actions or fake live integrations.
Use restrained dark, information-dense analyst UI. The user also requested this
Claude context export and then asked to continue the build.

## Workspace

- Release repo: `C:\Users\aadik\sih 2026\Gothamite-Release`
- Application: `<repo>\gothamite`
- React/Vite frontend: `<app>\frontend-react`
- Older sibling checkout `C:\Users\aadik\sih 2026\gothamite` is untouched.
- OS: Windows; PowerShell. Python 3.12.7; system Node 22.11.0.
- No applicable AGENTS.md was found in the inspected project hierarchy.
- Commits 145d110 and 147a75c are pushed; no merge to the default branch and no
  deployment.

## Existing architecture and preserved work

React 18 + TypeScript + Vite, React Router, D3; FastAPI, SQLAlchemy/SQLite;
persona/artifact models, deterministic persona correlation, legacy Streamlit UI,
and six backend test suites. Existing routes `/overview`, `/graph`, `/dossier`,
`/dossier/:id`, `/timeline` remain available through the new app shell.
Original README claims about Ollama/Neo4j/production readiness were overstated.

## Added implementation

- `backend/models/workbench.py`: additive `wb_*` entity, evidence, relation, case,
  note, action and audit tables using the existing database engine.
- `backend/services/workbench_seed.py`: idempotent fictional scenarios; 120 IPs,
  120 domains, four hashes, four URLs, four emails, four cases, four fictional
  actors/campaigns/malware families, eight assets, synthetic exposure/vulnerability
  records. `workbench_library.py` adds INC-1047 to INC-1052; the dataset importer
  adds INC-1046 and public snapshot records (see Latest verified state). Evidence has SHA-256 content integrity and explicit entity links.
- `workbench_intelligence.py`: bounded search/pagination, profiles, graph queries.
- `workbench_analysis.py`: transparent risk factors, an offline rule-based analysis
  provider (explicitly NOT an LLM), evidence references, recommendations, CSF 2.0.
- `workbench_cases.py`: optimistic version checks, persistent notes, sequential
  case stages, approve-before-simulate response, audit events and Markdown reports.
- `workbench_security.py`: expiring signed local demo session, CSRF checks,
  origin checks and per-process rate limiting. This is not production SSO/RBAC.
- `backend/api/workbench.py`: new `/api/v1/workbench/*` API.
- `backend/demo.py`: seeds demo data, serves built React app, security headers,
  local session enforcement for legacy APIs. Seeds legacy personas on empty DB.
- `scripts/run_workbench.py`: loopback server at `http://127.0.0.1:8042`, stable
  `workbench-demo.db` location; configurable `GOTHAMITE_PORT`/`GOTHAMITE_DB_PATH`.
- `frontend-react/src/workbench/`: new shell, dashboard, search/catalog, entity
  profile, graph with evidence inspector, case tabs, notebook, reports and NIST.
- `src/main.tsx` now loads WorkbenchApp. Original App.tsx remains in place.
- `tests/test_workbench.py`: six isolated integration tests.
- `frontend-react/scripts/verify_workbench.mjs`: headless Edge browser flow using
  a temporary SQLite DB and a temporary server on port 8043.
- `scripts/harden_legacy_html.py`: executed once to migrate 107 unsafe Streamlit
  Markdown HTML calls to `st.html` and HTML-escape dynamic interpolations.
  Requires Streamlit >=1.33; current environment has 1.55. Python 3.12+ is the
  documented minimum because the escaped formatting uses nested f-string syntax.

## Hero exercise

Search `203.0.113.42` → `IP-001` → `glass-harbor-sync.example` → Glass Harbor /
Grey Moth / SableLoader → `FIN-GW-01` → `INC-1042` Finance gateway beaconing.
Other cases: INC-1043 (exposed service identity), INC-1044 (staging), INC-1045
(unverified scanning). Reserved documentation IPs and `.example` domains only.
Hero baseline risk = 100 from 20 reputation + 25 internal sample + 15 network +
20 critical asset + 10 exposure claim + 10 multiple observation types. This is
priority, not a probability. Simulated actions do not reduce baseline risk.

## Commands / installed environment

```powershell
cd 'C:\Users\aadik\sih 2026\Gothamite-Release\gothamite'
.\.venv\Scripts\python.exe scripts/run_workbench.py

# In a separate terminal, frontend build:
cd 'C:\Users\aadik\sih 2026\Gothamite-Release\gothamite\frontend-react'
npm run build
npm run lint
node scripts/verify_workbench.mjs

# Backend regression suite (from app root):
.\.venv\Scripts\python.exe -m pytest tests -q
```

`.venv` exists with system-site-packages enabled and project requirements installed.
SQLAlchemy 2.1.1's wheel was blocked by Windows application control. Its official
pure Python build was installed successfully with:
`$env:DISABLE_SQLALCHEMY_CEXT='1'; .\.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps --no-binary sqlalchemy sqlalchemy==2.1.1`.

Vite 8 requires newer Node than system 22.11. Project devDependency `node@22.22.0`
provides a local runtime used by npm scripts. npm initially omitted required
native modules due to system Node's version; Windows x64 Rolldown and Oxlint
bindings were explicitly installed. The unused WASM fallback and redundant
optional Rolldown declaration were removed. The dependency setup targets Windows
x64; adjust platform bindings before other-OS installation. Runtime uses uvicorn
h11/asyncio for predictable Windows support. Prettier 3.6.2 formatted new workbench
TSX/CSS and the browser test; use `npm run format:workbench` for later edits.

## Latest verified state

TOR + case library pass (Claude Opus 5.5, 2026-09-29): `data_sources/tor/`
holds a frozen Onionoo snapshot (CC0); `importer.import_tor` adds tor_relay
entities and `tor_context`/`tor_relay` evidence with rule `tor-exact-ip-v1`
(exact normalized IPv4 only; reuse existing IP entities). Tor is context (+5,
dimension "TOR context"), never reputation. `services/workbench_library.py`
seeds INC-1047/1048/1051/1052 (synthetic) and presets INC-1049/1050 (dataset
cases made by the importer). Startup order: seed → library → import. Never fetch
Onionoo at runtime, never start Tor, never connect DarkForums and Infoblox.
Tests: 98 backend, 12/12 browser.

Dataset pass (Claude Opus 5.5, 2026-09-28): `backend/data_sources/` imports
filtered offline snapshots (DarkForums Safe Corpus, Infoblox; CC BY 4.0) as
provenance `dataset_derived` with a `wb_dataset_records` row each; DWData is
reference-only (no licence) and must never be downloaded or bundled. INC-1046 is
the dataset-backed case. Never link datasets to INC-1042/203.0.113.42, never
reverse redactions, never add live collection. Rebuild snapshots only with
scripts/prepare_datasets.py. See DATA_SOURCES.md.

Source adapter pass (Claude Opus 5.5, 2026-09-28): `backend/collection/` adds
adapter interfaces, normalized observations, SourceState, dedup, a deepdarkCTI
registry parser and synthetic MailAccess/horus/TorBot adapters. Live adapters are
process-isolated and off by default (GOTHAMITE_LIVE_COLLECTION + per-adapter
flag); horus/MailAccess live calls are intentionally unwired. Never vendor GPL
code, never wire MailAccess active probing or horus scanning, never add UI-driven
crawling. Tests run with subprocess forbidden. See THIRD_PARTY_NOTICES.md.

Content/realism pass (Claude Opus 5.5, 2026-09-28): no Ollama/LLM exists; the
legacy Streamlit views now compute from data instead of showing fabricated model
output. The stylometry signal is `lexical_similarity` (bag-of-words cosine).
Report has 9 sections (Executive summary … Audit trail). Never reintroduce AI,
live-collection or percentage-attribution claims without a real implementation.

Second polish pass (Claude Opus 5.5, 2026-09-28). See OVERNIGHT_PROGRESS.md
"Second polish pass" for the change list. Key new contracts:
- Case payload has `advance: {next, ready, requirement}`. `advance_requirement()` in
  workbench_cases.py is the single gate used by both the payload and PATCH.
- NIST rows carry `basis`, `evidence_ids`, `actions[{rule,title,category,status}]`.
- Report section 03 is "Automated interpretation (offline evidence rules)".
- Graph edges use orthogonal gutter/row-gap routing (`routeEdges`). The browser
  test asserts no edge passes through an unrelated node in the full graph.
- Formatting: use `npm run format:workbench` only. Do not run Prettier on legacy
  `src/pages`/`src/components`/`src/utils`; they use a different style.
- The persistent demo DB on 8042 was not mutated during this pass.

- Final production TypeScript/Vite build passed, including source formatting and
  static asset routing fixes. Main JS is about 212 KB / 70 KB gzip; routes are lazy.
- All 44 backend tests passed (43 original + NIST traceability/stage-gate test).
- Final lint exit 0: six existing set-state-in-effect warnings in legacy
  ArtifactModal, Graph (two), Timeline, Overview and Dossier. No new-workbench warnings.
- All 10 browser checks passed with zero console/page errors: command center,
  search/profile/incident, evidence drawer, graph, analysis/NIST, notebook persistence
  and inert HTML, reviewed simulation/stage advancement, report download,
  navigation/direct-route reload/pagination/legacy graph, and tablet/keyboard search.
- Notebook labels are fixed; the earlier selector timeout is resolved. Mobile
  sidebar closes on navigation. Vite bundles moved to `/static` to avoid the
  `/assets` inventory route collision. Dev proxy now points to the demo on 8042.
- Valid session cookies are reused across tabs; a regression assertion ensures
  opening another tab does not invalidate the first tab's CSRF token.
- Screenshots in `<app>\verification`: command-center.png, investigation.png,
  relationship-graph.png, response-review.png, tablet.png; example report is
  GOTHAMITE-INC-1042-example.md. Main, graph and tablet screenshots were inspected.
- Setup/start PowerShell scripts passed parser checks. Git diff --check passed.
  Fresh-machine installation has not been tested independently.
- Persistent demo was started at http://127.0.0.1:8042 and refreshed after polish.
  Health and `/assets` returned HTTP 200. Process state can change after this
  handoff; check before launching another server. Logs and PID are in
  `<app>\.local\` (ignored). Browser test port 8043 and temporary DB were cleaned up.

## Completed handoff and next work

Root README and app README now describe implemented behavior accurately.
ARCHITECTURE.md records design and security boundaries. OVERNIGHT_PROGRESS.md has
the required feature inventory, exact commands, demo path, limitations and next
steps. SETUP_GOTHAMITE.ps1 installs dependencies/builds; START_GOTHAMITE.ps1 runs
the persistent local demo. Setup preserves databases and uses the official pure
Python SQLAlchemy build to avoid this machine's native DLL restriction.

There is no known blocking failure in the verified primary demo flow. Useful next
work: validated evidence ingestion and user-created cases; explicit schema
migrations; optional model-backed analysis with evidence-reference evaluation;
production identity/roles/shared security state; locked Python dependencies and
clean-machine/CI coverage. These are future work, not completed capabilities.
Review the final progress file before choosing scope. Do not repeat finished
verification unless code changes or a new concern justify it.

## Important boundaries and environment issues

- No OpenAI/other model key was provisioned or used. Do not call rule-based output
  real model inference. Live feeds, actual EDR response, enterprise SSO/RBAC,
  durable multi-worker sessions, uploads and production deployment are unfinished.
- Older documentation says not to add LLM dependencies. Current user brief permits
  AI assistance, but offline evidence rules satisfy the credential-free demo path.
- Do not reset existing databases or analyst work to reseed. Seed is idempotent.
- Shell commands sometimes fail before execution with sandbox helper errors.
  Read commands usually work; affected execution commands worked after requesting
  normal escalation. Existing approvals cover npm build/lint/installs and pytest.
- The in-app browser tool failed before initialization (Windows sandbox
  `SetTokenInformation(TokenDefaultDacl) failed: 1344` / kernel exit). A local
  Playwright test using installed Edge works. No browser session/profile or secrets
  were inspected. Tests use fresh browser sessions and temporary test data.
- Do not assume a previous test failure is still present: read the current files.
- Source of NIST mapping: https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf
- Vite runtime requirement: https://vite.dev/guide/
- SQLAlchemy pure Python install: https://docs.sqlalchemy.org/en/21/intro.html
