# INVESTIGATION_PIPELINE.md

**Repo:** `GOTHAMITE`
**Prerequisites:** `MASTER_CONTEXT.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`

The end-to-end path a single scraped page takes, from arrival to appearing as scored evidence in front of an analyst. This is the operational spec; `ARCHITECTURE.md` is the structural one.

---

## 1. Stages

```
1  ARRIVE      scraper POSTs one artifact
2  VALIDATE    schema + hash integrity
3  DEDUPE      seen this exact content from this source before?
4  PERSIST     artifact → persona → identifiers
        ─── ingest ends here. no scoring. ───
5  CORRELATE   separate pass over all stored data
6  SCORE       weighted signals, supporting and contradicting
7  EVIDENCE    one row per signal, each naming its artifact
8  PRESENT     graph, dossier, timeline, evidence panel
9  REVIEW      analyst confirms or rejects → recompute
10 EXPORT      CSV / JSON with provenance
```

Stages 1–4 run per artifact, on arrival. Stages 5–7 run as a batch pass, triggered manually. **That boundary is deliberate** — see `ARCHITECTURE.md` §1.

---

## 2. Stages 1–4: ingest

### 1 — Arrive
`POST /api/v1/ingest`, one artifact per request, per `API_CONTRACT.md`.

### 2 — Validate
- Schema conformance. Missing or malformed required field → `400` naming the field
- Recompute `sha256(raw_content.encode('utf-8'))`, compare to `content_hash`. Mismatch → `400`
- `source_id` must be one of the three known sources
- `collected_at` and `observed_at` must both parse as ISO 8601 UTC

**Treat every field as hostile.** It originated from a scraped page. Validate before it touches the database.

### 3 — Dedupe
Look up (`source_id`, `content_hash`).

Found → `200 {"accepted": false, "reason": "duplicate_content_hash"}`. Not an error. Re-scraping the same unchanged page is expected behaviour.

Not found → continue.

### 4 — Persist
**Order matters. Artifact first.**

1. **Artifact** — `raw_content` stored verbatim: not cleaned, not stripped, not truncated. Plus hash, url, source, `collected_at`, `relay_path`. This row is the evidence locker; everything downstream points at it
2. **Persona** — upsert on (`handle`, `source_id`). New → create with `first_seen = last_seen = observed_at`. Existing → widen the window: `first_seen = min(...)`, `last_seen = max(...)`, increment `post_count`
3. **Identifiers** — one row per identifier, each carrying `persona_id` **and** `artifact_id`. The artifact link is what makes the evidence traceable later. An identifier without it is unusable

Normalisation is the scraper's job and is re-verified here: PGP uppercase, whitespace stripped, 40 hex chars. Wallets and handles verbatim.

Duplicate identifier for the same persona from a *different* artifact → **store both**. Two artifacts independently showing the same key is stronger evidence than one, and observation history is never collapsed.

Return `202` with counts.

**No relationship is created at any point in stages 1–4.**

---

## 3. Stages 5–7: correlation

Triggered by `POST /api/v1/correlate` or the dashboard button. Full pass, not incremental.

### 5 — Correlate
```
personas    = all personas
identifiers = all identifiers, grouped by persona

for each unordered pair (P, Q) where P.source_id != Q.source_id:
    evaluate signals
```

**Cross-source pairs only.** Two handles on the same forum are a different question and out of scope.

### 6 — Score
Signals and weights are defined in `DATA_MODEL.md` §3 and that file is authoritative. Applied as:

| Signal | Weight | Direction | Condition |
|---|---|---|---|
| Shared PGP fingerprint | +0.70 | supporting | identical normalised value |
| Shared wallet | +0.45 | supporting | identical value |
| Temporal succession | +0.15 | supporting | `P.last_seen < Q.first_seen`, gap < 45 days |
| Handle similarity | +0.05 | supporting | Levenshtein ≤ 2 |
| Activity overlap conflict | **−0.30** | contradicting | active windows overlap |

```
score = clamp(sum(weights), 0.0, 0.95)
create relationship if score >= 0.30
```

Three rules that are easy to get wrong:

- **The contradicting signal is not a filter — it is a term in the sum.** It reduces the score and is displayed. It never silently suppresses a link
- **Cap at 0.95.** Never emit 1.0
- **Idempotent.** Re-running must produce identical scores. No randomness, no timestamps in the calculation, no dependence on row order

Relationships with `status = rejected` are skipped and never recreated. Analyst decisions survive re-runs.

### `transacted_with` — separate track
Where persona P's post references a wallet belonging to persona Q, emit a `transacted_with` edge. No score, no identity claim.

**This edge is never promoted to `same_actor_suspected`.** Two people transacting are two people. Conflating interaction with identity is the classic attribution error and the seed data contains a case (`bellwether` → `n1ghtjar_`) specifically to demonstrate the system not making it.

### 7 — Evidence
One evidence row **per signal**, supporting and contradicting alike, each with: `signal_type`, `direction`, `weight`, `artifact_id`, and a human-readable note.

A relationship with no evidence rows is a bug. A score that cannot be reconstructed by summing its evidence weights is a bug.

---

## 4. Expected output on seed data

After ingest + correlation over `DATA_MODEL.md` §4, exactly this:

| Pair | Signals | Score | Result |
|---|---|---|---|
| `nightjar` ↔ `n1ghtjar_` | PGP +0.70, wallet +0.45 | **0.95** (capped) | very strong |
| `quillfeather` → `quill_v2` | wallet +0.45, succession +0.15 | **0.60** | strong |
| `nightjar` ↔ `nightjarr` | handle +0.05, overlap −0.30 | **0.00** | **no edge** |
| `bellwether` → `n1ghtjar_` | wallet reference | n/a | `transacted_with` only |

**This table is the acceptance test for the whole pipeline.** If any row differs, something upstream is wrong — usually seed data that does not match `DATA_MODEL.md` character for character.

The third row is the important one. Every naive matcher links `nightjar` and `nightjarr`. This one does not, because a one-character handle similarity is worth almost nothing and the activity windows actively conflict.

---

## 5. Stages 8–10: analyst

### 8 — Present
- **Graph** — personas as nodes, coloured by source; relationships as edges, thickness by score
- **Edge click** — every signal, its weight, its direction, and a link through to the raw artifact
- **Dossier** — one persona: identifiers, linked personas, timeline, sources
- **Timeline** — observations over time. Where the `quillfeather` → `quill_v2` handoff becomes visible as one line ending and another starting
- **Search** — handle, PGP fingerprint, wallet

Every displayed number is clickable to its evidence. No unexplained scores anywhere in the UI.

### 9 — Review
Analyst sets an edge to `confirmed` or `rejected`.

- Rejected → edge hidden from the graph, row retained with `status = rejected`, never recreated by later passes
- Confirmed → may be grouped into an `Actor` with an analyst-assigned label
- Either way the graph recomputes immediately

Analyst judgement outranks the score. The system proposes; the human decides.

### 10 — Export
CSV and JSON of the current graph plus evidence. **Must include `artifact_id` on every evidence row** — an export without provenance is just a list of assertions, which is the thing this system exists not to produce.

---

## 6. Failure behaviour

| Failure | Behaviour |
|---|---|
| Malformed payload | `400` naming the field. Nothing persisted |
| Hash mismatch | `400`. Nothing persisted. Log loudly — this means content changed in transit |
| Duplicate content | `200 duplicate`. Normal |
| Identifier fails normalisation | Store the artifact and persona, skip that identifier, log it. Never drop the artifact |
| Correlation finds nothing | Valid outcome. Empty graph, no error |
| Artifact referenced by evidence is missing | **Bug.** Fail loudly, do not render the relationship |

Partial ingest is always better than a rejected batch. One malformed page must never prevent the other forty from landing.
