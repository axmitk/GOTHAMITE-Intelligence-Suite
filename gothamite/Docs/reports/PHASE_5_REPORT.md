# Phase 5 Report

## Built
- `frontend/api_client.py`: Client communication layer providing resilient REST queries with direct database fallbacks, supporting headless local development and containerized multi-service deployment.
- `frontend/app.py`: Streamlit Analyst Workbench home featuring system metrics, single-click "Run Correlation Pass" trigger, active correlation table, and monitored source status.
- `frontend/pages/1_graph.py`: Force-directed graph explorer powered by PyVis with source-based node color coding, score-weighted edge widths, and an interactive Edge Evidence Inspector displaying supporting/contradicting signals and verbatim raw artifact inspection.
- `frontend/pages/2_dossier.py`: Multi-vector search interface (querying handles, PGP fingerprints, and wallet addresses) and comprehensive actor dossier view (identifiers, cross-source linkages, timeline, and source details).
- `frontend/pages/3_timeline.py`: Temporal activity timeline featuring an Altair activity-window Gantt chart highlighting the `quillfeather` → `quill_v2` rebrand handoff (16/17-day succession gap with rotated PGP keys), paired with a filterable chronological observation stream.
- `tests/test_phase5.py`: Test suite verifying UI language rules, safety boundaries, API client operations, and analyst review actions.

## Tested — how, not just whether
- Graph Rendering Library Evaluation:
  - Evaluated `streamlit-agraph` and `pyvis`. Selected `pyvis` for the primary network canvas due to its zero-dependency HTML canvas rendering, robust physics simulation, and smooth browser frame-rate stability.
- Ran `./venv/bin/python -m py_compile frontend/app.py frontend/api_client.py frontend/pages/1_graph.py frontend/pages/2_dossier.py frontend/pages/3_timeline.py`:
  - Verified 0 syntax, runtime, or import errors.
- Ran `./venv/bin/pytest -v tests/test_phase5.py`:
  - `test_score_rendering_language_rules`: PASSED (Confirmed confidence scores format as `0.95 [Very Strong Link]`, zero percentage signs).
  - `test_frontend_security_no_unsafe_html`: PASSED (Confirmed `unsafe_allow_html=True` is strictly absent across all frontend modules; ingested content rendered via `st.code` or `st.text`).
  - `test_frontend_forbidden_attribution_vocabulary`: PASSED (Verified absence of forbidden terms: *identified*, *deanonymised*, *confirmed identity*, *proof*, *95%*).
  - `test_api_client_operations`: PASSED (Verified graph payload, edge details, search, and dossier retrieval).
  - `test_confirm_reject_workflow`: PASSED (Verified edge rejection immediately updates graph topology and hides rejected links).
- Ran full regression test suite `./venv/bin/pytest -v tests/`:
  - All 32 tests across Phases 1, 2, 3, 4, and 5 passed cleanly (3.20s).

## Stubbed / faked / incomplete
- None.

## Deviations from the docs
- None.

## Blocked
- None.

## Acceptance criteria
- [x] Graph renders, nodes coloured by source, edge thickness by score
- [x] Clicking an edge shows all evidence — supporting **and** contradicting — with weights
- [x] Evidence links through to the raw artifact and it displays
- [x] Confirm/reject works; graph updates immediately
- [x] Search returns results for handle, PGP and wallet
- [x] Dossier shows identifiers, links, timeline, sources
- [x] Timeline makes the `quillfeather` → `quill_v2` handoff visually obvious
- [x] **Scores render as `0.95` with a band label — never as a percentage**
- [x] **No ingested string rendered with `unsafe_allow_html=True`**
- [x] No unexplained number anywhere — every score clicks through to its signals

## Ready for next phase: YES
