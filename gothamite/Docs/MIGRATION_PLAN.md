# MIGRATION_PLAN.md

**Repo:** `GOTHAMITE`
**Prerequisites:** `UI_SPEC.md`, `UX_SPEC.md`, `docs/MASTER_CONTEXT.md`, `docs/ARCHITECTURE.md`
**Presentation:** 2-3 days out
**Runs in parallel with:** a separate fix for the relationship-status data bug (see §0). Different files, different session, no collision.

---

## 0. Before this starts — the thing that is not part of this migration

There is an active data-integrity bug: relationships have twice been found in an unexpected `status` (`rejected`, then `confirmed`) without a deliberate analyst action. This is being fixed **separately, in `backend/`, by a different session**, in parallel with this plan.

**This migration does not fix that bug and must not try to.** React will faithfully render whatever the API returns — correct or not. Before Phase 4 acceptance (below), re-verify `/api/v1/graph` shows the correct 3-edge state independent of anything done here.

---

## 1. Decision on record

Full replacement of the Streamlit frontend with React. Backend is untouched — same FastAPI service, same endpoints, same contract in `ARCHITECTURE.md` §4. This is a frontend-only rebuild.

**Old Streamlit code stays in the repo, untouched, until the React version is confirmed working end-to-end.** Do not delete `frontend/` until Phase 5 is signed off. If React breaks close to presentation day, Streamlit is the fallback and must remain runnable.

---

## 2. On "Stitch"

If this refers to **Google Stitch**, it is a UI *design/mockup* generator — it produces visual designs and can export frontend code scaffolding, but it is not a build tool a coding agent invokes mid-session as part of a normal dev workflow.

**How to actually use it, if at all:** generate initial component visual references or a starting layout for the Graph and Overview screens from the descriptions in `UI_SPEC.md`, then hand-adapt the output into the real React codebase. Treat anything it produces as a **visual starting point**, not final code — it will not know your API contract, your data model, or your state management approach, and it should not be trusted to wire up real data.

**Do not let Stitch output become the source of truth for interaction logic.** `UX_SPEC.md` is the source of truth for behavior. Stitch, if used, only ever informs `UI_SPEC.md`-level visual decisions.

If access to Stitch isn't actually available or working when this starts, skip it — build directly from `UI_SPEC.md` and `UX_SPEC.md`. They're written to be sufficient without it.

---

## 3. Stack

| Layer | Choice |
|---|---|
| Build tool | Vite |
| Framework | React 18 + TypeScript |
| Styling | Tailwind CSS (matches `UI_SPEC.md` §2 color tokens as CSS variables / Tailwind theme extension) |
| Routing | React Router |
| Graph rendering | `react-force-graph` or `reactflow` — pick whichever renders the score-colored, type-distinguished (solid/dashed) edges from `UI_SPEC.md` §5 with least friction. Report which and why |
| Timeline | A lightweight library (e.g. `visx` or hand-built SVG) — do not pull in a heavy Gantt library for 6 lanes |
| API calls | Native `fetch`, wrapped in a small typed client. No React Query / SWR — this app is small enough that manual fetch + state is simpler and has less to go wrong live |
| Icons | `lucide-react` |

No Redux, no GraphQL, no CSS-in-JS runtime library. Keep the dependency surface small — every added library is a new way for `npm install` to fail on presentation morning.

---

## 4. Directory

```
frontend-react/
├── src/
│   ├── main.tsx
│   ├── App.tsx                    ← router setup, top nav
│   ├── api/
│   │   └── client.ts              ← typed fetch wrapper, one function per endpoint
│   ├── components/
│   │   ├── ScoreBadge.tsx
│   │   ├── StatusPill.tsx
│   │   ├── EvidenceRow.tsx
│   │   ├── SourceBadge.tsx
│   │   └── MonoValue.tsx
│   ├── pages/
│   │   ├── Overview.tsx
│   │   ├── Graph.tsx
│   │   ├── Dossier.tsx
│   │   └── Timeline.tsx
│   ├── types/
│   │   └── api.ts                 ← TypeScript types matching DATA_MODEL.md §2 exactly
│   └── styles/
│       └── tokens.css             ← UI_SPEC.md §2 as CSS variables
├── index.html
├── package.json
├── tailwind.config.ts
└── vite.config.ts
```

`types/api.ts` matters more than it looks — it is the same discipline as `API_CONTRACT.md` on the sandbox side. Types must match `DATA_MODEL.md` §2 field-for-field. A drifted type produces silent `undefined`s in the UI, not a build error, which is a bad way to discover a mismatch live.

---

## 5. Phases

Same discipline as the backend build: **stop at each gate, commit, wait for confirmation before continuing.**

### Phase 1 — Scaffold + API client + types
**Build:** Vite/React/TS/Tailwind init. `api/client.ts` with a typed function per endpoint from `ARCHITECTURE.md` §4. `types/api.ts`. Design tokens from `UI_SPEC.md` §2 wired into Tailwind config. Top nav shell with four routes, each rendering a placeholder.

**Acceptance**
1. `npm run dev` runs clean, no console errors
2. All four routes navigate, placeholders render
3. `api/client.ts` successfully calls `GET /api/v1/graph` against the running Docker backend and logs the real response — prove the connection works before building any UI on top of it
4. Types compile with no `any` on core entities (Persona, Relationship, Evidence)

**Commit.** `git commit -m "phase 1: react scaffold, api client, types"`. Stop. Wait for confirmation.

---

### Phase 2 — Overview + shared components
**Build:** `ScoreBadge`, `StatusPill`, `EvidenceRow`, `SourceBadge`, `MonoValue`. Overview page: stat cards, source health, Run Correlation button, top relationships list.

**Acceptance**
1. Stat cards show real counts from the API
2. Run Correlation button calls `POST /api/v1/correlate`, shows loading state, updates counts on success — per `UX_SPEC.md` §5
3. Loading/empty/error states all implemented and manually triggered/verified (throttle network, kill the backend briefly, check zero-data state)
4. Shared components visually match `UI_SPEC.md` §6 and are actually reused — no duplicate score-rendering logic elsewhere

**Commit.** Stop. Wait for confirmation.

---

### Phase 3 — Graph + Evidence Inspector
**Highest-risk phase — this is the screen judges watch longest.**

**Build:** Graph canvas with chosen library, two-pane layout, evidence inspector, confirm/reject flow, decoy-node explanation per `UX_SPEC.md` §7.

**Acceptance — verify against real data, not mocked data**
1. All 6 nodes render, colored by source, per `UI_SPEC.md` §5
2. **All 3 real edges render** — re-confirm this against a fresh `/graph` call, independent of the parallel data-bug fix
3. Edge type visually distinguishable (solid vs dashed) before clicking
4. Clicking an edge populates the inspector with every evidence row, correct weights, correct signs
5. Score renders via `ScoreBadge`, correct color band, never a percentage
6. Confirm/Reject work, call the real `PATCH` endpoint, wait for response before updating UI, buttons disable after action per `UX_SPEC.md` §10
7. Clicking `nightjarr` (the decoy) shows the explanatory state from `UX_SPEC.md` §7 — this must work, it is the strongest demo moment
8. Rejected relationships render at reduced opacity, not hidden
9. Zero console errors through the full click-through sequence in `UX_SPEC.md` §6

**This phase's acceptance criteria are the actual test of whether the migration was worth doing.** If this screen isn't clearly better than the Streamlit version, the trade-off wasn't worth the time spent.

**Commit.** Stop. Wait for confirmation.

---

### Phase 4 — Dossier + Timeline
**Build:** both remaining pages per `UI_SPEC.md` §5 and `UX_SPEC.md` §9.

**Acceptance**
1. Dossier shows identifiers, linked personas with working links back to Graph, activity summary
2. Timeline shows 6 lanes, correct activity windows
3. **The `quillfeather` → `quill_v2` gap is immediately visually obvious** without explanation — this is a hard visual requirement, not a nice-to-have
4. Hover/click interactions per `UX_SPEC.md` §9 work
5. Search (Overview + Graph) returns correct results for handle, PGP, and wallet queries and navigates correctly

**Commit.** Stop. Wait for confirmation.

---

### Phase 5 — Integration, hardening, cutover
**Build:** nothing new. Reliability pass.

**Acceptance**
1. Full click-through demo flow (`UX_SPEC.md` §6) run twice, cold start, zero errors
2. Every §12 "must never happen live" item explicitly tested (kill backend mid-session, check the error state; throttle network, check loading states)
3. `docker-compose.yml` updated to serve `frontend-react` build output in place of Streamlit — **but Streamlit's `frontend/` directory and its compose service are commented out, not deleted**
4. Side-by-side sanity check: does React show the same data as Streamlit did? (Confirms nothing was lost in translation, and confirms the data bug fix from the parallel session is reflected correctly)
5. Recorded video of the full flow, same as `DEMO_SCRIPT.md` requires for the sandbox

**Only after this phase passes:** update `docs/DEMO_SCRIPT.md` screen references from Streamlit to React, and remove the Streamlit fallback if you're confident. Given the timeline, I'd keep Streamlit available as a silent fallback through the actual presentation day regardless.

**Commit.** Report final status.

---

## 6. Report format

Same as `IMPLEMENTATION_PLAN.md` §4 — Built / Tested-how / Stubbed / Deviations / Blocked / Acceptance checklist / Ready YES-NO. One file per phase in `docs/reports/`, named `REACT_PHASE_<n>_REPORT.md` — distinct prefix so these don't collide with the backend's phase reports of the same numbers.

**Commit after every phase, before the report.** `git commit -m "phase N: <what>"` then write the report as a separate commit or in the same one — either is fine, but the code commit must exist before you claim the phase is done.

---

## 7. Time reality check

Five phases in 2-3 days, in parallel with rehearsing the actual demo and the backend bug fix. This is tight. If Phase 3 (Graph + Evidence) runs long, that's acceptable — it's the screen that matters most. If time runs out, the priority order for what must be done vs. what can stay Streamlit-quality is:

1. Graph + Evidence Inspector — must be React, must be right
2. Overview — should be React, simple enough to not be the risk
3. Dossier, Timeline — acceptable to leave as Streamlit pages linked from the React app if time is critically short, rather than risk an unfinished React version of a lower-stakes screen

Say so explicitly in the final report if this fallback is used. Do not silently ship a partial migration described as complete.

---

## 8. Session prompt

Paste after `docs/MASTER_PROMPT.md`, in a session separate from whichever session is fixing the backend status bug:

```
You are migrating GOTHAMITE's frontend from Streamlit to React. Read, in order:
UI_SPEC.md, UX_SPEC.md, this file (MIGRATION_PLAN.md).

Scope: frontend-react/ only. Do NOT modify anything under backend/ — a separate session
is fixing a data bug there in parallel. If you notice incorrect data (wrong edge count,
wrong status), report it, do not attempt to fix it in the frontend or work around it in
the UI. See UX_SPEC.md section 10 for why silently compensating for backend state in
the frontend is specifically forbidden here — it already happened once on this project's
Streamlit build and caused a real problem.

Do not delete frontend/ (the Streamlit app) until Phase 5 passes. It is the fallback if
this migration does not finish in time.

Five phases, gated: build, commit, write a report to docs/reports/REACT_PHASE_<n>_REPORT.md,
STOP, wait for explicit confirmation before continuing. This applies even under time
pressure — especially under time pressure, since an unverified Phase 3 is worse than a
late one.

Presentation is 2-3 days out. If you must cut scope near the deadline, Graph + Evidence
Inspector (Phase 3) is the non-negotiable priority — see this file's section 7.
```
