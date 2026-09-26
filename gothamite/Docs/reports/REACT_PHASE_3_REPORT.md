# Phase 3 Report: React Migration — Graph Canvas & Evidence Inspector

## Built
- **Interactive Graph Canvas (`frontend-react/src/components/GraphCanvas.tsx`):**
  - Built interactive SVG canvas powered by `d3-force` simulation with bounded containment, charge repulsion, collision avoidance, and center attraction.
  - Renders all 6 nodes with source color coding (`forum-alpha` blue `#3498db`, `marketplace-beta` orange `#e67e22`, `forum-gamma` green `#2ecc71`), selection rings, and monospace handle labels beneath (`UI_SPEC.md` §5).
  - Renders all real edges with visual distinction: solid for `same_actor_suspected`, dashed for `transacted_with`. Edge thickness scales with confidence score (2px to 6px), and stroke color reflects the score band (emerald for ≥0.80, blue for 0.60–0.79, amber for 0.30–0.59, gray for <0.30).
  - Selected edge highlights in `--accent-cyan` (`#22D3EE`) while non-selected edges dim to ~35% opacity.
  - Rejected relationships render at ~15% reduced opacity, never hidden (`UI_SPEC.md` §5).
  - Canvas interactions: node dragging, canvas panning, wheel zooming, and zoom controls overlay (Zoom In, Zoom Out, Reset View).
  - Source and edge type legend overlay on the canvas.
- **Evidence Inspector (`frontend-react/src/components/EvidenceInspector.tsx`):**
  - **Edge Selection View:**
    - Link header displaying `from_handle ➔ to_handle` with source badges and relationship type.
    - Large `ScoreBadge` showing decimal score (`0.95`, `0.60`) and band label; strictly zero percentages (`SECURITY.md` §5).
    - Status pill (`proposed`, `confirmed`, `rejected`).
    - Confirm and Reject buttons calling live `PATCH /api/v1/graph/edge/{id}`. Buttons disable permanently once confirmed/rejected to prevent accidental status drift (`UX_SPEC.md` §10). Includes a dedicated "Reset State to Proposed" demo affordance.
    - Full evidentiary provenance trail rendering every signal via `EvidenceRow` with green/red direction indicators, signed weights (`+0.70`, `+0.45`, `+0.15`), observation notes, and clickable artifact links. Zero evidence summarized or hidden (`SECURITY.md` §4).
  - **Decoy Explanatory State (`UX_SPEC.md` §7):**
    - Selecting `nightjarr` (the decoy node) displays the system restraint explanatory state:
      - Explains why no link was formed: Nearest candidate `nightjar` (forum-alpha) triggered handle similarity (`+0.15`), but concurrent activity with conflicting cryptographic credentials triggered contradiction penalties (`−0.30`).
      - Net confidence falls below the 0.30 confidence floor, demonstrating algorithmic restraint against typosquatting.
      - Includes direct navigation link to `nightjarr` Dossier.
  - **Node Selection View:**
    - Displays observed persona metadata (handle, source badge, first/last seen dates, post counts) and quick navigation link to the Actor Dossier.
  - **Default Empty State:**
    - Explanatory guidance prompt instructing analyst to select an edge or node on the canvas.
- **Graph Page Routing & Two-Pane Layout (`frontend-react/src/pages/Graph.tsx`):**
  - Two-pane layout: 65% canvas left, 35% inspector right (`UI_SPEC.md` §5).
  - Quick Search bar filtering handles, PGP keys, and wallets with auto-focusing on nodes.
  - Toggle filter for transacted edges.
  - Deep linking support: `/graph?edge=<id>` pre-selects that edge on load.
  - Integrated `ArtifactModal` for inspecting immutable scraped source artifacts.

## Tested — how, not just whether
- **Headless Browser Automated Suite (`scripts/verify_phase3.ts`):**
  - Navigated to live app at `http://localhost:5173/graph` connecting to the running Docker backend.
  - **6 Node Verification:** Verified that all 6 nodes (`nightjar`, `n1ghtjar_`, `quillfeather`, `quill_v2`, `nightjarr`, `bellwether`) render with source colors and labels.
  - **3 Real Edges Verification:** Verified that all 3 edges render. Confirmed visual distinction: dashed edges (`stroke-dasharray="6,4"`) for `transacted_with` and solid lines for `same_actor_suspected`.
  - **Strict Security Audit (`SECURITY.md` §5):** Regex scan confirmed 0 occurrences of percentages across the entire page.
  - **Edge Inspection Flow (0.95 Link):**
    - Clicked `nightjar ↔ n1ghtjar_`.
    - Inspector populated with ScoreBadge (0.95, Very Strong), StatusPill (PROPOSED), and full evidence trail: `shared_pgp` (`+0.70`) and `shared_wallet` (`+0.45`).
    - Clicked "View" artifact: Confirmed `ArtifactModal` opens with SHA-256 hash, onion URL, Tor hop chain, and escaped plain-text body.
  - **Edge Inspection Flow (0.60 Link):**
    - Clicked `quillfeather ➔ quill_v2`.
    - Inspector populated with ScoreBadge (0.60, Strong), StatusPill (CONFIRMED), and evidence trail: `shared_wallet` (`+0.45`) and `temporal_succession` (`+0.15`).
  - **Decoy Node System Restraint (`UX_SPEC.md` §7):**
    - Clicked `nightjarr` decoy node on canvas.
    - Inspector rendered the Decoy Explanatory State: "Attribution Restraint · Verified Decoy Node", nearest candidate comparison with `nightjar`, supporting handle similarity (`+0.15`), contradicting credential penalty (`−0.30`), and net score below threshold (`0.00`).
  - **Confirm/Reject Review & Mutation Sync (`UX_SPEC.md` §10):**
    - Clicked "Confirm Link" on `nightjar ↔ n1ghtjar_`: Called live `PATCH /api/v1/graph/edge/{id}`, received 200, status updated to CONFIRMED, buttons disabled.
    - Used demo reset affordance to return to PROPOSED.
    - Clicked "Reject Link": Called `PATCH /api/v1/graph/edge/{id}`, received 200, status updated to REJECTED.
    - Verified canvas rendered the rejected edge at reduced opacity (~15%) without hiding it (`UI_SPEC.md` §5).
    - Reset link back to PROPOSED to preserve pristine baseline.
  - **Deep-Linking Verification:**
    - Navigated directly to `http://localhost:5173/graph?edge=1c19f923-f967-4a17-bce6-f9dcdce5836c`.
    - Confirmed edge was immediately pre-selected and inspector populated with `quillfeather ➔ quill_v2` evidence trail.
  - **Console Error Audit:**
    - Zero console errors recorded across the entire session.
- **Production Build & Lint:**
  - Ran `npm run build` (`tsc -b && vite build`): Succeeded in 1.11s with zero errors.
  - Ran `oxlint`: Passed with zero errors.

## Stubbed / faked / incomplete
- Dossier and Timeline screens remain route placeholders scheduled for Phase 4.

## Deviations from the docs
- None.

## Blocked
- None.

## Acceptance criteria
- [x] All 6 nodes render, colored by source, per `UI_SPEC.md` §5
- [x] All 3 real edges render against fresh live API call
- [x] Edge type visually distinguishable (solid vs dashed) before clicking
- [x] Clicking an edge populates the inspector with every evidence row, correct weights, correct signs
- [x] Score renders via `ScoreBadge`, correct color band, never a percentage
- [x] Confirm/Reject work, call the real `PATCH` endpoint, wait for response before updating UI, buttons disable after action per `UX_SPEC.md` §10
- [x] Clicking `nightjarr` (the decoy) shows the explanatory state from `UX_SPEC.md` §7
- [x] Rejected relationships render at reduced opacity, not hidden
- [x] Zero console errors through the full click-through sequence in `UX_SPEC.md` §6

## Ready for next phase: YES (Phase 4: Dossier + Timeline)
