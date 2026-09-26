# AGENT_TASK_SPLIT.md

**Repo:** `GOTHAMITE`
**Owner:** Tanish
**Purpose:** who builds what in this repo, and what neither agent may touch.

Complex engineering goes to **Claude Code**. Presentation layer goes to **Antigravity / Codex**.

The split is by **directory ownership** and it is absolute. An agent editing a file it does not own creates a merge conflict resolved by hand, at night, near a deadline.

---

## 1. Ownership

| Path | Owner |
|---|---|
| `backend/db.py` | **Claude Code** |
| `backend/models/` | **Claude Code** |
| `backend/services/` | **Claude Code** |
| `backend/api/` | **Claude Code** |
| `backend/main.py` | **Claude Code** |
| `scripts/` | **Claude Code** |
| `docker-compose.yml` | **Claude Code** |
| `requirements.txt` | **Claude Code** |
| `frontend/` | **Antigravity** |
| `docs/`, `research/` | **Neither** — human-owned, read-only |
| `docs/reports/` | Both — own reports only |

### Why this split

Claude Code takes the data model, ingest, and the correlation engine. The scoring pass is where subtle mistakes are invisible until they surface as a wrong graph on stage — idempotency, the contradicting-signal arithmetic, the 0.95 cap, never promoting `transacted_with` to an identity link. These are "looks right but isn't" failures.

Antigravity takes the Streamlit dashboard: four screens over a settled API. Real work, high visual payoff, low algorithmic risk.

---

## 2. What each agent must never touch

### Claude Code — do not touch
- `frontend/` — not to fix a rendering bug, not to add a widget. If a page is broken, **report it, do not edit it**
- Antigravity's phase reports

### Antigravity — do not touch
- `backend/` — ever, for any reason
- `scripts/`, `docker-compose.yml`, `requirements.txt`
- **Any correlation, scoring or evidence logic.** If a score looks wrong, report it. Never "fix" it in the frontend
- Claude Code's phase reports

**If either agent believes it needs the other's files: stop and tell Tanish.**

The most dangerous version of this: Antigravity seeing an unexpected score and adjusting the display to compensate. That hides a real bug behind a cosmetic patch and it will be found on stage. Frontend renders what the API returns. It never corrects it.

---

## 3. Sequencing

```
Claude Code ─► Phase 1 ─► Phase 2 ─► Phase 3 ─► Phase 4 ──┐
               data       ingest     CORRELATION  graph/    │
               + seed                 (the core)  export    │
                                                            ▼
Antigravity ──────────────────────────────────────► Phase 5 ─► [CC] Phase 6
                                                    dashboard    integration
```

**Antigravity is blocked until Phase 4 is complete and confirmed.** The dashboard consumes the graph and evidence endpoints; building against an unfinished API produces code that must be rewritten.

While blocked, Antigravity does nothing in this repo. If it is free earlier, it belongs on `darkweb-sandbox` Phase 4 (mock sites), which has no dependencies at all.

Phase 6 returns to Claude Code.

### If Phase 3 overruns

It is allowed to — it is the core. If it does, Antigravity can start on the **static shell** of the dashboard against `GET /graph` alone (layout, navigation, search box) with a hard rule: **no evidence-panel work until Phase 4 confirms the evidence contract.** Building an evidence panel against a guessed schema wastes the time it was meant to save.

---

## 4. Reporting

Phase-gate rule from `IMPLEMENTATION_PLAN.md` §1: build, report, **stop**, wait.

- Claude Code → `PHASE_1_REPORT.md`, `_2_`, `_3_`, `_4_`, `_6_`
- Antigravity → `PHASE_5_REPORT.md`

No filename collisions.

---

## 5. Handoff at Phase 4 → 5

Verify yourself before Antigravity starts. Do not take the report's word for it.

- [ ] `GET /graph` returns nodes, edges and scores
- [ ] `GET /graph/edge/{id}` returns every evidence row with weight, direction and `artifact_id`
- [ ] `GET /artifacts/{id}` returns raw stored content
- [ ] `GET /entities/search?q=` works for handle, PGP and wallet
- [ ] `PATCH /graph/edge/{id}` rejects an edge and it disappears from `/graph`
- [ ] Export includes `artifact_id` on every evidence row
- [ ] **The Phase 3 expected table holds exactly** — including `nightjar` ↔ `nightjarr` producing no edge

The last one is the acceptance test for the whole system. If it fails, do not start the dashboard. A beautiful UI over wrong correlation is worse than no UI, because it makes the error look authoritative.

Hand Antigravity the actual JSON responses from these endpoints, not a description of them.

---

## 6. Session prompts

Both agents get `MASTER_PROMPT.md` in full, plus one of these appended:

### Claude Code
```
You own: backend/, scripts/, docker-compose.yml, requirements.txt.

You do NOT own and must never edit: frontend/ (another agent builds it), or docs/ and
research/ (human-owned specs, read-only).

Your phases are 1, 2, 3, 4, 6 — in that order. Phase 5 (dashboard) belongs to the other
agent.

Phase 3 is the core of this project. Budget accordingly. The expected-output table in
IMPLEMENTATION_PLAN.md Phase 3 is the acceptance test; every row must match exactly,
including nightjar <-> nightjarr producing NO edge.

scripts/seed_demo.py is a Phase 1 deliverable, not a Phase 6 one. It must load the seed
data with no scraper and no other repo present.

If the dashboard appears broken, report it. Do not fix it.
```

### Antigravity / Codex
```
You own: frontend/ only. Nothing else.

You do NOT own and must never edit: backend/, scripts/, docker-compose.yml,
requirements.txt, or docs/ and research/ (human-owned specs, read-only). Another agent
owns all backend logic.

Your only phase is Phase 5. Do not start until told Phase 4 is confirmed complete. When
Phase 5 is done, write the report and stop.

Build against the live API. Never reimplement scoring, correlation or evidence logic in
the frontend. If a score or an edge looks wrong, REPORT IT — never adjust the display to
compensate. The frontend renders what the API returns and never corrects it.

Hard UI rules from SECURITY.md:
  - Scores render as "0.95" with a band label, NEVER as a percentage
  - Contradicting evidence is always displayed alongside supporting evidence
  - Every score clicks through to its contributing signals — no unexplained numbers
  - NEVER render an ingested string with unsafe_allow_html=True. All ingested content
    is escaped before display, including raw artifact viewing
  - Never use "identified", "deanonymised", "confirmed identity", "proof", or a
    percentage probability in any UI string

Graph rendering: try streamlit-agraph first, fall back to pyvis. Report which and why.
```

---

## 7. Notes for Tanish

**Separate sessions**, not one agent with two roles. The boundary is enforced by the prompt and a single session will drift across it.

**Review before proceeding, every time.** Run one query or hit one endpoint per report. An unread gate is not a gate.

**If an agent crosses its boundary:**
> Stop. You have edited files outside your ownership per AGENT_TASK_SPLIT.md section 1. List every file you touched outside your scope, revert them, and rewrite your phase report.

**Watch for the display-patch failure specifically.** If Antigravity's Phase 5 report mentions adjusting, formatting, correcting or working around any score or edge, treat it as a backend bug that has been hidden rather than a frontend feature that has been delivered.
