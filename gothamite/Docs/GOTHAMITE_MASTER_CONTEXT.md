# MASTER_CONTEXT.md

**Repo:** `GOTHAMITE`
**Team:** AvivCREW
**Problem Statement:** SIH26151 — Dark Web Threat Actor De-anonymization (NTRO)
**Hard deadline:** 8 September 2026
**Read this file first. Every other doc in `docs/` assumes you have read it.**

---

## 1. What this is

An analyst platform that ingests observations from dark web sources, extracts identifiers, correlates personas across sites into a confidence-scored relationship graph, and shows an analyst *why* every link exists — traceable back to the source artifact it came from.

**This is the graded SIH deliverable.** The `darkweb-sandbox` repo exists to feed it. If time runs short, time comes out of the sandbox, not out of this.

### One sentence
Given handles scattered across separate marketplaces and forums, GOTHAMITE determines which of them are probably the same actor, scores how confident that is, and shows the evidence behind it — including the evidence against it.

---

## 2. Relationship to `darkweb-sandbox`

Two repos, one pipeline, one seam.

```
darkweb-sandbox                          GOTHAMITE (this repo)
────────────────                         ──────────────────────
mock sites → relays → scraper  ──POST──► ingest API
                                              ↓
                                         artifact store (raw, hashed)
                                              ↓
                                         personas + identifiers
                                              ↓
                                         correlation pass
                                              ↓
                                         relationships + evidence + score
                                              ↓
                                         dashboard: graph / dossier / evidence
                                              ↓
                                         CSV / JSON export
```

`darkweb-sandbox/Agent_Docs/API_CONTRACT.md` defines the seam. **`docs/DATA_MODEL.md` in this repo is authoritative** — if the contract and the data model disagree, the data model wins.

Neither repo imports code from the other.

---

## 3. Scope lock

Deliberate cuts, made with the deadline in view. **Do not restore anything from the OUT list, and do not scaffold placeholders for it.**

### IN SCOPE

| Component | Scope |
|---|---|
| **Ingest API** | `POST /api/v1/ingest` per `API_CONTRACT.md`. Stores raw artifact, persona, identifiers |
| **Artifact store** | Verbatim content + sha256, never overwritten |
| **Correlation pass** | Separate pass over stored data. Exact-match signals only, per `DATA_MODEL.md` §3 |
| **Evidence + scoring** | Every relationship carries its supporting **and contradicting** signals with weights |
| **Graph API** | Nodes, edges, scores, evidence |
| **Dashboard** | Graph view, search, actor dossier, evidence panel, timeline |
| **Analyst review** | Confirm / reject a link; graph recomputes |
| **Export** | CSV and JSON |

### OUT OF SCOPE

| Excluded | Why |
|---|---|
| **Stylometry / writing-style AI** | Cut. Needs a real corpus and real evaluation. Claiming it without both is the exact "unfounded ML claim" that loses marks |
| **Descriptor-inconsistency detection** | Cut. The project design document itself states the method must be validated against Tor documentation before being claimed. That validation has not happened |
| **Certificate Transparency / infrastructure attribution** | **STRETCH ONLY.** Build nothing until Phases 1–5 are complete and confirmed. See §6 |
| **Any LLM in attribution** | Correlation is deterministic and reproducible. That is what makes the audit trail meaningful |
| **Behavioural profiling / ML clustering** | Same reason as stylometry |
| **Fuzzy identifier matching** | Exact match only. A fuzzy PGP match is not a thing |
| **Autonomous scheduler / continuous collection** | Scrapes are manually triggered for the demo. Describe continuous collection as designed-for, not built |
| **Auth / RBAC / multi-user** | Single-analyst demo. No login |
| **Live collection from real sources** | **Hard rule.** Nothing in this repo ever connects to real dark web infrastructure |

---

## 4. Real vs. simulated — be precise

| Claim | Status |
|---|---|
| Correlation engine and scoring | **REAL.** Deterministic, reproducible, documented weights |
| Evidence provenance to source artifact | **REAL.** Every claim traces to a stored artifact and its hash |
| Contradiction detection | **REAL.** Conflicting signals reduce score and are shown |
| Analyst review recomputation | **REAL** |
| Source data | **SYNTHETIC.** Invented personas on mock sites. No real scraped data, ever |
| Continuous autonomous collection | **NOT BUILT.** Architecturally designed for; manually triggered in the demo |
| Infrastructure attribution | **NOT BUILT** unless the stretch is reached |
| Real-world identity attribution | **NEVER CLAIMED.** The system links pseudonyms to pseudonyms. It does not identify people |

**Language rules** — in code, logs, UI text, docs, and on stage:

- Say *confidence score*. Never *probability* or a percentage likelihood
- Say *suspected same actor*, *likely linked*. Never *identified*, *deanonymised*, *confirmed identity*
- Say *synthetic corpus*, *simulated sources*. Never imply live dark web collection
- A shared wallet is **evidence of a link between personas**, never an identity

If a UI string would embarrass you when a judge reads it closely, rewrite it before an agent ships it into a screenshot.

---

## 5. Stack

Chosen for build speed under a three-day deadline. Do not substitute.

| Layer | Choice | Note |
|---|---|---|
| Backend | Python 3.11 + FastAPI | |
| Database | **SQLite** | Schema stays Postgres-compatible. Zero setup friction matters more than scale here |
| ORM | SQLAlchemy | |
| Graph logic | NetworkX | In-memory, built from DB rows on demand. No graph database |
| Frontend | **Streamlit** | `app.py` + `pages/`. Fastest path to a working analyst UI |
| Graph rendering | `streamlit-agraph` or `pyvis` | Whichever renders reliably first — decide in Phase 5, report which |
| Export | stdlib `csv` / `json` | |
| Packaging | Docker Compose | |

No React, no Postgres, no Neo4j, no Celery, no Redis, no vector store, no LLM provider SDKs. Every one of those was considered and cut for time.

---

## 6. Hard rules

1. **No real dark web data, ever.** Not in code, tests, fixtures, seed data or comments.
2. **All ingested data is untrusted input.** It originates from scraped pages. Sanitise before rendering in the dashboard. Parameterised queries only. Never interpolate into a shell command, a URL, or an LLM prompt.
3. **Ingest never creates relationships.** Ingest stores artifacts, personas, identifiers. Correlation is a separate, re-runnable pass. Keeping them apart is what makes scoring reproducible.
4. **Never score above 0.95.** Certainty is not establishable here.
5. **No relationship without evidence rows.** If it cannot name the artifacts behind it, it does not get created.
6. **Store the raw artifact before parsing.** It persists even if extraction fails.
7. **No breadth-first scaffolding.** No empty files, stub modules or directory trees for things not being built. Files appear when they contain working code.
8. **The stretch stays untouched** until Phases 1–5 are complete and human-confirmed.

---

## 7. Phase gates

Build follows `docs/IMPLEMENTATION_PLAN.md`.

**At the end of every phase you stop**, write the phase report, and wait for explicit human confirmation. Silence is not permission. Encouragement is not permission.

If a spec is ambiguous or two docs conflict: **stop and ask.** Never resolve ambiguity by choosing an interpretation and continuing.

---

## 8. Done means

Live and repeatably:

1. Scraper POSTs artifacts; they persist with raw content and hashes
2. Correlation pass runs over stored data and produces the four expected results from `DATA_MODEL.md` §4:
   - `nightjar` ↔ `n1ghtjar_` — **0.95**, shared PGP + wallet
   - `quillfeather` → `quill_v2` — **0.60**, shared wallet + temporal succession, no PGP match
   - `nightjarr` — **no edge**, despite a one-character handle similarity, because activity windows conflict
   - `bellwether` → `n1ghtjar_` — `transacted_with` only, **not** an identity link
3. Graph renders; clicking an edge shows evidence with weights and source artifacts
4. Clicking through evidence reaches the stored raw artifact
5. Rejecting a link recomputes the graph
6. CSV and JSON export
7. Re-running correlation produces identical scores — deterministic

Item 2's third bullet is the most important thing this system does. **A correct rejection is a stronger result than a match**, and it is the part of the demo judges will remember.
