# Phase 4 Report — Mock Sites

**Date:** 2026-09-07
**Scope:** `IMPLEMENTATION_PLAN.md` §3 Phase 4 only. Phases 5 and 6 untouched.

---

## Built

- `mock_sites/seed_data.py` — six personas, 48 posts, every identifier copied
  character for character from `DATA_MODEL.md` §4. No generation, no runtime
  values.
- `mock_sites/site_server.py` — one stdlib server for all three sites, keyed by
  `SITE_ID`. Index, thread/listing and profile pages per `MOCK_SITES_SPEC.md` §4.
- `mock_sites/docker-compose.sites.yml` — `forum-alpha`, `marketplace-beta`,
  `forum-gamma`, no host ports, `sandbox-net` as external.
- `scripts/phase4_demo.py` — Docker-free crawl of all three sites through the
  relay chain.
- `tests/test_phase4.py` — 42 tests.
- `tests/harness.py` — extended with `with_sites=True`; Phase-1 behaviour unchanged.
- `Dockerfile` — one added `COPY mock_sites/` line.

**Dependencies added: none.** Standard library only; `requirements.txt` untouched.

---

## Tested — how, not just whether

**Phase 4: 42 tests, 42 passed, 0 failed**, 137s — re-verified 2026-09-07 after the
contract-freeze amendments (B11 and B12). The pre-amendment baseline was 41/41.
**Phase 1 regression: 38 tests, 38 passed, 0 failed** — see below.

Every page is fetched **through a real 3-hop relay path** before anything is
asserted about it. The module-level fixture crawls all three sites — 57 pages,
each on a freshly selected path — and the tests assert against those captured
bytes, not against the rendering functions.

Three things were done deliberately so the tests could fail:

- **Identifiers are asserted against literals written out in the test file**, not
  against `mock_sites.seed_data`. Comparing pages only to the module that renders
  them would pass even if that module had drifted from `DATA_MODEL.md`. The
  literals are the actual guard against drift.
- **Reachability is not inferred from a 200.** A page can be correct and still
  have been fetched directly, which would make criterion 1 meaningless. The test
  asserts three distinct relays in the path and one response envelope per hop —
  proof the page really came back through three layers of re-encryption.
- **Absence is asserted, not just presence.** Every base58-shaped string on every
  page must be a known seed wallet; every rendered fingerprint must normalise to a
  known one; and every persona pair that is *not* documented as sharing an
  identifier is checked for accidental collision. A stray wallet would create a
  link GOTHAMITE could not explain, which is worse than a missing one.

---

## Acceptance criteria — `MOCK_SITES_SPEC.md` §7

- [x] 1. All three sites reachable through a full relay path — 57 pages fetched
      through 3-hop circuits; path composition and per-hop re-encryption asserted
- [x] 2. None reachable directly from the host — verified live under Docker; see
      "Docker verification" below
- [x] 3. Every persona present with the exact handle and active window — six
      personas, first and last post landing on the window endpoints
- [x] 4. PGP fingerprints and wallets match `DATA_MODEL.md` character for
      character — including the canonical A1/A2 wallet per SD-015
- [x] 5. A1/A2 share both; B1/B2 share wallet only; C1 shares nothing
- [x] 6. B1's last post precedes B2's first by roughly 17 days — exactly 17
- [x] 7. Content stable across restarts, identical bytes every time — asserted
      across a full server restart, headers included (SD-019)
- [x] 8. No real-world content, no operational detail — asserted against a banned
      phrase list, plus no URLs, emails, real hostnames or bare `.onion` strings

**`IMPLEMENTATION_PLAN.md` §3 Phase 4**

- [x] 1. All three reachable through a full relay path
- [x] 2. Seeded personas, fingerprints and wallets present and consistent
- [x] 3. Planted cross-site links exist as specified
- [x] 4. Decoy present — similar-looking, genuinely unlinked
- [x] 5. Content stable and deterministic, no randomly generated personas

---

## The planted links, as built

| Link | Mechanism | Where |
|---|---|---|
| A1 ↔ A2 | same PGP **and** same wallet | forum-alpha ↔ marketplace-beta |
| B1 → B2 | same wallet, **rotated** PGP, 17-day gap | forum-alpha → forum-gamma |
| C1 vs A1 | handle one character apart, overlapping activity, **nothing shared** | forum-gamma vs forum-alpha |
| D1 vs A2 | **same site**, overlapping activity, **nothing shared** | marketplace-beta |

**Two positive links and two negative controls.** The decoys cover different false
positives: C1 is a *similar handle* on a different site — a signal `DATA_MODEL.md` §3
does score, at 0.05 — while D1 is a *shared venue and period*, which §3 scores not at
all. Neither may produce an edge.

**Changed 2026-09-07 by SD-027 and its R2 addendum.** D1 previously carried A2's
wallet on listing 44 as a counterparty reference, and this table previously claimed a
`transacted_with` edge. That was unachievable: `Identifier.persona_id` is a required
FK, a regex extractor cannot read the disclaiming prose around an address, and the
shared wallet scored 0.45 — producing exactly the `same_actor_suspected` edge that
`DATA_MODEL.md` §4 forbade in bold. The reference is removed from the corpus, the
transaction scenario is withdrawn, and D1 is now the co-location negative control.
**No seed scenario produces a `transacted_with` or `trusts` edge**; both remain valid
`Relationship.type` values that nothing in the demo exercises.

The replacement guard is `test_no_page_carries_another_personas_identifier`, which
scans the **rendered** pages and checks every wallet and fingerprint against the
author read from that same page's byline. The map-level test that existed throughout
could never have caught the original defect: listing 44 left every persona's own
values correct and still put A2's wallet on a page written by D1.

No relationship exists that the specification does not require. No scoring,
correlation, attribution, stylometry or profiling logic is implemented anywhere in
`mock_sites/` — the sites are observation sources; the graph reasoning is
GOTHAMITE's.

---

## Specification decisions made

Four resolved from the existing specification, one contradiction reconciled. All
in `SPEC_DECISIONS.md`.

- **SD-016** closes **OPEN-3** — exactly one decoy persona. The plan says "decoy
  personas" (plural), the data model specifies one. Resolvable without a product
  decision: SD-014 makes the data model authoritative for seed data, and a second
  decoy would have no defined handle, window, key, wallet or row in the
  expected-output table.
- **SD-017** closes **OPEN-7** — timestamps are ISO 8601, UTC, `Z` suffix,
  following `API_CONTRACT.md` §3, which already fixes that format for the field
  these become.
- **SD-018** reconciles a real contradiction. `MOCK_SITES_SPEC.md` §5 wants B1's
  last post "strictly before 2026-04-02" and B2's first "strictly after
  2026-04-19" — a gap of at least 19 days. `DATA_MODEL.md` §4 gives those dates as
  the window endpoints and annotates the pair "(17-day gap)", deriving B1→B2's
  expected 0.60 from it. The data model wins by its own authority line and by
  SD-014. Satisfying §5 literally would have changed a number the demo claims.
- **SD-019** — the sites emit no `Date` header, making criterion 7's "identical
  bytes every time" true of the whole response rather than only the page body.
  This closes an ambiguity the Phase-1 report recorded as a finding.
- **SD-020** — the directory is `mock_sites/`, not `mock-sites/`. A hyphen cannot
  appear in a Python package name, so the documented path cannot be imported or
  launched with `python -m`, which is how every other service starts.

---

## Docker verification

Run against the full stack:

```
docker compose -f docker-compose.yml -f mock_sites/docker-compose.sites.yml up -d --build
```

Twelve containers running: directory, seven relays, the Phase-1 endpoint, and
`forum-alpha`, `marketplace-beta`, `forum-gamma`.

**Criterion 2, both halves.** Direct from the host fails, the same page through
the chain succeeds — which is the criterion as written, and neither half proves it
alone:

```
curl http://localhost/       -> exit 7, no connection
curl http://localhost:8080/  -> exit 7, no connection
```

`docker compose ps` confirms the only published port in the entire stack is the
directory's `8000`; all three sites and all seven relays publish nothing.

Then, through a 3-hop path:

| Address | Resource | Path | Result |
|---|---|---|---|
| `alpha7fq2mx9k.onion.mock` | `/thread/14` | relay-01 → relay-02 → relay-03 | 200, canonical A1 wallet + A's fingerprint |
| `beta4np8vz3wc.onion.mock` | `/listing/44` | relay-01 → relay-04 → relay-02 | 200, A2's wallet named as counterparty, "theirs, not mine" |
| `gamma2xd6bt5hy.onion.mock` | `/thread/62` | relay-01 → relay-06 → relay-05 | 200, C1's own fingerprint |

The `/thread/14` response also confirms two things beyond reachability: it matches
`API_CONTRACT.md` §3's worked example exactly — same URL, same handle, same
`observed_at` of `2026-03-11T09:14:00Z` — and it carries `Server: mock-site` with
**no `Date:` header**, so SD-019's determinism holds in the container, not just in
the test harness.

**One fix was needed to get here.** The sites file originally used
`build: context: ..`, on the assumption that relative paths resolve against the
file's own directory. They resolve against the *project* directory — the directory
of the first `-f` file — so the build failed with "failed to read dockerfile".
Corrected to `context: .`, with a comment recording why.

---

## Stubbed / faked / incomplete

Nothing. No placeholder files, no unimplemented functions.

The Phase-1 endpoint (`phase1_endpoint/`, and its compose service) is now
superseded — SD-012 said to delete it at Phase 4. It has been **kept**, for two
reasons: the Phase-1 Docker verification recorded in `PHASE_1_REPORT.md` carries a
request to it and would become unreproducible, and removing it was outside the
"do not modify unrelated Phase 1 implementation" instruction this phase ran under.
Deleting the service block and the package is a one-line cleanup for whoever
closes Phase 6; the Phase-1 test suite needs the module, not the container.

---

## Open items

Resolved this phase: **OPEN-3** (SD-016), **OPEN-7** (SD-017).

Still open:

- **OPEN-4** — `persona.handle` is required by `API_CONTRACT.md` §3, but the crawl
  structure includes index pages with no single author. **Phase 5, and it will bite
  immediately** — the index pages this phase serves are exactly the case.
- **OPEN-5** — whether `handle` and `contact` are ever emitted as `identifiers[]`.
  Phase 5.
- **OPEN-6** — whether `url` in the ingest payload carries a scheme. Phase 5.
- **OPEN-8** — the Phase-4 gate sequencing note in `format/AGENT_TASK_SPLIT.md`.
  Moot in practice: the relay chain existed before this phase, and the sites were
  verified through it.
- **OPEN-9** — the error envelope. Untouched, still deferred. Before Phase 6.

**New, found during implementation:** `MOCK_SITES_SPEC.md` §5's B1/B2 bullets
cannot both be satisfied alongside `DATA_MODEL.md` §4's windows. SD-018 records how
it was resolved; the document itself is left as written.

---

## Ready for next phase: YES

All eight `MOCK_SITES_SPEC.md` §7 criteria and all five `IMPLEMENTATION_PLAN.md`
Phase-4 criteria passed under observation, on loopback and in containers. Nothing
in Phase 4 is unverified.

**OPEN-4 should be answered before Phase 5 starts**, not during it: the scraper
cannot POST an index page without knowing what `persona.handle` should contain
when a page has no single author.
