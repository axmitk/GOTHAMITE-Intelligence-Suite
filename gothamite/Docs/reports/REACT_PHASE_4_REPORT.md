# Phase 4 Report: React Migration — Dossier & Timeline

## Built
- **Threat Actor Dossier (`frontend-react/src/pages/Dossier.tsx`):**
  - **Header & Search:**
    - Integrated actor selector dropdown with all personas labeled with their sources.
    - Multi-vector search input querying handles, PGP key fingerprints, and cryptocurrency wallet addresses via `GET /api/v1/entities/search`. Dropdown results display match reason and link directly to the matched dossier (`UX_SPEC.md` §8).
  - **Persona Profile Header (`UI_SPEC.md` §5):**
    - Large monospace handle display, source badge (`forum-alpha`, `marketplace-beta`, `forum-gamma`), source type badge, and copyable UUID `MonoValue`.
    - Profile metrics grid: First seen date, last seen date, computed active window span (e.g. `224 days active`), and total scraped post count.
    - Quick navigation buttons to "View in Graph" and "View in Timeline".
  - **Digital Identifiers Section (`UI_SPEC.md` §5):**
    - Categorized blocks for PGP fingerprints (purple badges) and cryptocurrency wallets (amber badges) with observation timestamps.
    - Truncate-with-copy `MonoValue` blocks with one-click clipboard copying.
    - Artifact provenance links: clicking "View Source" opens `ArtifactModal` displaying SHA-256 content integrity hash, onion target URL, audit hop chain, and escaped verbatim raw content (`SECURITY.md` §2).
  - **Correlated Cross-Source Linkages (`UI_SPEC.md` §5):**
    - Deterministic link cards displaying directional arrows, target handle, target source badge, `StatusPill` (`proposed`, `confirmed`, `rejected`), and `ScoreBadge` showing confidence (`0.95`, `0.60`). Strictly zero percentages (`SECURITY.md` §5).
    - Working deep link button ("Jump to Graph Edge") that navigates directly to `/graph?edge=<relationship_id>` and pre-selects the edge in the graph inspector (`UX_SPEC.md` §2).
    - Decoy node handling: explicitly renders a restraint notice ("No cross-source relationships proposed or confirmed") when inspecting unlinked actors such as `nightjarr`.
  - **Scraped Observation Timeline:**
    - Shows chronological observation history with timestamps, onion target URLs, escaped raw snippet previews, and artifact modal triggers.
  - **Resilient States:**
    - Skeleton placeholders matching layout during data retrieval (`UX_SPEC.md` §4).
    - Error fallback banner with retry affordance on API disconnect.

- **Temporal Activity Timeline (`frontend-react/src/pages/Timeline.tsx`):**
  - **Rebrand Migration Spotlight Banner (`UI_SPEC.md` §5, `DEMO_SCRIPT.md`):**
    - Prominent callout card spotlighting the `quillfeather ➔ quill_v2` migration.
    - Explains the 17-day succession gap (`2026-04-02` cessation on *forum-alpha* to `2026-04-19` emergence on *forum-gamma*), shared Bitcoin wallet (`1Kp7dR3z...`), and deterministic `0.60` confidence attribution.
    - Dynamically highlights when either quill persona is hovered.
  - **Interactive 6-Lane Gantt Chart (`UI_SPEC.md` §5, `UX_SPEC.md` §9):**
    - 6 persona lanes arranged in juxtaposed order (`nightjar`, `n1ghtjar_`, `quillfeather`, `quill_v2`, `nightjarr`, `bellwether`) so that the migration pair is directly adjacent.
    - Source color mapping: blue `#3498db` (`forum-alpha`), orange `#e67e22` (`marketplace-beta`), and green `#2ecc71` (`forum-gamma`).
    - **Visual 17-Day Gap Marker:** Dashed callout bar with amber badge ("17-Day Gap") positioned between `quillfeather`'s end and `quill_v2`'s start, making the temporal handoff immediately obvious without verbal explanation (`MIGRATION_PLAN.md` Phase 4 item 3).
    - **Synchronized Hover Interaction (`UX_SPEC.md` §9):** Hovering either `quillfeather` or `quill_v2` triggers a synchronized double-bar highlight (`ring-2 ring-accent-cyan opacity-100 scale-y-105`), reinforcing that the two lanes represent the same physical actor.
    - **Click Navigation:** Clicking any persona's activity bar or handle navigates directly to `/dossier/:personaId`.
    - Horizontal month grid lines (Jan 2026 – Aug 2026).
  - **Chronological Observation Stream (`UI_SPEC.md` §5):**
    - Aggregates observation events from dossiers sorted chronologically.
    - Filter controls for Persona and Source with accessible labels.
    - Event cards showing date, persona handle, source badge, observation type, snippet value, and artifact inspection button.

## Tested — how, not just whether
- **Headless Browser Automated Suite (`scripts/verify_phase4.ts`):**
  - Ran automated Playwright test suite against the live Docker FastAPI backend and Vite development server:
    1. **Dossier Default Route & Redirection:** Verified `/dossier` redirects to `/dossier/cc7778c3...` (`nightjar`).
    2. **Profile Metrics:** Verified handle, source badge, first/last seen dates, active window span (`224 days active`), and total posts (`12`).
    3. **Digital Identifiers:** Verified 3 copyable `MonoValue` blocks rendered with clipboard copy buttons.
    4. **Artifact Modal Integration:** Clicked "View Source" on identifier; verified modal rendered with SHA-256 hash (`sha256:e84eb99c...`), onion URL, relay hop chain, and escaped HTML body.
    5. **Graph Jump Navigation:** Clicked "Jump to Graph Edge"; confirmed navigation to `/graph?edge=c44a1af1...` and verified that the Graph Evidence Inspector immediately loaded with the confidence score and signal rows.
    6. **Multi-Vector Search:**
       - Searched for handle `"quillfeather"`; verified dropdown result appeared and clicking it navigated to `/dossier/a277ecd2...` (`quillfeather`).
       - Searched for wallet address `"1Kp7dR3z"`; verified matching personas were returned.
    7. **Decoy Node Dossier:** Selected `nightjarr (forum-gamma)`; verified profile loaded and confirmed zero cross-source relationships were proposed or confirmed.
    8. **Timeline 6-Lane Rendering:** Verified all 6 lanes rendered in correct juxtaposed order (`nightjar`, `n1ghtjar_`, `quillfeather`, `quill_v2`, `nightjarr`, `bellwether`).
    9. **Visual 17-Day Gap Marker:** Confirmed visual dashed gap marker with "17-Day Gap" badge is rendered between `quillfeather` and `quill_v2`.
    10. **Synchronized Hover Interaction:** Hovered over `quillfeather` lane and verified that both `quillfeather` and `quill_v2` activity bars received active highlight rings (`ring-2 ring-accent-cyan`).
    11. **Bar Click Navigation:** Clicked `quill_v2` activity bar; confirmed immediate navigation to `/dossier/d6fdbc58...` (`quill_v2`).
    12. **Observation Stream & Filtering:**
        - Verified 19 total chronological observation events rendered.
        - Filtered by Persona `"quill_v2"`; verified event count narrowed to 3 events.
        - Filtered by Source `"forum-gamma"`; verified event count narrowed to 6 events.
        - Opened artifact modal from observation event; verified SHA-256 hash.
    13. **Overview & Graph Search Interoperability:**
        - Verified Overview quick search for `"nightjar"` navigated to `/dossier/cc7778c3...`.
        - Verified Graph quick search for `"quill"` found matching nodes and focused them on the canvas.
    14. **Strict Security Audit (`SECURITY.md` §5):** Regex scan confirmed 0 occurrences of percentage characters across the entire rendered content of both Dossier and Timeline pages.
    15. **Console Error Audit:** Confirmed 0 console errors logged across all test sequences.
- **Production Build & Lint Verification:**
  - Ran `oxlint`: 0 errors.
  - Ran `npm run build` (`tsc -b && vite build`): Succeeded in 1.31s with zero errors.

## Stubbed / faked / incomplete
- None. All four primary screens (`Overview`, `Graph`, `Dossier`, `Timeline`) are completely built and wired to the live FastAPI backend.

## Deviations from the docs
- None.

## Blocked
- None.

## Acceptance criteria
- [x] Dossier shows identifiers, linked personas with working links back to Graph, activity summary
- [x] Timeline shows 6 lanes, correct activity windows
- [x] The `quillfeather` → `quill_v2` gap is immediately visually obvious without explanation
- [x] Hover/click interactions per `UX_SPEC.md` §9 work
- [x] Search (Overview + Graph) returns correct results for handle, PGP, and wallet queries and navigates correctly
- [x] Strict zero-percentage compliance across all screens (`SECURITY.md` §5)
- [x] Zero console errors across all test sequences

## Ready for next phase: YES (Phase 5: Integration, hardening, and cutover)
