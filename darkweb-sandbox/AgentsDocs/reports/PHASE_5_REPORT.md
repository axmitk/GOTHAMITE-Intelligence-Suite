# Phase 5 Report — Scraper Agent

**Date:** 2026-09-08
**Scope:** `IMPLEMENTATION_PLAN.md` §3 Phase 5 only. Phase 6 untouched.
**Authority:** `API_CONTRACT.md` for the wire (SD-025, in force), `SCRAPER_AGENT_SPEC.md`
for scraper behaviour, `RELAY_PROTOCOL.md` for routing.

---

## 1. Files created

| File | Purpose |
|---|---|
| `scraper/__init__.py` | Package docstring stating what the package is *not* |
| `scraper/extract.py` | Page classification, route discovery, PGP/wallet/byline extraction |
| `scraper/contract.py` | Local validation of a payload against `API_CONTRACT.md` §3 |
| `scraper/scraper_agent.py` | Crawl orchestration, payload construction, delivery, run summary |
| `tests/test_phase5.py` | 54 tests |
| `tests/ingest_receiver.py` | **Test double** for the far side of the seam |

**Dependencies added: none.** Standard library only; `requirements.txt` untouched.

Nothing under `relay/`, `client/`, `common/`, `directory/`, `mock_sites/`,
`phase1_endpoint/` or `scripts/` was modified, and no specification was edited.

## 2. Architecture and data flow

```
SOURCES (3, hardcoded)
   └─ client.get_path(3)                one relay path per source
        └─ get_with_trace(path, host, route)   →  raw HTTP response + Trace
             └─ extract.http_body()            →  the page
                  ├─ extract.classify(route)   →  page_type
                  ├─ extract.byline()          →  handle + observed_at
                  ├─ extract.pgp_fingerprints()
                  └─ extract.wallets()
                       └─ build_payload()      →  one artifact
                            └─ contract.validate()   (local, before delivery)
                                 └─ POST /api/v1/ingest   (one per artifact)
```

The scraper reuses the existing client and HTTP utilities entirely. It defines no
transport, no crypto, and no routing of its own.

## 3. Discovery strategy

`SCRAPER_AGENT_SPEC.md` §3 contains two sentences that pull against each other:
*"It does not discover URLs by parsing links out of page content and following
them"*, and *"If a link on a page points outside the site's own host: ignore it
silently"* — the second only makes sense if links are read at all.

The preflight recorded this as non-blocking because both readings yield the same
corpus. **The implementation reads the index page's links and filters them through
hardcoded route patterns**, which satisfies both sentences and §3's binding
constraint, *"any URL that did not come from the hardcoded structure is not
visited"*:

```python
ITEM_ROUTE    = re.compile(r"^/(?:thread|listing)/[0-9]+$")
PROFILE_ROUTE = re.compile(r"^/user/[A-Za-z0-9_]+$")
```

A link is a **candidate route, never a destination**. Off-host, protocol-relative,
traversal and unknown-shape links are dropped without being fetched, and
`test_out_of_scope_links_are_not_followed` asserts exactly that against a page of
hostile links. The alternative — hardcoding 48 item ids — was rejected because it
would bake corpus specifics into the scraper, against the instruction that the
counts should follow from the corpus.

**No new decision was created.** This is a choice between two readings of existing
text, recorded here rather than in `SPEC_DECISIONS.md`.

## 4. Extraction behaviour

- **PGP** — locate the block, read the `Fingerprint:` line, uppercase, strip all
  whitespace, require exactly 40 hex characters. Anything else is skipped and logged.
- **Wallet** — base58 regex with lookarounds (the *"not a substring of a longer
  alphanumeric run"* rule), then length 26–35 and no `0`/`O`/`I`/`l`. §4 is explicit
  that a false positive is worse than a miss, so a match is a candidate and the
  checks decide. **Zero false positives** across the corpus: all 16 are seed values.
- **Handles** — read from the byline into `persona.handle`. **Never emitted as an
  identifier** (SD-022). `contact` is never extracted.
- **Attribution** — every identifier is attributed to the page's own author, which
  is sound only because `MOCK_SITES_SPEC.md` §2 rule 6 guarantees no page carries
  another persona's identifier. A regex cannot tell "my address" from "I paid this
  address"; the guarantee lives in the corpus, not here (SD-028).

## 5. Payload construction

Per `API_CONTRACT.md` §3, with the `page_type` matrix driving persona:

| `page_type` | `persona` | `persona.observed_at` | `identifiers` |
|---|---|---|---|
| `index` | omitted entirely | n/a | `[]` |
| `item` | handle + observed_at | the post's own timestamp | PGP and/or wallet |
| `profile` | handle only | **omitted** — no join date, no latest post | `[]` |

`url` is `http://<mock-host>/<route>`, index keeping its trailing slash (SD-023).
`collected_at` is UTC `Z` at fetch time. `content_hash` is `sha256:` + the hex digest
of `raw_content` as UTF-8. `relay_path` comes from `Trace.path`.

### `raw_content` — the interpretation chosen

The preflight flagged this as ambiguous: `onion_client` returns the destination's
**whole HTTP response**, while the contract calls the field *"verbatim page
content"* and both worked examples (`API_CONTRACT.md` §3, `README.md` §4) show the
HTML document alone.

**Chosen: the HTTP body — the page.** Grounds, in order: the field's own description
says *page content*; both examples in the repository show a document with no status
line or headers; and `tests/test_phase4.py` already uses a `body_of()` helper
described as *"the page, without the HTTP status line and headers"*, so this is the
repository's established meaning of "the page". Nothing inside the document is
cleaned, stripped or truncated.

**This changes no observable contract property.** SD-019 anticipated the question and
recorded that *"for these sites the full response is stable, so either reading yields
the same hash"* — so determinism and duplicate detection hold under either. **No new
decision was created**, and the `SD-019`/contract wording is untouched.

## 6. Delivery and failure handling

`SCRAPER_AGENT_SPEC.md` §6, implemented in `ScraperAgent.deliver`:

| Response | Outcome | Retries |
|---|---|---|
| `202` / any 2xx | `ACCEPTED` | — |
| `200` + `duplicate_content_hash` | `DUPLICATE`, not an error | — |
| `400` | `REJECTED`, logged with the error body, artifact skipped | none |
| `5xx` | one attempt, then two retries with backoff, then `UNDELIVERED` | 2 |
| unreachable | `UNDELIVERED`, logged | none |
| fails local validation | `INVALID`, never sent | — |

**GOTHAMITE being absent, slow or broken never aborts the crawl.** A source whose
path request fails is skipped and the next source still runs.

Backoff duration is an implementation default (`DEFAULT_BACKOFF = 0.5`) with a
comment recording that §6 does not fix it. **Not specified as a decision.**

## 7. Local validation strategy

`scraper/contract.py` validates a payload against §3 *before* delivery and returns
**all** problems rather than the first. It checks required fields, the three enums,
URL rules, timestamp format, `content_hash` against `raw_content`, the `page_type`
persona matrix, identifier types/values/timestamps, the index/profile
no-identifier rule, and `relay_path`.

**It is not GOTHAMITE and not an ingestion endpoint.** It reads a request the
scraper just built; it stores nothing, deduplicates nothing, correlates nothing.
Nine tests attack it with payloads the contract forbids, so it is verified to
*reject*, not merely to accept.

## 8. Tests — 54

- **Crawl (6)** — three sources through 3-hop paths; 57 artifacts; page types; per-source shape; one index each; only hardcoded route shapes visited.
- **Extraction (9)** — identifier totals; fingerprint normalisation; wallet verbatim + validation; no handle/contact; `observed_at` on every identifier; index/profile carry none; persona matrix; six personas and no seventh; page-local attribution.
- **Payload (11)** — local validation; required fields; canonical URLs; index trailing slash; UTC `Z`; `collected_at` ≠ `observed_at`; `content_hash`; `raw_content` is the page; `relay_path`; source identity; one payload per artifact; no same-source hash collision.
- **Delivery (7)** — 2xx, duplicate, 400 (asserted **not** retried), 5xx retried exactly twice then accepted, persistent 5xx, unreachable, and a crawl that continues after one artifact is rejected.
- **Safety (7)** — no `eval`/`exec`/`compile`/`__import__`; no dangerous imports; off-host links dropped; no relationship or score keys in any payload; no scoring logic or `DATA_MODEL.md` §3 weight in the scraper (AST-based); only three sources; no real network host.
- **Run summary (3)** and **validator (9)**.

## 9. Acceptance criteria — `SCRAPER_AGENT_SPEC.md` §8

| # | Criterion | Status |
|---|---|---|
| 1 | All routing through `onion_client`, no direct HTTP | ✅ **Verified locally** — every fetch goes through `get_with_trace`; `relay_path` populated on all 57 |
| 2 | Only three hardcoded sources, no discovered links followed | ✅ **Verified locally** |
| 3 | All six seed personas found with correct handles | ✅ **Verified locally** — exactly 6, no seventh |
| 4 | PGP uppercase, whitespace stripped, 40 hex | ✅ **Verified locally** — 13 of 13 |
| 5 | Wallets verbatim, **zero false positives** | ✅ **Verified locally** — 16 of 16 are seed values |
| 6 | `observed_at` from posts, `collected_at` from scrape time, values differ | ✅ **Verified locally** |
| 7 | Every payload validates against the contract | ✅ **Verified locally** — 57/57, zero failures |
| 8 | A downed site does not abort the run | ✅ **Verified with test receiver** — and by the per-source skip path |
| 9 | Re-running yields `200 duplicate`, not duplicate artifacts | ⚠️ **Verified with test receiver only.** The scraper's handling is proven; that GOTHAMITE actually deduplicates **cannot be verified — GOTHAMITE is not implemented** |
| 10 | Run summary prints, showing a different relay path than the previous run | ✅ **Verified locally** — paths are re-selected per run |

`API_CONTRACT.md` §6 criteria 5 and 6 carry the same caveat as §8.9: the scraper's
behaviour on `200 duplicate` and on `400` is verified against the test receiver;
**the integration itself is not verified and is not claimed.**

## 10. Regression counts

| Suite | Result |
|---|---|
| Phase 1 | **61/61 OK** |
| Phase 4 | **42/42 OK** |
| Phase 5 | **54/54 OK** |
| Combined | **157/157 OK** |

`py_compile` clean on all scraper and test modules. `git diff --check` clean.

## 11. Scraper-run corpus counts

A real run against the live mock sites, delivering to the test receiver:

```
Sources attempted:      3
Pages fetched:          57
Artifacts sent:         57   (accepted 57, duplicate 0, failed 0)
Identifiers extracted:  PGP 13 | wallet 16 | handles 0

artifacts         57
by page_type      {'index': 3, 'item': 48, 'profile': 6}
by source         {'forum-alpha': 19, 'marketplace-beta': 19, 'forum-gamma': 19}
identifiers       {'pgp_fingerprint': 13, 'wallet': 16}  total 29
personas          6
ingest attempts   57
received by stub  57
payloads validated 57      payloads failing 0
artifacts with a 3-relay path: 57
payload keys seen: collected_at, content_hash, identifiers, page_type, persona,
                   raw_content, relay_path, source_id, source_type, url
forbidden keys present: none
```

Every figure matches the expected corpus exactly.

## 12. GOTHAMITE-dependent items that remain unverified

**No GOTHAMITE implementation exists**, and none was written here. Unverifiable:

1. **Real duplicate detection on re-scrape** — the scraper's handling is proven; the server's is not.
2. **Real `400` on a malformed payload** — same.
3. **`content_hash` verification at ingest** (`API_CONTRACT.md` §5 rule 4).
4. **`raw_content` stored before parsing** (§5 rule 1).
5. **No relationship created at ingest** (§5 rule 3) — the sandbox emits none, which is the half this repo can prove.
6. **Whether `raw_content` as the page body is what GOTHAMITE expects.**

The endpoint `http://gothamite-backend:8000/api/v1/ingest` has no service in
`docker-compose.yml`, so in a container run every artifact takes the *unreachable*
path — which §6 requires to be survivable, and which is tested.

## 13. Assumptions on the two non-blocking ambiguities

1. **`raw_content` = HTTP body** (§5 above). Grounded in the field's description, both worked examples, and Phase 4's own `body_of` helper. SD-019 pre-cleared the consequence.
2. **Route discovery = index links filtered through hardcoded patterns** (§3 above). Grounded in §3's *"any URL that did not come from the hardcoded structure is not visited"* and its off-host rule.

Neither created a decision record. Both are reversible in one function.

## 14. Remaining debt

Unchanged from the preflight, none of it blocking:

1. SD-027 residuals 1 and 4 — closed by SD-028, never struck through.
2. `raw_content` wording — the contract still does not say which reading applies.
3. `SCRAPER_AGENT_SPEC.md` §3 — the two link-following sentences still read against each other.
4. Retry backoff — still unquantified in the spec.
5. `IMPLEMENTATION_PLAN.md` Phase 5 still says *"Blocked on: GOTHAMITE `docs/DATA_MODEL.md`"*, superseded by SD-025.

New, from this phase:

6. `API_CONTRACT.md` §6 criteria 5–6 and `SCRAPER_AGENT_SPEC.md` §8.9 cannot be
   fully satisfied until GOTHAMITE exists. They are marked *verified with test
   receiver* here, and should not be recorded as integrated.

---

**Phase 5 is complete on the sandbox side.** No blocker remains within this
repository's scope. The only outstanding work at this seam is GOTHAMITE's, in
GOTHAMITE's repository. No commit was made.
