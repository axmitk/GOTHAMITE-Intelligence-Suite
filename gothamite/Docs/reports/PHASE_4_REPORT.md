# Phase 4 Report

## Built
- `backend/services/graph_service.py`: Stateless NetworkX graph construction and queries on demand (`build_networkx_graph`, `get_graph_payload`, `get_edge_details`, `update_edge_status`). Excludes rejected edges from the active graph.
- `backend/services/export_service.py`: RFC 8259 JSON and CSV bundle generator embedding mandatory source `artifact_id` across every evidence row.
- `backend/api/graph.py`: REST endpoints `GET /api/v1/graph`, `GET /api/v1/graph/edge/{id}`, and `PATCH /api/v1/graph/edge/{id}` for analyst confirmation and rejection.
- `backend/api/entities.py`: REST endpoints `GET /api/v1/entities/search?q=` (searching across handles, PGP fingerprints, and wallet addresses) and `GET /api/v1/entities/persona/{id}` (full actor dossier, identifiers, links, and timeline).
- `backend/api/artifacts.py`: Provenance endpoint `GET /api/v1/artifacts/{id}` returning exact verbatim raw stored text and SHA-256 content hashes.
- `backend/api/export.py`: REST endpoint `GET /api/v1/export?format=csv|json` delivering intelligence graph exports with embedded provenance.
- `backend/main.py`: Mounted all new API routers under `/api/v1`.
- `tests/test_phase4.py`: Comprehensive test suite verifying all 8 Phase 4 acceptance criteria.

## Tested — how, not just whether
- Ran `./venv/bin/pytest -v tests/test_phase4.py`:
  - `test_get_graph_endpoint`: PASSED (Returned 6 nodes, 3 active edges with scores, verified required fields).
  - `test_get_edge_evidence`: PASSED (Retrieved complete evidence rows, verified supporting/contradicting directions, weights, notes, and artifact provenance).
  - `test_patch_edge_status_and_rejection_filter`: PASSED (Setting an edge to `rejected` immediately removed it from `/api/v1/graph`, while setting an edge to `confirmed` preserved it with confirmed status).
  - `test_entities_search`: PASSED (Successfully queried by handle substring `night`, PGP hex fingerprint `9F2A4C81...`, and wallet address `1Kp7dR3z...`).
  - `test_entities_persona_dossier`: PASSED (Retrieved full dossier for `nightjar` including identifiers, correlated links, activity timeline, and source info).
  - `test_artifact_provenance_endpoint`: PASSED (Retrieved verbatim raw HTML content and SHA-256 hash from `/api/v1/artifacts/{id}`).
  - `test_export_json_and_csv`: PASSED (Verified both JSON and CSV exports contain `artifact_id` on every evidence row).
  - `test_graph_service_stateless`: PASSED (Verified separate graph instances are created per request with no global state retention).
- Ran full regression test suite `./venv/bin/pytest -v tests/`:
  - All 27 tests across Phases 1, 2, 3, and 4 passed cleanly (2.62s).

## Stubbed / faked / incomplete
- None.

## Deviations from the docs
- None.

## Blocked
- None.

## Acceptance criteria
- [x] `GET /graph` returns nodes + edges + scores
- [x] `GET /graph/edge/{id}` returns every evidence row with weight, direction, `artifact_id`
- [x] `PATCH /graph/edge/{id}` sets confirmed/rejected; rejected disappears from `/graph`
- [x] `GET /entities/search?q=` finds by handle, PGP fingerprint and wallet
- [x] `GET /entities/persona/{id}` returns identifiers, links, timeline, sources
- [x] **`GET /artifacts/{id}` returns the raw stored artifact** — the provenance endpoint
- [x] CSV and JSON export both include `artifact_id` on every evidence row
- [x] Graph service holds no state between requests

## Ready for next phase: YES
