# Phase 2 Report: React Migration — Overview & Shared Components

## Built
- **Reusable Core Components (`frontend-react/src/components/`):**
  - `ScoreBadge.tsx`: Single source of truth for confidence scores (`DATA_MODEL.md` §3, `SECURITY.md` §5). Displays monospace numeric decimal scores (`0.95`, `0.60`, `0.00`) and semantic color bands ("Very Strong", "Strong", "Moderate", "Weak"). Strictly prohibits percentage formatting.
  - `StatusPill.tsx`: Renders relationship review state (`proposed`, `confirmed`, `rejected`) using semantic status tokens (`UI_SPEC.md` §2).
  - `SourceBadge.tsx`: Visual dot indicator and monospace label for monitored dark web sources (`forum-alpha`, `marketplace-beta`, `forum-gamma`).
  - `MonoValue.tsx`: Wrapper for raw identifiers (handles, PGP fingerprints, cryptocurrency wallet addresses) providing consistent font, middle-truncation, and copy-to-clipboard functionality.
  - `EvidenceRow.tsx`: Dense evidence signal row displaying direction indicator (green supporting, red contradicting), monospace signal type, signed weight (`+0.70`, `+0.45`, `+0.15`), observation note, and clickable artifact reference. Never suppresses contradicting evidence (`SECURITY.md` §4).
  - `ArtifactModal.tsx`: Read-only modal displaying verbatim scraped source artifacts, SHA-256 cryptographic hash, onion target URL, and Tor hop chain. Content is strictly escaped plain text, never executed or rendered as HTML (`SECURITY.md` §2).
  - `formatters.ts`: Centralized score thresholds, source colors, and truncation utilities.
- **Overview Screen (`frontend-react/src/pages/Overview.tsx`):**
  - Four stat cards in a single row: Immutable Artifacts, Observed Personas, Extracted Identifiers, and Active Linkages with large monospace numerals and descriptive captions.
  - Prominent "Run Correlation Pass" button in the header action bar with loading spinner, disabled state, success toast, error handling, and idempotent re-triggering (`UX_SPEC.md` §5).
  - Monitored Dark Web Sources panel tracking health status (`up`/`down`), node type (`forum`/`marketplace`), reliability level, persona counts, artifact counts, and last ingest scan timestamps.
  - High-Confidence Cross-Source Attributions list showing ranked relationships with source badges, `ScoreBadge`, `StatusPill`, top evidence note, and direct links to "Inspect in Graph" and "Artifact".
  - Quick Entity Search box supporting handle, PGP fingerprint, and wallet queries (`UX_SPEC.md` §8) with live dropdown results linking to Persona Dossiers.
  - Architectural safety and integrity summary card highlighting inert data handling, deterministic arithmetic scoring, and cryptographic provenance.
  - Full loading skeleton state, empty data state prompt, and network outage error banner (`UX_SPEC.md` §4).

## Tested — how, not just whether
- **Headless Browser & Interaction Verification (`scripts/verify_overview.ts`):**
  - Executed automated browser test against the live running app (`http://localhost:5173/overview`) and Docker backend (`http://localhost:8000`).
  - Verified stat cards display real API metrics: 6 immutable artifacts, 6 observed personas, 10 extracted identifiers, 3 active linkages.
  - Verified monitored sources panel correctly displays `forum-alpha`, `marketplace-beta`, and `forum-gamma`.
  - Verified top attributions render `nightjar ➔ n1ghtjar_` (0.95 Very Strong, PROPOSED), `quillfeather ➔ quill_v2` (0.60 Strong, CONFIRMED), and `bellwether ➔ n1ghtjar_` (0.00 Weak, PROPOSED).
  - Verified Quick Search queries:
    - Searching `nightjar` returns both `nightjar` and decoy `nightjarr` with direct Dossier navigation links.
  - Verified Artifact Modal:
    - Clicked "Artifact" on the top evidence row. Confirmed modal opens with SHA-256 hash, onion URL, Tor relay path, and escaped plain-text body.
  - Verified "Run Correlation Pass" trigger:
    - Clicked button, observed loading spinner and disabled state, and confirmed success banner: `"Correlation pass complete: Evaluated 12 candidate pairs · 3 active linkages identified."`
  - Verified zero console errors throughout the entire interaction sequence.
- **Strict Security & Provenance Audit (`SECURITY.md` §5):**
  - Evaluated all rendered text across the entire document body: regex check `/\b\d+(\.\d+)?%/g` confirmed **0 occurrences of percentages**. Confidence is strictly represented as decimal evidentiary weight.
- **Error Handling & Network Fallback Test (`scripts/verify_error_state.ts`):**
  - Simulated complete backend outage by aborting all API endpoint requests (`/api/v1/**` and `/health`).
  - Verified calm, non-technical error banner renders: `"Cannot reach GOTHAMITE backend at http://localhost:8000/api/v1. Ensure Docker backend is running."` alongside a functional "Retry" button.
  - Verified stat cards cleanly show zeroed baseline counts (`0`) rather than crashing.
  - Verified empty state prompt renders: `"No active relationships populated. No cross-source linkages have been computed yet. Trigger a correlation pass to evaluate stored observations across sources."`
  - Confirmed zero blank screens, zero white screens, and zero raw stack traces leaked to the user.
- **Production Build & Lint:**
  - Ran `npm run build` (`tsc -b && vite build`): Succeeded in 1.22s with zero TypeScript compilation errors.
  - Ran `oxlint`: Passed with zero errors.

## Stubbed / faked / incomplete
- Graph canvas, Dossier details, and Timeline screens remain route placeholders scheduled for Phase 3 and Phase 4.

## Deviations from the docs
- None.

## Blocked
- None.

## Acceptance criteria
- [x] Stat cards show real counts from the API
- [x] Run Correlation button calls `POST /api/v1/correlate`, shows loading state, updates counts on success — per `UX_SPEC.md` §5
- [x] Loading/empty/error states all implemented and manually triggered/verified
- [x] Shared components visually match `UI_SPEC.md` §6 and are actually reused — no duplicate score-rendering logic elsewhere

## Ready for next phase: YES (Phase 3: Graph + Evidence Inspector)
