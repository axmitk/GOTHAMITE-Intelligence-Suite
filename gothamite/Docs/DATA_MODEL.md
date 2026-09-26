# DATA_MODEL.md

**Repo:** `GOTHAMITE`
**Authority:** This file is the single source of truth for the schema and the seed data. `darkweb-sandbox/Agent_Docs/API_CONTRACT.md` and `MOCK_SITES_SPEC.md` must conform to it. Where they disagree, this file wins.

---

## 1. Design rules

1. **Observations are never overwritten.** New scrapes append. History is queryable.
2. **Every derived claim traces to an artifact.** If a relationship cannot name the evidence that produced it, it does not get created.
3. **Observed-at and collected-at are different fields.** When something happened is not when we saw it.
4. **Confidence is a score, not a probability.** We have no calibration ground truth. Never render it as a percentage likelihood of real-world identity.
5. **Identifiers are pseudonymous.** A shared wallet is evidence of a link between personas. It is not an identity.

---

## 2. Entities

### Source
| Field | Type | Notes |
|---|---|---|
| `source_id` | str | `forum-alpha`, `marketplace-beta`, `forum-gamma` |
| `type` | enum | `forum` \| `marketplace` |
| `reliability` | enum | `high` \| `medium` \| `low` |
| `last_scan` | datetime | |
| `status` | enum | `up` \| `down` |

### Artifact
Raw scraped content, stored verbatim. The evidence locker.

| Field | Type | Notes |
|---|---|---|
| `artifact_id` | uuid | |
| `source_id` | str | FK → Source |
| `url` | str | mock-site path |
| `raw_content` | text | as fetched, unmodified |
| `content_hash` | str | sha256 of `raw_content` |
| `collected_at` | datetime | |
| `relay_path` | list[str] | relay ids used, for provenance |

### Persona
A handle on one specific site. **A persona is per-site.** The same human on two sites is two personas.

| Field | Type | Notes |
|---|---|---|
| `persona_id` | uuid | |
| `handle` | str | |
| `source_id` | str | FK → Source |
| `first_seen` | datetime | earliest observed post |
| `last_seen` | datetime | |
| `post_count` | int | |

Unique on (`handle`, `source_id`).

### Identifier
| Field | Type | Notes |
|---|---|---|
| `identifier_id` | uuid | |
| `type` | enum | `pgp_fingerprint` \| `wallet` \| `handle` \| `contact` |
| `value` | str | normalised: PGP uppercase no spaces, wallet as-is |
| `persona_id` | uuid | FK → Persona |
| `artifact_id` | uuid | FK → Artifact — where it was seen |
| `observed_at` | datetime | |

### Relationship
An inferred link between two personas.

| Field | Type | Notes |
|---|---|---|
| `relationship_id` | uuid | |
| `from_persona_id` | uuid | |
| `to_persona_id` | uuid | |
| `type` | enum | `same_actor_suspected` \| `transacted_with` \| `trusts` |
| `score` | float | 0.0–1.0 |
| `status` | enum | `proposed` \| `confirmed` \| `rejected` — analyst sets |
| `created_at` | datetime | |

### Evidence
Why a relationship exists. One row per supporting or contradicting signal.

| Field | Type | Notes |
|---|---|---|
| `evidence_id` | uuid | |
| `relationship_id` | uuid | FK |
| `signal_type` | enum | `shared_pgp` \| `shared_wallet` \| `handle_similarity` \| `temporal_succession` \| `activity_overlap_conflict` |
| `direction` | enum | `supporting` \| `contradicting` |
| `weight` | float | contribution to score |
| `artifact_id` | uuid | the artifact that proves it |
| `note` | str | human-readable |

### Actor
A cluster of personas an analyst has confirmed as one entity.

| Field | Type | Notes |
|---|---|---|
| `actor_id` | uuid | |
| `label` | str | analyst-assigned |
| `persona_ids` | list[uuid] | |
| `confidence` | enum | `low` \| `medium` \| `high` |
| `created_at` / `updated_at` | datetime | |

---

## 3. Scoring

Exact-match signals only. **No fuzzy matching, no ML, no stylometry** — see `MASTER_CONTEXT.md` scope lock.

| Signal | Weight | Direction |
|---|---|---|
| Identical PGP fingerprint | **0.70** | supporting |
| Identical wallet address | **0.45** | supporting |
| Temporal succession (A last_seen < B first_seen, gap < 45 days) | **0.15** | supporting |
| Handle similarity (Levenshtein ≤ 2) | **0.05** | supporting |
| Activity window overlap while claimed same actor | **−0.30** | contradicting |

`score = clamp(sum(weights), 0.0, 0.95)`

**Cap at 0.95.** Never output 1.0. Certainty is not something this system can establish.

Bands for display: `< 0.30` weak, `0.30–0.59` moderate, `0.60–0.79` strong, `≥ 0.80` very strong.

A relationship is created when `score ≥ 0.30`. Below that, no edge.

---

## 4. Seed data

**All values below are invented.** No real PGP key, wallet address, handle, or person is referenced. Wallet strings are format-plausible so extraction regex is exercised, but do not correspond to real addresses. Do not replace any of these with values copied from anywhere real.

Content must be **deterministic and hardcoded**. No random generation — the demo depends on knowing exactly what should link.

### Actor A — strong PGP link (the headline result)

| | Persona A1 | Persona A2 |
|---|---|---|
| handle | `nightjar` | `n1ghtjar_` |
| site | forum-alpha | marketplace-beta |
| active | 2026-01-08 → 2026-08-20 | 2026-02-14 → 2026-08-22 |
| PGP | `9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D` | **same** |
| wallet | `1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6` | **same** |

Expected: PGP 0.70 + wallet 0.45 → capped **0.95, very strong**.

### Actor B — rebrand / migration

| | Persona B1 | Persona B2 |
|---|---|---|
| handle | `quillfeather` | `quill_v2` |
| site | forum-alpha | forum-gamma |
| active | 2026-01-20 → **2026-04-02** | **2026-04-19** → 2026-08-18 |
| PGP | `3B77E1A9C4D28F60B5E3A17C9D42F8E06B1A5C93` | `E4C08B21F7A6D93E5C1B84027FA36D9E1C05B872` (rotated — different) |
| wallet | `1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o` | **same** |

Expected: wallet 0.45 + temporal succession 0.15 (17-day gap) → **0.60, strong**. No PGP match — this is the case that shows the system catching a rebrand without a key match.

### Actor C — decoy (must NOT link)

| | Persona C1 |
|---|---|
| handle | `nightjarr` — one character from `nightjar` |
| site | forum-gamma |
| active | 2026-03-01 → 2026-08-21 — **overlaps A1** |
| PGP | `7D19F4C8B302A6E5D91C7B48F0A2E63D5C81B94F` |
| wallet | `1Qs2fT8yWn5LpX3mK9vGdC7bJ4hRzAeN1u` |

Expected: handle similarity 0.05 + activity overlap conflict −0.30 → **below threshold, no edge**.

This is the most important seed case. It proves the system resists the obvious false positive. Demo it explicitly.

### Actor D — transaction edge, not an identity link

| | Persona D1 |
|---|---|
| handle | `bellwether` |
| site | marketplace-beta |
| active | 2026-02-01 → 2026-08-19 |
| PGP | `A50C3E97B14D6F82093C5A7E1BD48F620E93C7A1` |
| wallet | `1Zr6bN4qJm8VhT2xD5cWfP9sLgY3kEuA7i` |

Transacts with A2's wallet. Creates a `transacted_with` edge only. **Must not produce `same_actor_suspected`.** Shows the system distinguishing interaction from identity.

### Summary of expected output

| Link | Type | Score | Band |
|---|---|---|---|
| A1 ↔ A2 | same_actor_suspected | 0.95 | very strong |
| B1 → B2 | same_actor_suspected | 0.60 | strong |
| C1 ↔ A1 | **none** | 0.00 | below threshold |
| D1 → A2 | transacted_with | n/a | n/a |

Four personas linked, one correctly rejected, one interaction edge. That is the demo.

---

## 5. Content volume

Per persona: **8–15 posts or listings**. Enough that timelines and activity windows look real; small enough to hand-write.

Each post carries: handle, timestamp, body text, and where specified, a PGP block or wallet address inline. Identifiers must appear in **post content**, not in structured metadata — the scraper's extraction is meant to be exercised, not handed the answer.

Timestamps must be spread across each persona's stated active window, with B1's final post before 2026-04-02 and B2's first after 2026-04-19.
