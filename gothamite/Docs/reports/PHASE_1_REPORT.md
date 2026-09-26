# Phase 1 Report

## Built
- `requirements.txt`: Specified Python dependencies for backend, database, graph, UI, and test suites.
- `.gitignore`: Configured exclusions for virtual environments, caches, SQLite databases, and environment variables.
- `backend/db.py`: SQLAlchemy engine, session factory (`SessionLocal`), SQLite foreign-keys pragma listener, and `init_db()` initialization helper.
- `backend/models/entities.py`: All seven database models (`Source`, `Artifact`, `Persona`, `Identifier`, `Relationship`, `Evidence`, `Actor`) conforming to `DATA_MODEL.md` §2.
- `backend/models/__init__.py`: Package init exporting all entity models.
- `scripts/seed_demo.py`: Standalone offline database seeder loading all 6 benchmark personas, artifacts, and identifiers per `DATA_MODEL.md` §4 with built-in invariant verification.
- `tests/test_phase1.py`: Pytest test suite validating table creation, unique and foreign key constraints, PGP normalization, and idempotent seed loading.

## Tested — how, not just whether
- Ran `./venv/bin/python scripts/seed_demo.py`:
  - Successfully created all 7 tables in `gothamite.db`.
  - Seeded 3 sources (`forum-alpha`, `marketplace-beta`, `forum-gamma`).
  - Seeded 6 benchmark personas, 6 raw artifacts with sha256 hashes, and 13 identifiers.
  - Verified all Phase 1 acceptance checks passed.
- Ran `./venv/bin/python scripts/seed_demo.py` a second consecutive time:
  - Confirmed idempotency: output confirmed `0 new personas, 0 new artifacts, 0 new identifiers`.
- Ran direct SQLite inspection via Python:
  - Confirmed 7 tables: `sources`, `actors`, `artifacts`, `personas`, `identifiers`, `relationships`, `evidence`.
  - Confirmed zero relationships and zero evidence created at this stage.
  - Confirmed exact persona handles and identifier linkages.
- Ran `./venv/bin/pytest -v tests/test_phase1.py`:
  - `test_tables_created_cleanly`: PASSED
  - `test_persona_unique_constraint`: PASSED (IntegrityError raised on duplicate handle per source)
  - `test_identifier_foreign_keys`: PASSED (IntegrityError raised when persona_id or artifact_id is missing)
  - `test_seed_demo_idempotence_and_vectors`: PASSED
  - `test_pgp_normalization_helper`: PASSED
  - Result: 5 passed in 0.35s.

## Stubbed / faked / incomplete
- None.

## Deviations from the docs
- None.

## Blocked
- None.

## Acceptance criteria
- [x] All seven tables create cleanly
- [x] Constraints hold: persona unique on (`handle`, `source_id`); identifiers require `persona_id` and `artifact_id`
- [x] `seed_demo.py` loads all six personas with exact values from `DATA_MODEL.md` §4
- [x] PGP fingerprints stored uppercase, 40 hex chars, no whitespace
- [x] Re-running `seed_demo.py` is idempotent — no duplicates
- [x] Query confirms A1/A2 share PGP and wallet; B1/B2 share wallet only; C1 shares nothing

## Ready for next phase: YES
