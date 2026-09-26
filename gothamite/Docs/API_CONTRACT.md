# API_CONTRACT.md

**Repo:** `darkweb-sandbox`
**Conforms to:** GOTHAMITE `docs/DATA_MODEL.md` — that file is authoritative. If this contract and the data model disagree, the data model wins and this file gets corrected.
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
  "url": "alpha7fq2mx9k.onion.mock/thread/14",
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
| `url` | yes | Including the `.onion.mock` host |
| `collected_at` | yes | When scraped. ISO 8601, UTC, `Z` suffix |
| `relay_path` | yes | Ordered relay ids used. Provenance — proves collection went through the chain |
| `raw_content` | yes | Verbatim page content. **Not cleaned, not stripped, not truncated** |
| `content_hash` | yes | `sha256:` + hex digest of `raw_content` as UTF-8 bytes |
| `persona.handle` | yes | As displayed on the page |
| `persona.observed_at` | yes | The post's own timestamp — **not** the scrape time |
| `identifiers` | yes | May be `[]`. Absent identifiers is normal and fine |

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
