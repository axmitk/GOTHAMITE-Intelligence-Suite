# API_CONTRACT.md

**Repo:** `darkweb-sandbox`
**Conforms to:** This file is authoritative for the sandbox ↔ GOTHAMITE wire format. Per SD-014, neither repository owns the other's internal model; they must remain compatible at this boundary. A disagreement between this contract and either side's internal model is a change request against this file, not an automatic override of it. Amendment by agreement once a GOTHAMITE counterparty exists.
**Phase:** 5

---

## 1. The seam

This is the **only** point of contact between the two repos.

```
darkweb-sandbox/scraper/scraper_agent.py
        │
        │  POST /api/v1/ingest
        ▼
GOTHAMITE backend
```

Neither repo imports code from the other. Ever. This HTTP contract is the entire interface.

---

## 2. Endpoint

```
POST http://gothamite-backend:8000/api/v1/ingest
Content-Type: application/json
```

One request per **artifact** — one scraped page. Not batched. If a page yields three identifiers, they go in that page's single request.

Batching is a valid future optimisation and explicitly not worth doing now.

---

## 3. Request body

```json
{
  "source_id": "forum-alpha",
  "source_type": "forum",
  "page_type": "item",
  "url": "http://alpha7fq2mx9k.onion.mock/thread/14",
  "collected_at": "2026-09-06T14:22:31Z",
  "relay_path": ["relay-05", "relay-02", "relay-07"],
  "raw_content": "<full page HTML, verbatim, unmodified>",
  "content_hash": "sha256:4f3a...",
  "persona": {
    "handle": "nightjar",
    "observed_at": "2026-03-11T09:14:00Z"
  },
  "identifiers": [
    {
      "type": "pgp_fingerprint",
      "value": "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D",
      "observed_at": "2026-03-11T09:14:00Z"
    },
    {
      "type": "wallet",
      "value": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
      "observed_at": "2026-03-11T09:14:00Z"
    }
  ]
}
```

### Field rules

| Field | Required | Notes |
|---|---|---|
| `source_id` | yes | Exactly `forum-alpha` \| `marketplace-beta` \| `forum-gamma` |
| `source_type` | yes | `forum` \| `marketplace` |
| `page_type` | yes | Exactly `index` \| `item` \| `profile`. **No default** — see below |
| `url` | yes | Canonical absolute HTTP URL, `http://<mock-host>/<path>` — see below |
| `collected_at` | yes | When scraped. ISO 8601, UTC, `Z` suffix |
| `relay_path` | yes | Ordered relay ids used. Provenance — proves collection went through the chain |
| `raw_content` | yes | Verbatim page content. **Not cleaned, not stripped, not truncated** |
| `content_hash` | yes | `sha256:` + hex digest of `raw_content` as UTF-8 bytes |
| `persona` | depends on `page_type` | Omitted entirely for `index` — see the matrix below |
| `persona.handle` | with `persona` | As displayed on the page |
| `persona.observed_at` | `item` only | The post's own timestamp — **not** the scrape time |
| `identifiers` | yes | May be `[]`. Absent identifiers is normal and fine |
| `identifiers[].observed_at` | yes, per object | Required on **every** identifier object that exists. No surrogate — see below |

### `page_type` — required, closed, no default

| `page_type` | Represents | `persona` | `persona.handle` | `persona.observed_at` |
|---|---|---|---|---|
| `index` | a listing / index / navigation page | **omitted** | n/a | n/a |
| `item` | a thread, listing or post with one author | required | required | required — the item's own post timestamp |
| `profile` | a single persona's profile page | required | required | **omitted** |

Allowed values are exactly `index`, `item` and `profile`. **There is no default.** A
validator must not infer `item`, or anything else, from a missing field; a missing or
unsupported `page_type` is rejected.

For `profile`, the join date **must not** be substituted for `observed_at`, and
neither may the timestamp of the latest post shown on the profile.

The purpose of the field is to make the *absence* of persona information explicit
rather than leaving GOTHAMITE to infer it. An artifact with no persona and no
discriminator is ambiguous between "a page with no author" and "a page whose author
the scraper failed to extract" — two conditions that need opposite handling.

### `identifiers[].observed_at` — required, never substituted

`observed_at` is required on **every identifier object that exists**. It is not
relaxed, not made conditional on `page_type`, and not defaulted.

If `identifiers` is `[]`, no identifier timestamp is required — an empty array is
normal. But an identifier that exists without a timestamp is invalid, and its
`observed_at` must **not** be derived from a profile's "Joined" date, the latest post
shown on a profile, the collection time, or any other surrogate.

**A consequence worth stating, because it constrains the sites and not just the
scraper:** the only timestamp available for an identifier is the timestamp of the item
it appeared on. `index` and `profile` pages have none. Therefore **an `index` or
`profile` page must carry no extractable identifier** — if one appeared there, the
artifact could not be emitted in conformance. `MOCK_SITES_SPEC.md` §2 rule 7 states
this as a normative constraint on the corpus rather than leaving it to how the pages
happen to be written.

### `url` — canonical absolute HTTP URL

```
http://<mock-host>/<path>
```

1. The scheme is **required**, and is **`http`** for the current simulated sandbox.
2. The `.onion.mock` host is **required**.
3. A route path is **required**. The index page is therefore
   `http://alpha7fq2mx9k.onion.mock/` **with the trailing slash** — `.../` and `...`
   are different strings, and three artifacts per run depend on it.
4. A bare `/path` is invalid. A host-and-path value without a scheme is invalid.
5. **No HTTPS** unless the sandbox actually implements it.
6. This field is an **ingestion-payload field only**. `RELAY_PROTOCOL.md` §5.1 fixes
   the wire layer at four fields and the relay chain never sees this string.
7. No query-string or fragment semantics are defined. Duplicate detection remains
   `content_hash` + `source_id`, per §4 — not `url`.

### Which identifier types are actually emitted

Phase 5 emits **`pgp_fingerprint` and `wallet` only**.

`handle` and `contact` are **reserved**: they remain valid `Identifier.type` values in
the data model, but the scraper never sends them. A validator built from the enum will
accept a `handle` identifier that no producer emits — that is deliberate, not an
oversight, and it must not be read as evidence that handles are emitted.

A persona's handle travels in `persona.handle`, where correlation reads it. Emitting
it a second time as an identifier would add no signal: it would be tautological with
the persona it is attached to. Handles **mentioned** in another persona's content are
not that persona's identifiers and are out of scope entirely.

### `observed_at` vs `collected_at`

The distinction is load-bearing, not pedantry. `observed_at` is when the thing happened on the site. `collected_at` is when we saw it. GOTHAMITE's temporal succession scoring — the signal that catches the B1→B2 rebrand — reads `observed_at`. Getting these backwards silently breaks that link.

### Identifier normalisation — scraper's job, before sending

| Type | Normalisation |
|---|---|
| `pgp_fingerprint` | Uppercase, all whitespace removed. `9F2A 4C81 …` → `9F2A4C81…` |
| `wallet` | Verbatim. Case-sensitive, never altered |
| `handle` | Verbatim. Case-sensitive |

---

## 4. Responses

**`202 Accepted`**
```json
{ "accepted": true, "artifact_id": "a7f3e2c1-...", "identifiers_stored": 2 }
```

**`200 OK` — duplicate**
```json
{ "accepted": false, "reason": "duplicate_content_hash", "artifact_id": "a7f3e2c1-..." }
```
Same `content_hash` from the same `source_id` already exists. Not an error — expected on re-scrape. The scraper logs and continues.

**`400 Bad Request`**
```json
{ "accepted": false, "errors": ["identifiers[0].value: invalid pgp fingerprint format"] }
```
Scraper logs the full error, skips that artifact, **continues with the rest of the run**. One bad page never kills a scrape.

**`5xx`** — retry twice with backoff, then log and continue.

---

## 5. Rules for GOTHAMITE's side

1. **Store `raw_content` before parsing anything.** The artifact is the evidence; it gets persisted even if downstream extraction fails
2. **Treat every field as untrusted input.** This payload originates from scraped content. Sanitise before rendering anywhere in the dashboard. Never interpolate it into a query, a shell command, or an LLM prompt
3. **Never create a Relationship at ingest time.** Ingest stores personas, identifiers and artifacts. Correlation is a separate pass over stored data. Keeping these apart is what makes the pipeline re-runnable and the scoring reproducible
4. **Verify `content_hash`** against the received `raw_content` and reject on mismatch

---

## 6. Acceptance criteria

1. Scraper POSTs a valid payload for every page from all three sites
2. `relay_path` is populated and matches what the relay logs show
3. `observed_at` reflects post timestamps, `collected_at` reflects scrape time, and they differ
4. PGP fingerprints arrive uppercase with no spaces
5. Re-running the scraper produces `200 duplicate` responses, not duplicate artifacts
6. A deliberately malformed payload returns `400` and the scrape run continues
