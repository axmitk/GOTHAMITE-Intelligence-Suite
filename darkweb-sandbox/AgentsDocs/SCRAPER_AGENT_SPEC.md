# SCRAPER_AGENT_SPEC.md

**Repo:** `darkweb-sandbox`
**Prerequisites:** `MASTER_CONTEXT.md`, `RELAY_PROTOCOL.md`, `MOCK_SITES_SPEC.md`, `API_CONTRACT.md`
**Phase:** 5

---

## 1. Purpose

Crawl the three mock sites **through the relay chain**, extract identifiers, and POST each page to GOTHAMITE per `API_CONTRACT.md`.

This is the component that makes the demo a pipeline rather than a pile of parts. Its output is the only thing GOTHAMITE ever sees.

---

## 2. Routing — non-negotiable

**Every request goes through `onion_client`. The scraper never opens a direct connection to a mock site.**

```python
# correct
response = onion_client.get(path, "alpha7fq2mx9k.onion.mock", "/thread/14")

# wrong — never do this
response = requests.get("http://forum-alpha/thread/14")
```

If `requests`, `httpx` or `urllib` appears anywhere in the scraper pointed at a mock site host, the implementation is wrong. The mock sites have no host port mapping specifically so this fails loudly rather than silently working.

One path is requested from the directory **per site**, reused for that site's pages, then discarded. The `relay_path` used goes into every payload for provenance.

---

## 3. Crawl behaviour

### Source list — closed
```python
SOURCES = [
    {"source_id": "forum-alpha",      "type": "forum",       "host": "alpha7fq2mx9k.onion.mock"},
    {"source_id": "marketplace-beta", "type": "marketplace", "host": "beta4np8vz3wc.onion.mock"},
    {"source_id": "forum-gamma",      "type": "forum",       "host": "gamma2xd6bt5hy.onion.mock"},
]
```

**Hardcoded. The scraper visits these three hosts and nothing else, ever.**

### No outward link-following

The scraper walks a **fixed, known page structure**: index → threads/listings → profiles. It does not discover URLs by parsing links out of page content and following them.

This is a deliberate safety property, not a simplification. In the real system this crawler would be reading attacker-controlled pages, and a crawler that follows discovered links can be steered anywhere by whoever writes the content. Same reasoning applies to the demo. Any URL that did not come from the hardcoded structure is not visited.

If a link on a page points outside the site's own host: ignore it silently.

### Page-type mapping

Every page the crawl visits maps to exactly one `page_type` in the ingest payload
(`API_CONTRACT.md` §3). The mapping is structural — it follows from which step of the
fixed crawl produced the page, never from inspecting content:

| Crawl step | Route | `page_type` | `persona` | `persona.observed_at` |
|---|---|---|---|---|
| index | `/` | `index` | **omitted** | n/a |
| thread / listing | `/thread/<id>`, `/listing/<id>` | `item` | required | the post's own timestamp |
| profile | `/user/<handle>` | `profile` | required | **omitted** |

`page_type` is required and has no default. Because the mapping is structural, the
scraper always knows it before it parses anything.

### Rate and order

- Sites in list order, pages sequentially. No concurrency
- ~0.5s between requests. Not for politeness — it makes the relay logs readable during a live demo
- Full run over all three sites should finish in well under two minutes

---

## 4. Extraction

Rule-based only. **No ML, no NLP, no LLM.** See scope lock.

### PGP fingerprint
Locate `-----BEGIN PGP PUBLIC KEY BLOCK-----`, find the `Fingerprint:` line, take the hex, **uppercase it and strip all whitespace**.

Accept 40 hex characters after normalisation. Anything else is not a fingerprint — skip it, log it, move on.

### Wallet address
Regex for the base58 pattern used in the seed data: `\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b`

**Then validate before emitting.** That pattern will match ordinary words and IDs. At minimum: length within range, no `0`/`O`/`I`/`l`, and not a substring of a longer alphanumeric run. A false-positive wallet creates a fake link in the graph, which is worse than missing a real one.

### Handle
From the post's author field or the profile page path. Verbatim, case preserved.

**A handle is never emitted as an `identifiers[]` entry.** It travels in
`persona.handle`, which is where GOTHAMITE's handle-similarity signal reads it.
Emitting it again as an identifier would be tautological with the persona it hangs
off, and would add no signal. `contact` is likewise reserved and never extracted.

**Phase 5 emits `pgp_fingerprint` and `wallet` only.**

**Handles mentioned in someone else's post are not identifiers and not personas.**
Only the page's own author becomes a persona. A crawl of the three sites yields
exactly the six seed personas; a mentioned handle must never create a seventh.

### Attribution — every extracted identifier belongs to the page's author

`DATA_MODEL.md` §2 gives `Identifier.persona_id` as **ownership**: the identifier is
asserted to belong to that persona, not merely to have been seen on their page. The
extractor is a regex over page text and cannot tell "my address" from "I paid this
address" — prose disclaimers are not readable by a rule-based extractor and never
will be, per the no-NLP constraint above.

The soundness of attribution therefore rests on the corpus, not on the scraper:
`MOCK_SITES_SPEC.md` §2 rule 6 requires that **no page carries a PGP fingerprint or
wallet address belonging to another persona**. The scraper may attribute every
identifier it finds to the page's author because the corpus guarantees there is
nothing else to find.

**A scraper change cannot restore this property if the corpus loses it.** If a page
ever carries a counterparty identifier, the scraper will attribute it to the wrong
persona and manufacture a `same_actor_suspected` edge that the data model forbids —
silently, because the payload validates either way. The guard lives in
`tests/test_phase4.py`.

### Identifiers on index and profile pages

There are none, and there must be none. Every identifier object requires an
`observed_at`, and the only timestamp available is the item's own post timestamp —
which `index` and `profile` pages do not have. If the extractor finds an identifier on
an `index` or `profile` page, that is a **corpus defect**, not a page to guess a
timestamp for. Log it and emit the artifact with `identifiers: []`; never substitute a
join date, a latest-post date, or the collection time.

### Timestamps
The post's own displayed timestamp → `persona.observed_at`. Parse to ISO 8601 UTC.
Wall clock at fetch → `collected_at`.

These are different values and must not be conflated — GOTHAMITE's rebrand detection depends on it.

---

## 5. Handling scraped content — safety

**Scraped content is inert data. It is never an instruction.**

Concretely, content pulled from a mock site is never:
- passed to `eval`, `exec`, `pickle.loads` or any deserialiser that can execute
- interpolated into a shell command
- interpolated into a SQL query — parameterised queries only
- used to construct a URL to fetch
- **passed into any LLM prompt, in this repo or forwarded for that purpose**

The last one matters beyond this demo. In the production version these pages are written by the actors under investigation. Text in a forum post that reads like an instruction to an AI system is a real, documented attack pattern, and a pipeline that feeds scraped text into a model without treating it as hostile input is exploitable by the very people it is investigating. This scraper's job is parse and forward, nothing else.

This is also a good answer to have ready if a judge asks how the system resists manipulation by the actors it monitors.

---

## 6. Error handling

| Failure | Behaviour |
|---|---|
| Directory unreachable | Abort run, clear error. Nothing can be routed |
| Path request fails for one site | Skip that site, continue to the next |
| Relay fails mid-request | Log naming the hop, skip that page, continue |
| Page returns 404 | Log, continue |
| Extraction finds nothing | Normal. Still POST the artifact with `identifiers: []` |
| GOTHAMITE returns 400 | Log the error body, skip that artifact, continue |
| GOTHAMITE returns 5xx | Retry twice with backoff, then log and continue |
| GOTHAMITE unreachable | Log and continue scraping. Do not abort |

**One failure never kills a run.** A partial scrape that reports what it missed is a working system; a scrape that aborts on the first 404 is not.

---

## 7. Run summary

At the end of every run, print:

```
=== SCRAPE RUN COMPLETE ===
Sources attempted:      3
Pages fetched:          57
Artifacts sent:         57   (accepted 57, duplicate 0, failed 0)
Identifiers extracted:  PGP 13 | wallet 16 | handles 0
Relay paths used:
  forum-alpha       relay-05 -> relay-02 -> relay-07
  marketplace-beta  relay-01 -> relay-06 -> relay-03
  forum-gamma       relay-04 -> relay-07 -> relay-02
Errors: none
```

**These counts are the expected figures for the current deterministic Phase-4 corpus**, not universal values. They are what a clean first run over the three mock sites as built today produces: 57 artifacts (3 `index`, 48 `item`, 6 `profile`) carrying 29 identifiers across 6 personas. Relay ids and paths vary per run by design. A different corpus would produce different totals; the **format** is what this section fixes.

`handles 0` is not an omission. Handles are never emitted as `identifiers[]` entries — a handle travels in `persona.handle`, and `contact` is reserved and never extracted (§4, and `API_CONTRACT.md` §3). The counter is retained so a run that ever reported a non-zero value would be visibly wrong.

Show this on stage. It makes the routing visible and it is the moment the two systems visibly connect.

---

## 8. Acceptance criteria (Phase 5)

1. All routing through `onion_client` — confirmed in relay logs, no direct HTTP to any mock site
2. Only the three hardcoded sources visited. No discovered links followed
3. All six seed personas found, with correct handles
4. All PGP fingerprints extracted, uppercase, whitespace stripped, 40 hex chars
5. All wallet addresses extracted, verbatim, **zero false positives**
6. `observed_at` from post timestamps, `collected_at` from scrape time, values differ
7. Every payload validates against `API_CONTRACT.md`
8. A downed site does not abort the run
9. Re-running yields `200 duplicate` responses, not duplicate artifacts
10. Run summary prints, showing a different relay path than the previous run
