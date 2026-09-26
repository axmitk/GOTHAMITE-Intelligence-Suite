# UX_SPEC.md

**Repo:** `GOTHAMITE`
**Scope:** `frontend-react/` only.
**Prerequisites:** `UI_SPEC.md`, `docs/DEMO_SCRIPT.md`, `docs/ARCHITECTURE.md` §4 (API contract)

This is interaction and state: what happens on click, what loading/empty/error look like, and the exact flows that must work live on stage. `UI_SPEC.md` covers how it looks.

---

## 1. Non-negotiable: this must survive a live demo

`DEMO_SCRIPT.md` describes a 6-7 minute run in front of judges, on a laptop, possibly on an unfamiliar projector/network. Every interaction spec below is written with that constraint first. A beautiful interaction that's one network hiccup from a blank screen is worse than a plain one that degrades visibly and recoverably.

### 1.1 Role of Google Stitch vs. Interaction Logic
Google Stitch informs visual mockup exploration only (see `UI_SPEC.md` §1.1 and `MIGRATION_PLAN.md` §2):
- **Stitch is not the source of truth for behavior, state management, or API communication.**
- All user interactions, loading/empty/error states (§4), correlation triggers (§5), the core Graph → Evidence flow (§6), decoy handling (§7), search behavior (§8), timeline interactions (§9), and confirm/reject semantics (§10) are authoritatively defined by this document (`UX_SPEC.md`).
- Mockup code output from Stitch must never dictate client state transitions, error boundaries, or backend API wiring.

---

## 2. Navigation

- Four top tabs: Overview, Graph, Dossier, Timeline. Client-side routing, no full page reload between them
- Active tab visually distinct (underline or filled background, per `UI_SPEC.md` accent color)
- Deep-linkable: `/graph?edge=<id>` should open Graph with that edge pre-selected, `/dossier/<persona_id>` should open a specific dossier directly. This makes "click through from Dossier to Graph" and "click through from Timeline to Dossier" actual navigations, not dead ends
- No modal-based navigation. Everything is a real route

---

## 3. Data fetching

- On mount, each screen fetches what it needs from the FastAPI backend directly — no client-side caching layer, no state management library beyond React's built-in state/context. This is a small app; Redux or similar is not warranted
- Poll or refetch is manual, not automatic. A "Refresh" affordance on Overview and Graph, not a background interval — this keeps behavior predictable during a live demo (no surprise re-renders mid-sentence)
- API base URL is an environment variable, not hardcoded, so it can point at Docker's internal network or `localhost` depending on how it's run — this is exactly the class of bug that broke the Streamlit build (`ModuleNotFoundError` from a hardcoded path assumption). Do not repeat it

---

## 4. Loading, empty and error states — every screen needs all three

| State | Behavior |
|---|---|
| **Loading** | Skeleton placeholders matching the eventual layout (not a spinner-only blank screen). Graph canvas shows a dimmed placeholder grid while nodes load |
| **Empty** | Before any correlation has run: Overview shows zeroed stat cards with a clear "Run Correlation to populate the graph" prompt, not a blank page. Graph with zero edges shows nodes only, with a message explaining no relationships have been found yet — this is a valid state, not an error |
| **Error** | If the API is unreachable: a clear, calm banner — "Cannot reach GOTHAMITE backend at `<url>`" — never a raw stack trace or a white screen. This is the React equivalent of the Streamlit crash you already hit once; do not let it happen silently again |

**Every fetch call needs a try/catch with a real fallback UI.** No screen may render blank on a failed request.

---

## 5. The correlation trigger

"Run Correlation" (Overview) calls `POST /api/v1/correlate`.

- Button shows a loading state (spinner + disabled) while the request is in flight
- On success: toast/banner confirming counts ("3 relationships active"), and the stat cards update
- On failure: clear error banner, button re-enables, no silent failure
- This is idempotent per `INVESTIGATION_PIPELINE.md` §3 — running it twice is always safe and expected. Nothing in the UI should warn against re-running it

---

## 6. The core demo flow — Graph → Evidence → Confirm/Reject

This is what `DEMO_SCRIPT.md` §4 walks through live. It must be smooth.

1. **Land on Graph.** Nodes and edges render. Default: no edge selected, inspector shows a placeholder ("Select an edge to inspect evidence")
2. **Click the `nightjar ↔ n1ghtjar_` edge.** Inspector populates: score 0.95, band "Very Strong", every evidence row (PGP +0.70, wallet +0.45), each with its artifact reference
3. **Click "View Source Artifact."** Opens the raw artifact — escaped, read-only text, never rendered as HTML (`SECURITY.md` §2). This can be an inline expansion or a side panel; not a new route, to keep the demo flow uninterrupted
4. **Click the `quillfeather → quill_v2` edge.** Same pattern, score 0.60, two evidence rows, wallet + temporal succession
5. **Click on `nightjarr`, the decoy node.** No edge exists to select — this must be **visually explainable without an edge to click**. See §7
6. **Confirm or reject an edge.** Click Confirm on the 0.95 link → status pill updates immediately, button state updates, no page reload. Click Reject on something → edge dims to the rejected-opacity state from `UI_SPEC.md` §5, stays visible but muted

Every step above must work with zero console errors and no loading flicker longer than ~300ms on a normal connection.

---

## 7. Handling the decoy — the most important UX moment in the app

`nightjarr` has **no edge** to `nightjar`. That's the point — it's the correct rejection, and it's arguably your strongest demo beat per `REQUIREMENTS.md` §3. But "nothing happens when you click it" is a weak interaction on its own.

**Required:** clicking a node with no strong relationships shows a small state in the inspector panel explaining *why* — something like: "No relationship proposed. Nearest candidate: `nightjar` (handle similarity only, activity windows conflict — net signal below threshold)." This can be computed client-side by checking if a near-miss exists in reasoning shown elsewhere (the correlation report), or — better — expose a lightweight `GET /api/v1/entities/near-misses/{persona_id}` style read on the backend if time allows. If backend time doesn't allow it, hardcode this specific explanatory string for the demo persona, clearly commented as a demo-specific affordance, not a general capability.

This turns your strongest result from "notice what's absent" (hard to stage-manage) into "click and see the system explain its own restraint" (an actual interaction).

---

## 8. Search

- Single search box, present on Overview and Graph
- Searches handle, PGP fingerprint, wallet — matches `GET /api/v1/entities/search`
- Results as a small dropdown/list beneath the box; selecting a result navigates to that persona's Dossier
- Empty query shows nothing (not "no results") — don't imply a search happened when it didn't
- No results for a real query shows an explicit "No matches" state

---

## 9. Timeline interaction

- Hovering a persona's activity bar shows a tooltip: handle, source, first_seen → last_seen, post_count
- Clicking a bar navigates to that persona's Dossier
- The `quillfeather` / `quill_v2` gap should be independently noticeable without a click — this is a visual requirement from `UI_SPEC.md` §5, but the interaction requirement here is: hovering near the gap should make it obvious this is a *deliberate* juxtaposition, e.g., both bars highlight together on hover of either

---

## 10. Confirm/Reject semantics — must match backend exactly

- Confirm/Reject buttons call `PATCH /api/v1/graph/edge/{id}` with the new status
- **Buttons are disabled entirely (not just visually, actually disabled) once a relationship is already `confirmed` or `rejected`**, to prevent accidental re-toggling live on stage. If re-toggling is wanted for demo purposes, require a distinct "Reset to proposed" action, not a re-click of Confirm/Reject — this is a direct response to the status-drift bug that already happened twice on the Streamlit build. Make it structurally harder to accidentally mutate demo state
- No optimistic UI update before the API confirms — wait for the `200` response, then update. A demo where the UI shows "confirmed" but the backend call actually failed is a worse failure mode than a half-second of visible waiting

---

## 11. Responsive behavior

- Design for a laptop screen (1366-1920px wide), presented via projector or screen-share. Not mobile-first
- The Graph screen's two-pane layout may stack vertically below ~1024px, but this is a fallback, not the primary target — verify the actual demo machine's resolution before the day and design for that specifically if known

---

## 12. What must never happen live

- A blank white/black screen with no explanation
- A raw JSON error or stack trace visible to the audience
- An edge silently changing status without an explicit, deliberate click
- The evidence panel showing partial evidence (some rows rendered, others dropped) — if the evidence array is incomplete, show a visible warning, don't render a plausible-looking partial list
- Any percentage-based score display, anywhere, per `SECURITY.md` §5
