# PROJECT_PROGRESS.md — GOTHAMITE / darkweb-sandbox Handoff

**Purpose:** authoritative navigation/handoff document for continuing development,
primarily for a fresh AI coding agent picking this repository up cold. It indexes
and summarizes; it does not supersede the specification documents it points to.

**Last verified:** 2026-09-08 (Phase 5 completion). Read against the actual
repository state, `AgentsDocs/SPEC_DECISIONS.md`, the reports under
`AgentsDocs/reports/`, and the test suites — nothing below is inferred beyond what
those sources state.

---

## 1. Project identity

- **Project:** GOTHAMITE — a dark-web threat-intelligence platform.
- **SIH problem statement:** SIH26151 — Dark Web Threat Actor De-anonymization.
  *(Asserted by the user requesting this document; not found verbatim in any file
  in this repository — `MASTER_CONTEXT.md` names the event and team but not a
  problem-statement code. Recorded here for continuity; verify against the
  competition portal or the separate GOTHAMITE repository if it matters.)*
- **Team:** AvivCREW (`MASTER_CONTEXT.md` line 4, `README.md` line 4).
- **Event:** Smart India Hackathon 2026 — internal college round + SIH prototype
  (`MASTER_CONTEXT.md` line 5).
- **This repository (`darkweb-sandbox`) is a sandbox, not the graded deliverable.**
  `AgentsDocs/IMPLEMENTATION_PLAN.md` line 21: *"This repo is not the graded SIH
  deliverable — GOTHAMITE is."*
- **What this repository is:** a simulated onion-routed network (relay pool +
  directory + onion client), three deterministic mock dark-web sites, and a
  scraper agent that crawls them through the relay chain and POSTs artifacts to
  GOTHAMITE. It is explicitly **not** real Tor, does not touch the real dark web,
  and every claim about it is meant to be literally demonstrable
  (`MASTER_CONTEXT.md` §1).
- **Relationship to GOTHAMITE:** two separate repositories, one data pipeline.
  `AgentsDocs/MASTER_CONTEXT.md` §2: *"`API_CONTRACT.md` is the only place these
  two repos touch. The scraper agent lives here. GOTHAMITE never imports anything
  from this repo, and this repo never imports anything from GOTHAMITE."* **No
  GOTHAMITE repository exists in this workspace, in any sibling directory, as a
  git remote, or as a submodule** — confirmed during the Phase-5 preflight audit
  (see `AgentsDocs/reports/CONSOLIDATED_FREEZE_REVIEW.md` and
  `AgentsDocs/SPEC_DECISIONS.md` SD-021's project-state clarification).

---

## 2. Current phase status

| Phase | Status | Purpose | Implementation | Tests |
|---|---|---|---|---|
| **Phase 1** — Single hop, proven crypto | ✅ **COMPLETE, Docker-verified** | Prove the crypto and one-hop routing mechanism | `relay/`, `client/`, `common/`, `directory/`, `phase1_endpoint/` | `tests/test_phase1.py` — **61/61** |
| **Phase 2** — Directory service | ✅ **COMPLETE** (folded into Phase 1/3 work; no separate report) | Relay registration and path selection | `directory/directory_service.py` | covered within `test_phase1.py` |
| **Phase 3** — Full multi-hop path | ✅ **COMPLETE** (folded into Phase 1 implementation; relay pool is multi-hop from the start per SD-000) | N-hop onion routing | `relay/`, `client/onion_client.py` | covered within `test_phase1.py` |
| **Phase 4** — Mock sites | ✅ **COMPLETE, Docker-verified** | Three deterministic mock forums/marketplace with planted identifiers | `mock_sites/` (`seed_data.py`, `site_server.py`, `docker-compose.sites.yml`) | `tests/test_phase4.py` — **42/42** |
| **Phase 5** — Scraper agent | ✅ **COMPLETE** (sandbox side only) | Crawl the three mock sites through the relay chain, extract fields, POST to GOTHAMITE | `scraper/` (`extract.py`, `contract.py`, `scraper_agent.py`) | `tests/test_phase5.py` — **54/54** |
| **Phase 6** — Integration and demo hardening | ❌ **NOT STARTED** | Cold-start `docker compose up` → scraper runs → data visible in GOTHAMITE's dashboard; recorded demo video | none | none |
| **GOTHAMITE backend** (`/api/v1/ingest` server, storage, correlation, dashboard) | ❌ **NOT IMPLEMENTED in this repository, and must not be** | The counterparty system | **does not exist anywhere in this workspace** | n/a |

Relay-relay carry inside real Docker containers (as opposed to the loopback test
harness) is **not independently reproduced** — recorded as a Phase-6 hardening
recommendation in `AgentsDocs/reports/PHASE_1_REPORT.md`, not a blocker.

---

## 3. Verified test status

Most recent full-suite run (end of Phase 5, 2026-09-08):

| Suite | Result |
|---|---|
| Phase 1 (`tests.test_phase1`) | **61/61 OK** |
| Phase 4 (`tests.test_phase4`) | **42/42 OK** |
| Phase 5 (`tests.test_phase5`) | **54/54 OK** |
| Combined (`unittest discover -s tests -t .`) | **157/157 OK** |
| `py_compile` on all scraper/relay/client/test modules | clean |
| `git diff --check` | clean (CRLF advisories only — this checkout is Windows/`core.autocrlf`) |

No test is skipped, expected-failed, or marked flaky anywhere in the suite. No
test contacts the real network — confirmed by explicit assertions in both
`test_phase1.py` and `test_phase4.py` and by the loopback-only design of
`tests/harness.py`.

---

## 4. Phase 5 verified output (an actual scraper run)

Recorded in `AgentsDocs/reports/PHASE_5_REPORT.md` §11, against the live mock
sites through the real relay chain, delivering to a **test receiver**
(`tests/ingest_receiver.py` — not GOTHAMITE, see §9 below):

```
Sources attempted:      3
Pages fetched:          57
Artifacts sent:         57   (accepted 57, duplicate 0, failed 0)
Identifiers extracted:  PGP 13 | wallet 16 | handles 0

by page_type      {'index': 3, 'item': 48, 'profile': 6}
by source         {'forum-alpha': 19, 'marketplace-beta': 19, 'forum-gamma': 19}
identifiers       {'pgp_fingerprint': 13, 'wallet': 16}   total 29
personas          6
ingest attempts   57       received by stub   57
artifacts with a 3-relay path: 57
payload keys seen: collected_at, content_hash, identifiers, page_type, persona,
                   raw_content, relay_path, source_id, source_type, url
forbidden keys present: none   (no relationship/score/edge/actor keys)
payloads validated: 57         payloads failing: 0
```

Every count matches what the corpus was built to contain — nothing here is
hardcoded except the three source hosts; counts fall out of the crawl.

---

## 5. Architecture and the sandbox → GOTHAMITE boundary

```
mock forums / marketplaces  (mock_sites/, 3 sites, Flask-free stdlib servers)
        ▲  routed through
  relay pool + directory    (relay/, directory/, 7 relays, RSA-OAEP + AES-GCM)
        ▲  uses
   onion_client              (client/onion_client.py)
        ▲  uses
  scraper_agent  ───────────────►  POST /api/v1/ingest  ───────────►  GOTHAMITE
  (scraper/scraper_agent.py)       (API_CONTRACT.md, the ONLY seam)   (separate repo,
                                                                        not implemented)
```

**The seam:** `POST http://gothamite-backend:8000/api/v1/ingest`,
`Content-Type: application/json`, **one request per artifact** (one scraped page),
never batched (`API_CONTRACT.md` §2).

**Currently authoritative payload fields** (`API_CONTRACT.md` §3, all IN FORCE):

| Field | Required? | Rule |
|---|---|---|
| `source_id` | yes | exactly `forum-alpha` \| `marketplace-beta` \| `forum-gamma` |
| `source_type` | yes | `forum` \| `marketplace` |
| `page_type` | yes | exactly `index` \| `item` \| `profile`, **no default** (SD-021) |
| `url` | yes | canonical absolute HTTP URL, `http://<mock-host>/<path>`, `.onion.mock` host required, index keeps its trailing slash (SD-023) |
| `collected_at` | yes | ISO 8601 UTC, `Z` suffix — scrape time |
| `relay_path` | yes | ordered relay ids actually used |
| `raw_content` | yes | verbatim page content, not cleaned/stripped/truncated |
| `content_hash` | yes | `sha256:` + hex digest of `raw_content` as UTF-8 bytes |
| `persona` | depends on `page_type` | **omitted** for `index`; required (handle only) for `profile`; required (handle + `observed_at`) for `item` |
| `identifiers` | yes | may be `[]`; only `pgp_fingerprint` and `wallet` are ever emitted (SD-022); every identifier object requires its own `observed_at`, never a substitute timestamp (SD-021.2) |

**Responses** (`API_CONTRACT.md` §4): `202` accepted; `200` + `duplicate_content_hash`
on a repeat `content_hash`+`source_id` (not an error); `400` + `errors[]` on a
malformed payload (scraper skips and continues); `5xx` retried twice with backoff
then logged and continues.

**GOTHAMITE's responsibilities at ingest** (`API_CONTRACT.md` §5): store
`raw_content` before parsing; treat every field as untrusted input; **never create
a Relationship at ingest time** — correlation is a separate pass over stored data;
verify `content_hash` against the received `raw_content`.

---

## 6. Authoritative documents

| Document | Authoritative for |
|---|---|
| `AgentsDocs/MASTER_CONTEXT.md` | Project identity, scope lock, what must never be built here. **Read first.** |
| `AgentsDocs/API_CONTRACT.md` | **The sandbox ↔ GOTHAMITE wire format.** Self-authoritative as of SD-025 — its own line 4 now reads *"This file is authoritative for the sandbox ↔ GOTHAMITE wire format... A disagreement between this contract and either side's internal model is a change request against this file, not an automatic override of it."* |
| `AgentsDocs/DATA_MODEL.md` | §4–§5: **the sandbox's simulated seed data and ground truth** (SD-014, SD-025 §2 scope note). §2–§3 (entity tables, scoring weights): **descriptive of the expected GOTHAMITE representation only, explicitly non-normative for GOTHAMITE** (SD-026). Where a §2 field also appears on the wire, `API_CONTRACT.md` governs, not this file. |
| `AgentsDocs/RELAY_PROTOCOL.md` | The routing layer. Its own line 7: *"If code and this document disagree, this document is correct."* Amended by SD-029/SD-030 (§§6, 9.1, 9.3) and by the SD-024 freeze amendments (§§6, 7, 9.1–9.5) — implementation matches it. |
| `AgentsDocs/SCRAPER_AGENT_SPEC.md` | Scraper crawl/extraction behaviour. §7's run-summary block is illustrative for the current corpus (corrected 2026-09-08), not a universal constant. |
| `AgentsDocs/MOCK_SITES_SPEC.md` | Mock-site corpus rules, including the SD-028 attribution invariant (rule 6) and the no-identifier rule for index/profile pages (rule 7). |
| `AgentsDocs/SPEC_DECISIONS.md` | **The decision record.** Every architectural choice that isn't derivable from the other specs, with explicit PROPOSED/IN FORCE status per entry. Read this before assuming any ambiguity is still open. |
| `AgentsDocs/IMPLEMENTATION_PLAN.md` | Phase sequencing and per-phase acceptance criteria. **Partially superseded**: Phase 5's "Blocked on: GOTHAMITE `docs/DATA_MODEL.md`" line predates SD-025 and is stale (see §8 below). |
| `AgentsDocs/reports/PHASE_1_REPORT.md`, `PHASE_4_REPORT.md`, `PHASE_5_REPORT.md` | What was actually built and verified for each completed phase, with exact test counts and any deviations. |
| `AgentsDocs/reports/CONSOLIDATED_FREEZE_REVIEW.md` | The full audit trail for the 2026-09-07 contract freeze and the 2026-09-08 OPEN-9 closure — all thirteen B-items, both status. |
| `AgentsDocs/reports/*_DECISION_BRIEF.md` | Analysis behind individual SDs (A1, A3, B4, layer_malformed, OPEN-4/5/6/9). Historical reasoning, not itself normative — the SD entries are. |

**SD-025 and the authority hierarchy are explicitly preserved as of this
document.** `API_CONTRACT.md` line 4 carries SD-025's wording; `MASTER_CONTEXT.md`
§2 was corrected 2026-09-08 to match it (it previously said GOTHAMITE's
`docs/DATA_MODEL.md` wins on disagreement — that was the obsolete rule SD-025
superseded, and the correction is recorded in `MASTER_CONTEXT.md` itself with a
note citing SD-025).

---

## 7. Decisions currently IN FORCE (practical consequence only)

| SD | Practical consequence for future work |
|---|---|
| **SD-014** | `AgentsDocs/DATA_MODEL.md` is this repo's own document for sandbox ground truth, not a synced copy of a GOTHAMITE file. Do not restate a GOTHAMITE data model here. |
| **SD-015** | Persona A1/A2's canonical wallet is the base58 form `1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6`. No bech32, no mixed-format extraction, anywhere. |
| **SD-016** | Exactly one decoy persona (C1, `nightjarr`) — do not add more. |
| **SD-017** | All mock-site timestamps: ISO 8601, UTC, `Z` suffix. No other timezone handling. |
| **SD-018** | B1's last post is `2026-04-02T11:26:00Z`, B2's first is `2026-04-19T10:12:00Z` — a 17-day gap, matching `DATA_MODEL.md` §4's stated score derivation. |
| **SD-019** | Mock sites emit no `Date` header — responses are byte-identical across restarts by design. Don't add one back. |
| **SD-020** | The directory is `mock_sites/`, not `mock-sites/`. |
| **SD-021** (+ .1, .2) | `page_type` is required, closed-enum (`index`\|`item`\|`profile`), **no default**. `persona`/`observed_at` follow the matrix in §5 above. Never substitute a surrogate timestamp for a missing `observed_at`. |
| **SD-022** | Only `pgp_fingerprint` and `wallet` are ever emitted as identifiers. `handle` and `contact` stay reserved in the enum but unemitted. A handle travels only in `persona.handle`. Mentioned handles (someone else's handle appearing in a post) are never identifiers and never create a persona. |
| **SD-023** | `url` is a canonical absolute HTTP URL, `http://<mock-host>/<path>`, index keeps its trailing slash. No scheme-less or bare-path form anywhere on the wire. |
| **SD-024** | Relay protocol: errors travel sealed under the normal return path (E2) as `{"type":"error","code":...,"reported_by":...}` (D2), HTTP status is transport-only (200 for any sealed envelope). **SPEC AMENDED status** (not "IN FORCE" as a category) — this is SD-024's own recorded structure, not an omission. §C's closed set is now four values via SD-030. |
| **SD-025** | `API_CONTRACT.md` is self-authoritative for the sandbox↔GOTHAMITE wire. Neither repo's internal model overrides it; a disagreement is a change request against the contract, not a silent override. **This is the rule a future agent must not accidentally re-flip** — the obsolete "GOTHAMITE DATA_MODEL wins" wording has already been found and corrected once (in `MASTER_CONTEXT.md`), so check for it if resurrecting old text. |
| **SD-026** | `DATA_MODEL.md` §2/§3 are descriptive/non-normative for GOTHAMITE. `Artifact.url` in §2 reads as the absolute URL, matching the wire, not "mock-site path". |
| **SD-027** (+ R2 addendum) | D1 (`bellwether`) carries **no** counterparty identifier — listing 44 was rewritten to remove A2's wallet. D1 is now the co-location negative control: same site as A2, overlapping window, shares nothing, must produce no edge. Do not reintroduce a cross-persona identifier into the corpus without also extending the SD-028 guard. |
| **SD-028** | `Identifier.persona_id` means **attribution/ownership**, not "observed on this page". The corpus invariant enforcing this: no page may carry a PGP fingerprint or wallet belonging to another persona (`MOCK_SITES_SPEC.md` §2 rule 6), enforced by `tests/test_phase4.py::test_no_page_carries_another_personas_identifier`, which scans **rendered pages**, not the persona→identifier map. |
| **SD-029** | The one case a relay answers in plaintext (it cannot decrypt its own layer, holds no key): HTTP 400, exactly `{"error":"decryption_failure","reported_by":"<own relay_id>"}`. Travels one hop only, never forwarded. Implemented in `relay/relay_node.py`. |
| **SD-030** | Fourth closed relay error code, `unusable_layer`: a layer that decrypted and authenticated fine but has an unusable `next_port` or `payload`. Relay **must** seal (it holds the key), HTTP 200. Implemented in `relay/relay_node.py`; `int()` coercion pitfalls (`8080.9`, `True`) are explicitly guarded against — see `_usable_port` in that file. |

---

## 8. Open / non-blocking debt

**Blocking:** none currently known. Every SD-021 through SD-030 blocker is closed;
Phase 5 acceptance criteria that don't require a live GOTHAMITE are all verified.

**Non-blocking, recorded in the spec/decision trail:**

- **OPEN-8** (still open in `SPEC_DECISIONS.md` §2): `IMPLEMENTATION_PLAN.md`
  Phase 4's acceptance criterion 1 assumed the relay chain wasn't built yet;
  it now is (SD-000). Resolved in practice; the sequencing note in
  `format/AGENT_TASK_SPLIT.md` §4 is still textually inconsistent. Cosmetic.
- **SD-027 residuals 2, 3, 5** — `transacted_with`/`trusts` have no production
  rule anywhere and nothing in the corpus exercises them; residual 5's "only
  attribution principle" framing is stale (superseded by SD-028's rule 6).
  Non-blocking: correlation is GOTHAMITE's job, not this repo's.
- **SD-028 residuals 1–3** — two attribution principles (SD-022.4 for handles,
  rule 6 for PGP/wallets) rather than one unified rule; the guard covers only
  the two identifier types currently emitted; an observational (as opposed to
  ownership) identifier model is deferred entirely to future GOTHAMITE
  architecture. None require a decision before further sandbox work.

**Documentation debt (cosmetic, not architectural):**

- `AgentsDocs/IMPLEMENTATION_PLAN.md` line 119, Phase 5: *"Blocked on: GOTHAMITE
  `docs/DATA_MODEL.md` and this repo's `API_CONTRACT.md`"* — the first clause
  predates and is superseded by SD-025. Not corrected yet (deliberately, per
  explicit instruction in the session that shipped Phase 5, to keep that edit
  separate from implementation work).
- `README.md` lines 222–223 and `requirements.txt` both still say Phase-5 will
  need `requests` and `beautifulsoup4`. **The actual Phase-5 implementation uses
  neither** — `scraper/extract.py` is regex-based and `scraper/scraper_agent.py`
  reuses `common.http_util.post_json` for delivery, per the explicit "no
  unnecessary dependencies, no LLM" implementation discipline. This is a stale
  forward-reference discovered while writing this handoff; not yet corrected.
- `AgentsDocs/SCRAPER_AGENT_SPEC.md` §3 carries two sentences about link-
  following that read against each other in isolation (resolved in the Phase-5
  implementation by treating index-page links as filtered candidates — see
  `AgentsDocs/reports/PHASE_5_REPORT.md` §3 — but the spec text itself is
  unedited).
- `raw_content` wording: `API_CONTRACT.md` doesn't explicitly say whether it
  means the whole HTTP response or the body alone. Phase 5 implemented "body
  alone" with a recorded rationale (`PHASE_5_REPORT.md` §5); SD-019 already
  established this makes no observable difference for the current corpus.
- Retry backoff duration for `5xx` responses is unspecified in
  `API_CONTRACT.md`/`SCRAPER_AGENT_SPEC.md` §6; `scraper_agent.py` uses an
  implementation default (`DEFAULT_BACKOFF = 0.5`), not a specified value.

**Future GOTHAMITE-side work (out of this repository's scope entirely):**

- The `/api/v1/ingest` server itself, with real validation against
  `API_CONTRACT.md`.
- Artifact storage, `content_hash` verification, real `duplicate_content_hash`
  detection.
- The correlation pass, scoring per `DATA_MODEL.md` §3 (descriptive only here),
  actor/relationship graph, dashboard.
- Real end-to-end verification of `SCRAPER_AGENT_SPEC.md` §8 criterion 9 and
  `API_CONTRACT.md` §6 criteria 5–6, which currently are verified only against
  the **test receiver** (`tests/ingest_receiver.py`), not a real GOTHAMITE.

---

## 9. Current repository scope — what must NOT be implemented here

Per `MASTER_CONTEXT.md`'s scope lock and every Phase 5 instruction reaffirming
it, **do not implement in `darkweb-sandbox` unless explicitly re-authorized**:

- The GOTHAMITE `/api/v1/ingest` **server**. `tests/ingest_receiver.py` is a
  test double only — it records requests and replies as instructed, performs no
  validation, storage, deduplication, or correlation, and is explicitly
  documented in its own module docstring as not reusable for a real
  implementation. **Never mistake it for GOTHAMITE, and never let it grow into
  one.**
- Attribution engine, actor intelligence store, or any correlation/scoring
  logic. `DATA_MODEL.md` §3's weights are descriptive only (SD-026); nothing in
  this repo computes them.
- Any relationship, edge, or graph object. The scraper's own payloads are
  tested to carry none (`tests/test_phase5.py::TestSafetyAndScope`).
- Production data storage of any kind (PostgreSQL, artifact database models).
- The GOTHAMITE dashboard/frontend.
- Real Tor, real `.onion` networking, CREATE/EXTEND, perfect forward secrecy,
  DHT/descriptors, guard persistence, traffic padding, timing defenses, or any
  claim of real anonymity (`RELAY_PROTOCOL.md` §10, `MASTER_CONTEXT.md` §3).
- Stylometry, behavioral profiling, or actor attribution of any kind
  (`MOCK_SITES_SPEC.md`, reaffirmed for Phase 5 in the implementation
  instructions).
- Phase 6 work (demo hardening, cold-start reliability, the recorded video) —
  not started, and out of scope until Phase 5's sandbox-side completeness is
  confirmed sufficient by a human.

---

## 10. Next action

**Implement the GOTHAMITE-side `/api/v1/ingest` consumer in the separate
GOTHAMITE repository, and perform real end-to-end integration testing** against
the scraper already built here. Concretely, that means:

1. Stand up (in the GOTHAMITE repo, not this one) an endpoint matching
   `API_CONTRACT.md` §2–§4 exactly, including real `content_hash` verification,
   real `duplicate_content_hash` detection, and storage that never creates a
   Relationship at ingest time (§5 rule 3).
2. Point `scraper/scraper_agent.py --ingest <real-url>` at it (or set
   `INGEST_URL`) and run a real crawl of the Phase-4 corpus.
3. Verify `SCRAPER_AGENT_SPEC.md` §8 criterion 9 and `API_CONTRACT.md` §6
   criteria 5–6 for real, which is the one thing this repository's own test
   suite cannot do.
4. Only after that: Phase 6 (cold-start reliability, `docker compose up` to
   visible dashboard data, the recorded demo).

---

## 11. Handoff rules for the next agent (agy or otherwise)

- **Do not redo completed phases.** Phases 1, 4 and 5 are implemented, tested,
  and reported. Re-verify with the existing test suites (§3 above) rather than
  re-implementing anything.
- **Do not reopen IN FORCE decisions without new evidence.** Every SD in §7 is
  the settled answer to a real ambiguity that was analyzed and resolved. If
  something in that list looks wrong, that is a signal to re-read the decision
  brief cited in `SPEC_DECISIONS.md`, not to silently pick a different answer.
- **Do not guess when specifications conflict.** This project's whole working
  pattern has been: find the conflict, write a decision brief, get a human
  decision, record it as an SD, then implement. Continue that pattern.
- **Stop and ask when a blocking ambiguity is discovered.** Don't invent
  semantics to keep moving — see the "STOP conditions" pattern used throughout
  Phase 5's implementation instructions and honored in `PHASE_5_REPORT.md`.
- **Treat this file as a navigation document.** The specifications listed in §6
  remain authoritative; if this file and one of them disagree, the specification
  wins and this file is stale and should be corrected.
- **Distinguish implemented functionality from planned architecture explicitly.**
  Phases 1/4/5 are real code with real tests. Phase 6 and the GOTHAMITE backend
  are architecture described in documents, not code that exists.
- **Never claim real GOTHAMITE integration based solely on the test receiver.**
  `tests/ingest_receiver.py` proves the *scraper's* behavior under each response
  type the contract defines. It proves nothing about a real GOTHAMITE service,
  because no such service has been built anywhere this repository can see. Every
  claim in this file and in `PHASE_5_REPORT.md` about GOTHAMITE-dependent
  criteria is qualified as "verified with test receiver only" for exactly this
  reason — keep that qualification when reporting further progress.
