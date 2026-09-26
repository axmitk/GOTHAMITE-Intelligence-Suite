# ARCHITECTURE.md

**Repo:** `GOTHAMITE`
**Prerequisites:** `MASTER_CONTEXT.md`, `DATA_MODEL.md`

---

## 1. Shape

Four layers, one direction of flow. No component reaches backwards.

```
                    darkweb-sandbox/scraper
                              │  POST /api/v1/ingest
┌─────────────────────────────▼──────────────────────────────┐
│  INGEST                                                     │
│  validate → hash-check → store artifact → store persona     │
│  → store identifiers                                        │
│  Creates NO relationships. Ever.                            │
└─────────────────────────────┬──────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────┐
│  STORE  (SQLite)                                            │
│  artifacts · personas · identifiers · relationships ·       │
│  evidence · actors · sources                                │
│  Append-only for observations. Nothing overwritten.         │
└─────────────────────────────┬──────────────────────────────┘
                              ▼  triggered separately
┌────────────────────────────────────────────────────────────┐
│  CORRELATION PASS                                           │
│  read all personas + identifiers                            │
│  → apply exact-match signals (DATA_MODEL §3)                │
│  → emit relationships + evidence rows                       │
│  Idempotent. Re-runnable. Deterministic.                    │
└─────────────────────────────┬──────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────┐
│  PRESENT                                                    │
│  FastAPI: /graph /entities /export                          │
│  Streamlit: graph · search · dossier · evidence · timeline  │
└────────────────────────────────────────────────────────────┘
```

**Why ingest and correlation are separate** — this is the single most important structural decision in the repo. If ingest created links inline, scores would depend on the order pages happened to arrive, and re-running would produce different output. Separating them makes correlation a pure function of stored state: deterministic, reproducible, and re-runnable after an analyst rejects a link. The audit trail is only meaningful because of this split.

---

## 2. Layout

```
GOTHAMITE/
├── docker-compose.yml
├── .env.example
│
├── docs/                          ← human-owned, agents read-only
│   ├── MASTER_CONTEXT.md
│   ├── PROBLEM_STATEMENT.md
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── AI_DESIGN.md
│   ├── INVESTIGATION_PIPELINE.md
│   ├── SECURITY.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── MASTER_PROMPT.md
│   ├── AGENT_TASK_SPLIT.md
│   └── reports/
│
├── research/
│   └── ROBIN_ANALYSIS.md
│
├── backend/
│   ├── main.py                    ← FastAPI app, router mounting
│   ├── db.py                      ← engine, session, init
│   ├── models/
│   │   └── entities.py            ← ALL SQLAlchemy models, one file
│   ├── services/
│   │   ├── ingest_service.py      ← validate, hash, persist
│   │   ├── correlation_service.py ← the scoring pass
│   │   ├── graph_service.py       ← NetworkX build + queries
│   │   └── export_service.py      ← CSV / JSON
│   └── api/
│       ├── ingest.py
│       ├── graph.py
│       ├── entities.py
│       └── export.py
│
├── frontend/
│   ├── app.py                     ← Streamlit entry, overview
│   └── pages/
│       ├── 1_graph.py
│       ├── 2_dossier.py
│       └── 3_timeline.py
│
└── scripts/
    ├── seed_demo.py               ← load DATA_MODEL §4 directly, no scraper
    └── run_correlation.py         ← trigger the pass from CLI
```

**One file per concern, not one folder per concern.** All models live in `entities.py`. Extraction helpers live inside the service that uses them. This is a three-day build for two people — module boundaries cost more than they return at this size.

---

## 3. Modules

### `models/entities.py`
Every table from `DATA_MODEL.md` §2, as SQLAlchemy models. Nothing else — no business logic, no queries.

### `services/ingest_service.py`
1. Validate payload against `API_CONTRACT.md`
2. Recompute sha256 of `raw_content`, reject on mismatch
3. Duplicate check on (`source_id`, `content_hash`) → `200 duplicate`
4. Persist artifact **first**, then persona (upsert on handle+source), then identifiers
5. Return `202` with counts

Creates no relationships. Runs no scoring.

### `services/correlation_service.py`
The core. Full pass over stored data:

```
load personas + identifiers
for each unordered pair (P, Q) where P.source_id != Q.source_id:
    signals = []
    if shared pgp_fingerprint          → supporting, 0.70
    if shared wallet                    → supporting, 0.45
    if temporal succession (gap < 45d)  → supporting, 0.15
    if levenshtein(handles) <= 2        → supporting, 0.05
    if activity windows overlap         → contradicting, -0.30

    score = clamp(sum(weights), 0.0, 0.95)
    if score >= 0.30:
        upsert relationship + one evidence row per signal
```

Rules:
- **Idempotent.** Re-running produces identical relationships and scores
- Relationships with `status = rejected` are preserved and never recreated
- Every signal emits an evidence row naming the artifact that proves it
- `transacted_with` edges are separate: wallet-to-wallet references between personas. **Never** upgraded to `same_actor_suspected`
- Only cross-source pairs are compared. Two handles on the same site are not the same-actor question this system answers

Same-source pairs and the exact weights are defined in `DATA_MODEL.md` §3 — that file is authoritative, this is the algorithm around it.

### `services/graph_service.py`
Builds a NetworkX graph from DB rows on demand. Nodes are personas, edges are relationships. Serves node/edge/evidence queries and dossier assembly. **Holds no state** — rebuilt per request.

### `services/export_service.py`
CSV and JSON of the current graph plus evidence. Exports must include source artifact ids — an export without provenance defeats the point.

---

## 4. API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/ingest` | Receives scraper payloads |
| `POST` | `/api/v1/correlate` | Triggers the correlation pass |
| `GET` | `/api/v1/graph` | Nodes + edges + scores |
| `GET` | `/api/v1/graph/edge/{id}` | Edge with full evidence |
| `PATCH` | `/api/v1/graph/edge/{id}` | Analyst confirm / reject → recompute |
| `GET` | `/api/v1/entities/search?q=` | Search handle, PGP, wallet |
| `GET` | `/api/v1/entities/persona/{id}` | Dossier: identifiers, links, timeline, sources |
| `GET` | `/api/v1/artifacts/{id}` | Raw stored artifact — the provenance endpoint |
| `GET` | `/api/v1/export?format=csv\|json` | Export |

`/api/v1/artifacts/{id}` matters more than it looks: it is what makes "click the evidence, see the actual page it came from" work, and that click is the demo's credibility moment.

---

## 5. Frontend

Streamlit, four screens.

**`app.py` — Overview.** Counts: artifacts, personas, identifiers, relationships. Source health. A "Run correlation" button. Recent high-score links.

**`1_graph.py` — Graph.** Force-directed. Node = persona, coloured by source. Edge thickness = score. Click an edge → evidence panel showing every signal, weight, direction, and a link to the artifact. Confirm / reject buttons.

**`2_dossier.py` — Actor dossier.** Per persona: handles, identifiers, linked personas with scores, activity timeline, source list, evidence summary.

**`3_timeline.py` — Timeline.** Observations across time, filterable by persona. This is where the `quillfeather` → `quill_v2` rebrand becomes visually obvious — one line stops, another starts.

### UI rules
- **Always render contradicting evidence alongside supporting.** Never hide the negative signals
- Show scores as `0.95`, with a band label. Never as `95%`
- Every score displays its contributing signals on click. No unexplained number anywhere
- Sanitise all ingested strings before rendering — they came from scraped pages

---

## 6. Reference note — Robin

Robin (open-source dark web OSINT tool) was reviewed for structure. Its separation of search / scrape / analysis informed the ingest / correlation / present split here.

It is **not a dependency**. No code from it is used. Its actual workflow — query real dark web search engines over Tor, summarise with an LLM — is a different capability from persistent cross-source correlation. See `research/ROBIN_ANALYSIS.md`.

---

## 7. What is deliberately absent

No message queue, no Celery, no Redis, no scheduler, no vector store, no graph database, no LLM provider, no auth layer, no microservices. Each was considered and cut in `MASTER_CONTEXT.md` §3.

Do not add any of them. If one seems necessary, stop and say so.
