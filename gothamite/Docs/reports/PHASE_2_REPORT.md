# Phase 2 Report

## Built
- `backend/services/ingest_service.py`: Service logic enforcing hash recomputation (`compute_sha256`), duplicate detection (`source_id`, `content_hash`), verbatim immutable artifact persistence, persona observation window widening, and identifier persistence.
- `backend/api/ingest.py`: REST endpoint `POST /api/v1/ingest` with Pydantic v2 boundary validators (1 MB size ceiling, `.onion.mock` host validation, control-character prevention in handles, 40 hex char PGP checks, base58 wallet checks, and known source enumeration).
- `backend/main.py`: FastAPI application entrypoint with startup database schema initialization, CORS middleware, and custom `RequestValidationError` handler translating schema errors into RFC-compliant 400 Bad Request responses (`{"accepted": false, "errors": [...]}`).
- `tests/test_phase2.py`: Comprehensive test suite verifying all 9 acceptance criteria for the Ingest API.

## Tested — how, not just whether
- Ran `./venv/bin/pytest -v tests/test_phase2.py`:
  - `test_valid_payload_ingest`: PASSED (HTTP 202, verified database persistence of artifact, persona, and identifiers).
  - `test_raw_content_verbatim`: PASSED (HTTP 202, verified stored text is byte-identical including embedded HTML, scripts, and whitespace).
  - `test_hash_mismatch_rejected`: PASSED (HTTP 400, verified rejection when `content_hash` fails sha256 integrity, zero rows persisted).
  - `test_duplicate_content_hash`: PASSED (HTTP 200 with `duplicate_content_hash`, verified no second artifact created).
  - `test_malformed_payload_rejected`: PASSED (HTTP 400 naming missing field `source_id`, zero rows persisted).
  - `test_repeat_persona_widens_window`: PASSED (3 sequential ingests of `quillfeather` in May, January, August widens `first_seen` to Jan and `last_seen` to Aug with `post_count=3` and zero persona duplication).
  - `test_same_identifier_different_artifacts_both_retained`: PASSED (Identical PGP key in two distinct artifacts stores 2 identifier rows, preserving complete provenance).
  - `test_no_relationships_created_at_ingest`: PASSED (Confirmed `Relationship` count and `Evidence` count remain exactly 0 after multiple cross-source ingests).
  - `test_security_boundary_validations`: PASSED (Tested and rejected: unknown `source_id`, non-onion URLs, payloads > 1 MB, handles with control chars, malformed PGP keys, and non-base58 wallet addresses).
- Ran full regression test suite `./venv/bin/pytest -v tests/`:
  - All 14 tests across Phase 1 and Phase 2 passed cleanly (0.90s).

## Stubbed / faked / incomplete
- None.

## Deviations from the docs
- None.

## Blocked
- None.

## Acceptance criteria
- [x] Valid payload → `202`, artifact + persona + identifiers persisted
- [x] `raw_content` stored **verbatim** — byte-identical to what was sent
- [x] Hash recomputed and mismatch rejected with `400`
- [x] Duplicate (`source_id`, `content_hash`) → `200 duplicate`, no second artifact
- [x] Malformed payload → `400` naming the field, nothing persisted
- [x] Repeat persona ingest widens `first_seen`/`last_seen`, does not duplicate the persona
- [x] Same identifier from two artifacts → **two rows**, both retained
- [x] **No relationship is created by any ingest call**
- [x] Validation constraints from `SECURITY.md` §2 enforced at the boundary

## Ready for next phase: YES
