# IMPLEMENTATION_PLAN.md

**Repo:** `GOTHAMITE`
**Prerequisites:** `MASTER_CONTEXT.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`, `INVESTIGATION_PIPELINE.md`
**Deadline:** 8 September 2026

---

## 1. The rule

Six phases. **At the end of each, stop, write a report, wait.**

Not because the phase felt finished — because a human replied with an explicit instruction to proceed. Silence is not permission. Encouragement is not permission.

**Why:** an agent given a large scope builds broad and shallow. By the time that is visible it is too late to unwind. Each gate forces one narrow thing to actually work before the next starts.

---

## 2. Time budget

Roughly three days. **This is the graded deliverable** — if time runs short, it comes out of `darkweb-sandbox`, never out of here.

| Phase | Target | Note |
|---|---|---|
| 1 | Fri night | Models + DB. Fast, unblocks everything |
| 2 | Sat AM | Ingest API |
| 3 | Sat PM | **Correlation engine. The core. Budget the most time here** |
| 4 | Sat PM | Graph + export API |
| 5 | Sun AM | Dashboard |
| 6 | Sun PM | Integration + demo hardening |

Phase 3 is the project. Everything before it is plumbing; everything after is presentation. If a phase overruns, it should be 3, and that is acceptable — the others are not allowed to.

**`scripts/seed_demo.py` lands in Phase 1, not Phase 6.** It loads seed personas straight into the DB with no scraper and no sandbox. It unblocks Phases 3–5 from depending on the other repo, and it is your fallback if the relay chain fails on stage.

---

## 3. Phases

### Phase 1 — Data layer + seed loader

**Build**
- `backend/db.py` — SQLAlchemy engine, session, SQLite init
- `backend/models/entities.py` — every table from `DATA_MODEL.md` §2, one file
- `scripts/seed_demo.py` — loads `DATA_MODEL.md` §4 personas and identifiers directly

**Acceptance**
1. All seven tables create cleanly
2. Constraints hold: persona unique on (`handle`, `source_id`); identifiers require `persona_id` **and** `artifact_id`
3. `seed_demo.py` loads all six personas with exact values from `DATA_MODEL.md` §4
4. PGP fingerprints stored uppercase, 40 hex chars, no whitespace
5. Re-running `seed_demo.py` is idempotent — no duplicates
6. Query confirms A1/A2 share PGP and wallet; B1/B2 share wallet only; C1 shares nothing

Criterion 6 is the one to actually run. If the seed data is wrong, every later phase produces wrong results and it will look like the correlation engine is broken.

**Do not build:** API, correlation, frontend.

---

### Phase 2 — Ingest API

**Build**
- `backend/main.py` — FastAPI app
- `backend/api/ingest.py`, `backend/services/ingest_service.py`

Per `INVESTIGATION_PIPELINE.md` §2 and `API_CONTRACT.md`.

**Acceptance**
1. Valid payload → `202`, artifact + persona + identifiers persisted
2. `raw_content` stored **verbatim** — byte-identical to what was sent
3. Hash recomputed and mismatch rejected with `400`
4. Duplicate (`source_id`, `content_hash`) → `200 duplicate`, no second artifact
5. Malformed payload → `400` naming the field, nothing persisted
6. Repeat persona ingest widens `first_seen`/`last_seen`, does not duplicate the persona
7. Same identifier from two artifacts → **two rows**, both retained
8. **No relationship is created by any ingest call**
9. Validation constraints from `SECURITY.md` §2 enforced at the boundary

Criterion 8 is structural. If ingest scores anything, the pipeline is wrong — see `ARCHITECTURE.md` §1.

**Do not build:** correlation, graph, frontend.

---

### Phase 3 — Correlation engine

**The core of the project. Most of your time goes here.**

**Build**
- `backend/services/correlation_service.py`
- `backend/api/correlate.py` — `POST /api/v1/correlate`

Per `INVESTIGATION_PIPELINE.md` §3 and `DATA_MODEL.md` §3.

**Acceptance — run against seeded data, verify every row**

| Pair | Expected |
|---|---|
| `nightjar` ↔ `n1ghtjar_` | **0.95**, evidence: PGP +0.70, wallet +0.45 |
| `quillfeather` → `quill_v2` | **0.60**, evidence: wallet +0.45, succession +0.15 |
| `nightjar` ↔ `nightjarr` | **no relationship** — 0.05 handle, −0.30 overlap, below threshold |
| `bellwether` → `n1ghtjar_` | `transacted_with` only, **not** `same_actor_suspected` |

Plus:
5. Every relationship has one evidence row per signal, each naming an `artifact_id`
6. Contradicting evidence stored with negative weight, **not** discarded
7. Score reconstructs exactly by summing its evidence weights
8. **Idempotent** — running three times produces identical relationships and scores
9. No score exceeds 0.95
10. A `rejected` relationship is not recreated on re-run
11. Same-source persona pairs are never compared

Row three is the most important test in this document. Every naive matcher links `nightjar` and `nightjarr`. If yours does, the scoring is wrong.

**Do not build:** frontend, export.

---

### Phase 4 — Graph, entities, export API

**Build**
- `backend/services/graph_service.py` — NetworkX, built from DB per request, stateless
- `backend/services/export_service.py`
- `backend/api/graph.py`, `entities.py`, `artifacts.py`, `export.py`

**Acceptance**
1. `GET /graph` returns nodes + edges + scores
2. `GET /graph/edge/{id}` returns every evidence row with weight, direction, `artifact_id`
3. `PATCH /graph/edge/{id}` sets confirmed/rejected; rejected disappears from `/graph`
4. `GET /entities/search?q=` finds by handle, PGP fingerprint and wallet
5. `GET /entities/persona/{id}` returns identifiers, links, timeline, sources
6. **`GET /artifacts/{id}` returns the raw stored artifact** — the provenance endpoint
7. CSV and JSON export both include `artifact_id` on every evidence row
8. Graph service holds no state between requests

Criterion 6 makes "click the evidence, see the actual page" work. That click is the demo's credibility moment.

---

### Phase 5 — Dashboard

**Build**
- `frontend/app.py` — overview, counts, "Run correlation" button
- `frontend/pages/1_graph.py`, `2_dossier.py`, `3_timeline.py`

Graph rendering: try `streamlit-agraph` first, fall back to `pyvis`. **Report which you used and why.**

**Acceptance**
1. Graph renders, nodes coloured by source, edge thickness by score
2. Clicking an edge shows all evidence — supporting **and** contradicting — with weights
3. Evidence links through to the raw artifact and it displays
4. Confirm/reject works; graph updates immediately
5. Search returns results for handle, PGP and wallet
6. Dossier shows identifiers, links, timeline, sources
7. Timeline makes the `quillfeather` → `quill_v2` handoff visually obvious
8. **Scores render as `0.95` with a band label — never as a percentage**
9. **No ingested string rendered with `unsafe_allow_html=True`**
10. No unexplained number anywhere — every score clicks through to its signals

---

### Phase 6 — Integration + demo hardening

**Build nothing new.** Make what exists reliable.

**Acceptance**
1. `docker compose up` brings up backend + frontend cleanly
2. Full path works: sandbox scraper → ingest → correlate → visible in dashboard
3. **Fallback path works: `seed_demo.py` → correlate → dashboard, with the sandbox entirely absent**
4. Cold start to visible graph in under two minutes
5. Run three times consecutively without failure
6. `DEMO_SCRIPT.md` walked end to end twice
7. **Recording of the full working flow exists**

Criterion 3 is your insurance. If the relay chain fails on stage, you still demo the part that is graded.

---

## 4. Phase report format

`docs/reports/PHASE_<n>_REPORT.md`:

```markdown
# Phase <n> Report

## Built
- <files created/modified, one line each>

## Tested — how, not just whether
- <what was run, what output was observed>

## Stubbed / faked / incomplete
- <"None" is valid only if true>

## Deviations from the docs
- <what differs from spec, and why>

## Blocked
- <on what, on whom>

## Acceptance criteria
- [ ] <each criterion, checked or not>

## Ready for next phase: YES / NO
```

- "Implemented" means it ran and you observed the output
- Never mark a criterion passed from reading code
- Any unmet criterion → `Ready: NO`. Do not round up

---

## 5. Stop conditions

Stop mid-phase and ask if:

- Two docs conflict, or a spec is ambiguous
- Acceptance criteria look unachievable as written
- You need a dependency not named in `MASTER_CONTEXT.md` §5
- Something on the OUT OF SCOPE list seems necessary
- Correlation output does not match the Phase 3 table
- A task appears to require breaking a rule in `SECURITY.md` §7

Never resolve any of these by picking an interpretation and continuing. A wrong assumption in Phase 1 surfaces in Phase 6, and there is no time to unwind it.
