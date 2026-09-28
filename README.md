# GOTHAMITE

An evidence-first cyber-intelligence investigation workbench that runs fully
offline: search an indicator, inspect evidence and relationships, investigate a
case, review risk and NIST CSF 2.0 alignment, approve a response simulation, and
export the report. React, FastAPI and SQLite support persistent analyst work.

**Every record carries one provenance label: synthetic (the exercise and case
library), dataset-derived (filtered public snapshots: DarkForums Safe Corpus,
Infoblox, Tor Project Onionoo) or reference-derived (DWData-shaped
reconstructions). Analysis uses offline evidence rules, not an LLM. Response
simulations never change external systems. Nothing is collected live.**

## Run on this Windows machine

Dependencies and the production frontend are already installed in this checkout.

```powershell
cd 'C:\Users\aadik\sih 2026\Gothamite-Release'
.\START_GOTHAMITE.ps1
```

Open **http://127.0.0.1:8042**. The server binds loopback only; Ctrl+C stops it.
If this session's demo is already running, open the URL directly.

For a fresh Windows x64 installation, install Python 3.12+ and Node 22.22+, then:

```powershell
.\SETUP_GOTHAMITE.ps1
.\START_GOTHAMITE.ps1
```

Setup downloads dependencies, creates a virtual environment if needed and builds
the frontend. It preserves databases. If PowerShell blocks downloaded scripts,
inspect them and run their listed commands manually under your organization's policy.
This checkout explicitly includes Windows x64 bundler/linter bindings; other
platforms need those dependencies adjusted. npm scripts use project-local Node
22.22. System Node 22.11 can emit engine warnings during installation.

## Five-minute demo

1. On **Command center**, review the 11-case queue and the provenance labels.
2. Search **203.0.113.42** using global search (Ctrl+K).
3. Open the IOC profile, then **Relationship graph**. Select **Finance gateway
   beaconing** and **Open investigation** (INC-1042).
4. Inspect an evidence item's source, raw observation and SHA-256 hash. In **Graph**,
   select **Grey Moth** and inspect a relationship's supporting evidence.
5. In **Analysis**, run evidence analysis. Each finding shows its confidence,
   reasoning factors, supporting evidence and recommended next step. Inspect the
   risk factors. In **NIST alignment**, each CSF function cites its evidence and
   linked response actions. Save a notebook hypothesis.
6. In **Response**, approve **Isolate affected endpoint**, then **Run simulation**.
   **Advance to containment** stays disabled, with its prerequisite stated, until
   a containment or hunt simulation exists. The decision audit trail records
   approval, simulation and progression.
7. In **Report**, export Markdown with observed evidence, correlated context,
   automated interpretation, risk, NIST mapping, response decisions and the
   analyst approval record in separate sections.

8. Optional: search **185.220.100.242** to see Tor exit-node context (INC-1047),
   or **claudfront.net** to see an indicator listed by three Infoblox reports.

The hero case begins in INVESTIGATING. Notes and actions persist, so a previously
exercised case may be further along. Seeding never resets it.

| Cases | What they exercise |
| --- | --- |
| INC-1042 to INC-1045 | Original synthetic exercise: beaconing (hero), exposed service identity, staging, unverified scanning |
| INC-1046 | Dataset-derived Decoy Dog DNS review (Infoblox) |
| INC-1047 to INC-1052 | Case library: Tor context, multi-source corroboration, forum claim, repeated Infoblox IOC, credential exposure (placeholders), lookalike domain |

A fresh database holds 510 indicators (259 synthetic, 251 dataset-derived), 664
evidence items (148 synthetic, 510 dataset-derived, 6 reference-derived), 639
relationships and 12 assets.

## Development and checks

```powershell
cd gothamite
.\.venv\Scripts\python.exe -m pytest tests -q
cd frontend-react
npm run build
npm run lint
npm run test:e2e
```

Current results: 98 backend tests, 12/12 browser checks with no console errors,
a clean production build and 6 pre-existing lint warnings in legacy pages.
The browser check uses installed Microsoft Edge, a fresh temporary database and
port 8043. Screenshots and an example report go to `gothamite/verification/`.
Set `GOTHAMITE_BROWSER=chrome` to use an installed Chrome channel instead.
Keep port 8043 free while running the check.

For frontend hot reload, keep the demo backend running and run `npm run dev` from
`gothamite/frontend-react`. Open http://localhost:5173; Vite proxies API calls to 8042.

## Architecture and data

- `gothamite/frontend-react/src/workbench/`: React application and case workspace.
- `gothamite/backend/api/workbench.py`: investigation API.
- `gothamite/backend/services/workbench_*.py`: seed, search, graph, analysis,
  case lifecycle, reports and local session checks.
- `gothamite/backend/services/workbench_library.py`: case library INC-1047 to INC-1052.
- `gothamite/backend/data_sources/`: bundled dataset snapshots, manifest, safety
  filter and offline importer (DarkForums, Infoblox, Tor Onionoo, DWData reconstruction).
- `gothamite/backend/collection/`: source adapter layer (synthetic fixtures by default).
- `gothamite/backend/models/workbench.py`: additive SQLAlchemy tables.
- `gothamite/workbench-demo.db`: persistent SQLite database (ignored by Git).
- `gothamite/backend/demo.py`: seeded, same-origin demo entrypoint and SPA hosting.

Set `GOTHAMITE_DB_PATH` to another file for a separate exercise. For a custom
`GOTHAMITE_PORT`, also set `GOTHAMITE_ORIGINS` to the exact browser origin.
Preserve any database containing analyst work.

Existing persona overview, graph, dossiers and timeline remain at /overview,
/graph, /dossier and /timeline. Legacy Streamlit runs separately; see
[the app README](gothamite/README.md).

## Boundaries

Collection: the workbench loads synthetic source observations from a
reproducible seed and public datasets from bundled snapshots. The companion `darkweb-sandbox` demonstrates collection from
mock hidden services over a simulated relay network. Scheduled or continuous
ingestion through source adapters is the deployment architecture, not a running
service; see [architecture](ARCHITECTURE.md#collection-model).

Public datasets: filtered snapshots of the DarkForums Safe Corpus and Infoblox
Threat Intelligence (both CC BY 4.0) are imported offline at startup as
**dataset-derived** evidence, shown with a distinct provenance badge, and backed
by INC-1046. DWData is reference-only (no licence). The canonical 203.0.113.42
investigation remains synthetic. See [data sources](DATA_SOURCES.md).

TOR exit-node intelligence: a bounded Tor Project Onionoo snapshot (18 relays,
published 2026-09-28 17:00 UTC, CC0) is imported offline. An IP that exactly
matches a relay address gets a TOR infrastructure section, a small "TOR exit node"
badge, an `ASSOCIATED_WITH` edge to the relay and a +5 "TOR context" risk factor.
Tor association is context, never a malicious verdict. GOTHAMITE never contacts
Onionoo or starts Tor.

Case library: INC-1047 to INC-1052 add Tor context, multi-source corroboration,
a forum claim, a repeated Infoblox IOC, a credential exposure (placeholders only)
and a lookalike domain, each in a different workflow and response state. They are
deliberately synthetic or dataset-derived exercises, not real incidents.

Source adapters: `gothamite/backend/collection/` normalizes MailAccess-,
horus- and TorBot-shaped findings and the deepdarkCTI source catalogue into one
observation model. In this build every adapter runs on synthetic fixtures; live
execution is off by default and needs explicit opt-in. See
[third-party notices](THIRD_PARTY_NOTICES.md) for what is integrated versus
architectural only.

This is a single-process local prototype. Its demo session is not SSO or user
authentication. No live feeds, dark-web crawling, Tor connection, model API, real
endpoint containment, arbitrary case creation or evidence uploads are implemented.
NIST CSF 2.0 labels organize the workflow; they do not certify compliance.
Risk expresses triage priority, not a probability or proof of attribution.

See [architecture](ARCHITECTURE.md), [completed work and limitations](OVERNIGHT_PROGRESS.md),
and [Claude continuation context](CLAUDE_CONTEXT.md). Preview the
[command center](gothamite/verification/command-center.png).
