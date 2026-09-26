# MOCK_SITES_SPEC.md

**Repo:** `darkweb-sandbox`
**Prerequisites:** `MASTER_CONTEXT.md`, GOTHAMITE `docs/DATA_MODEL.md`
**Phase:** 4 — **parallelisable, no dependency on the relay work. Start immediately if a second person is free.**

---

## 1. Purpose

Three synthetic sites that act as the hidden services the scraper collects from. They exist to carry the seed personas defined in `DATA_MODEL.md` §4.

**This is content design as much as it is code.** If the planted links are wrong or inconsistent, GOTHAMITE finds nothing and there is no demo. Get the data right before making it look good.

---

## 2. Hard content rules

1. **Entirely invented.** No content copied, adapted or paraphrased from any real forum, marketplace, archive or dataset. Not from Robin, not from published dark web corpora, not from anywhere.
2. **No real illegal-goods listings, no instructional content, no actual illicit material.** Listings name generic placeholder items — `dataset bundle`, `access credentials pack`, `archive dump` — with no detail, no instructions, nothing operational. This is set dressing for a correlation demo, not a working marketplace.
3. **Deterministic.** Hardcoded content. No random generation, no faker library, no timestamps computed at runtime. The demo depends on knowing exactly what is there.
4. **Identifiers appear in post bodies**, not in structured metadata or HTML attributes. The scraper's extraction must do real work.
5. **Values exactly as written in `DATA_MODEL.md` §4.** Copy them character by character. A single wrong character in a PGP fingerprint silently breaks the headline link.
6. **No page carries a PGP fingerprint or wallet address belonging to another persona.** Every emitted PGP fingerprint and wallet address belongs to that page's author. This is what makes attribution sound (`DATA_MODEL.md` §2, Identifier): the scraper's extractor is a regex and cannot tell "my address" from "I paid this address", so the guarantee has to live here. A counterparty identifier on a page produces a `same_actor_suspected` edge the data model forbids, and it does so silently — the payload validates either way. Enforced by `tests/test_phase4.py::test_no_page_carries_another_personas_identifier`.
7. **Index and profile pages carry no extractable identifier.** No PGP block, no wallet address. Every identifier object in the ingest payload requires an `observed_at`, and the only timestamp available is an item's own post timestamp, which these two page types do not have (`API_CONTRACT.md` §3). An identifier on an index or profile page cannot be emitted in conformance. This is a rule, not an accident of how the pages are currently written.

---

## 3. The three sites

| Site | Type | Personas hosted |
|---|---|---|
| `forum-alpha` | forum | `nightjar` (A1), `quillfeather` (B1) |
| `marketplace-beta` | marketplace | `n1ghtjar_` (A2), `bellwether` (D1) |
| `forum-gamma` | forum | `quill_v2` (B2), `nightjarr` (C1) |

Each is a small Flask (or equivalent) app in its own container, on the internal Docker network only. **No host port mapping** — they must be unreachable except through the relay chain. That is verifiable and worth verifying: `curl` from the host should fail.

---

## 4. Page structure

Keep it minimal. Three page types total.

### Index — `/`
Site name, a one-line description, list of threads or listings with author handle and date.

### Thread / listing — `/thread/<id>` or `/listing/<id>`
The page that matters. Contains:
- author handle
- timestamp (ISO 8601, matching the persona's active window)
- body text — 40–120 words
- where specified, an inline PGP block or wallet address

### Profile — `/user/<handle>`
Handle, join date, post count, and the persona's posts. Gives the scraper a per-persona entry point.

### PGP blocks
Render as a realistic-looking block containing the fingerprint from `DATA_MODEL.md`:

```
-----BEGIN PGP PUBLIC KEY BLOCK-----
Fingerprint: 9F2A 4C81 D3E5 B706 9A1C 4F82 D6E3 0B57 A4C1 9E8D
[synthetic key material — not a real key]
-----END PGP PUBLIC KEY BLOCK-----
```

Fingerprints may be displayed space-separated for realism. The scraper normalises to uppercase, no spaces.

**Do not generate real PGP keys.** Placeholder text inside the block is correct and sufficient.

### Wallet addresses
Inline in body text, naturally: `payment to 1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6 only`.

---

## 5. Content volume

Per `DATA_MODEL.md` §5 — **8–15 posts per persona**, timestamps spread across that persona's active window.

Critical placements:
- **A1 / A2:** PGP block on at least 2 posts each, wallet on at least 2 each. Redundancy protects against a parser miss on one page
- **B1:** last post `2026-04-02T11:26:00Z` — the closing bound of its active window, not before it. Wallet on ≥ 2 posts
- **B2:** first post `2026-04-19T10:12:00Z` — the opening bound of its active window, not after it. Same wallet as B1 on ≥ 2 posts. Its own different PGP visible

  *Corrected per SD-018.* These bullets previously read "strictly before `2026-04-02`" and "strictly after `2026-04-19`", which forced a gap of at least 19 days against `DATA_MODEL.md` §4's stated 17. The gap is a scoring input — B1 → B2's 0.60 is derived from wallet 0.45 plus temporal succession 0.15 at 17 days — so the data model's dates govern. The intent of the original wording is preserved: B1 posts nowhere after its window ends, B2 nowhere before its window begins.
- **C1:** posts spread across `2026-03-01 → 2026-08-21`, deliberately overlapping A1. Own PGP and wallet, sharing nothing with anyone
- **D1:** the **co-location negative control**. Hosted on `marketplace-beta` alongside A2, with an active window that overlaps A2's, and **sharing no identifier with any persona**. Own PGP and own wallet on ≥ 2 posts each — the identifiers are what make the negative result meaningful, since a persona carrying none would demonstrate nothing

  *Replaced per SD-027 and its R2 addendum.* This bullet previously required *"at least one post referencing A2's wallet as a counterparty, phrased as a transaction, not as its own address"*. That post satisfied the letter of the spec and still produced a false `same_actor_suspected` edge at 0.45, because a rule-based extractor reads the address but not the disclaimer around it. The counterparty reference is removed from the corpus and D1's purpose is now the opposite: same venue, overlapping period, nothing shared, therefore **no edge**

### Writing the body text

Keep it mundane — vendor-to-buyer logistics chatter, availability, payment terms, reputation talk. No operational or instructional content of any kind.

Do **not** write text intended to make personas sound stylistically similar. Stylometry is cut from scope; effort spent on writing-style hints is wasted and creates a temptation to claim a capability that does not exist.

---

## 6. Addressing

Each site gets a mock onion-style address for demo legibility, mapped directly to its container:

| Address | Container |
|---|---|
| `alpha7fq2mx9k.onion.mock` | `forum-alpha` |
| `beta4np8vz3wc.onion.mock` | `marketplace-beta` |
| `gamma2xd6bt5hy.onion.mock` | `forum-gamma` |

**The `.onion.mock` suffix is mandatory.** These are not real onion addresses and must never be presentable as such. Direct container mapping, no descriptor resolution — see scope lock.

---

## 7. Acceptance criteria (Phase 4)

1. All three sites reachable through a full relay path
2. None reachable directly from the host — `curl` from the host fails
3. Every persona from `DATA_MODEL.md` §4 present, with the exact stated handle and active window
4. PGP fingerprints and wallet addresses match `DATA_MODEL.md` character for character
5. A1/A2 share both PGP and wallet; B1/B2 share wallet only; C1 shares nothing
6. B1's last post precedes B2's first post by roughly 17 days
7. Content is stable across restarts — identical bytes every time
8. No real-world content, no operational detail, anywhere on any site
