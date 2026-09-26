# OPEN-4 — Cross-Repository Change List

**Date:** 2026-09-07
**Status:** **PROPOSAL. NOTHING IMPLEMENTED.** See `SPEC_DECISIONS.md` SD-021.
**Updated 2026-09-07** with **SD-021.1** (`page_type` required, closed enum, no
default) and **SD-021.2** (`identifiers[].observed_at` required for every
identifier that exists, no surrogate timestamps). Both are **proposed**, on the
same footing as the rest of SD-021. **OPEN-4 remains open.**

**Project-state clarification, 2026-09-07 — see §0.** There is currently no
GOTHAMITE implementation available for compatibility review. Everything in §3
below is a **specification of required behaviour for a future ingestion layer**,
not a diff against inspected code.

This document itemises what would have to change if the proposed `page_type`
discriminator is agreed. It changes nothing itself. `API_CONTRACT.md`,
`SCRAPER_AGENT_SPEC.md`, the mock sites and all implementation files are
untouched, and OPEN-4 remains open.

The change spans two repositories. Per SD-014, `darkweb-sandbox` owns the
simulated ground truth and GOTHAMITE owns its ingestion representation; the two
meet at `API_CONTRACT.md`. `page_type` moves that boundary in both directions, so
neither side can adopt it alone.

---

## 0. Project state — no GOTHAMITE implementation exists

**Recorded 2026-09-07.** A GOTHAMITE compatibility review was requested and could
not be performed. No GOTHAMITE repository is present in this workspace, in any
sibling directory, as a git remote or submodule, or in the owning GitHub account.
No ingestion endpoint, request schema, validation rules, unknown-field behaviour,
persona upsert, timeline logic, identifier validation or ingest test suite was
found.

**Nothing in this document assumes otherwise.** No GOTHAMITE repository, schema,
validator or implementation is invented here. §3 below is written as a
**specification of required behaviour** for whatever ingestion layer is built
first — it is not, and must not be read as, a review of existing code.

### What "GOTHAMITE agreement" can currently mean

Not implementation compatibility approval — there is nothing to be compatible
with. Only **contract approval**: a decision to freeze `API_CONTRACT.md` with
`page_type` in it. SD-021, SD-021.1 and SD-021.2 stay **PROPOSED and NOT IN
FORCE** until that freeze happens.

### Three things kept distinct

| | Asserts | State |
|---|---|---|
| **Proposal correctness** | The sandbox-side reasoning is sound | Argued; reviewed sandbox-side only |
| **Contract approval** | `API_CONTRACT.md` amended and frozen | **Not given** — the file is unchanged |
| **Implementation compatibility** | An ingestion layer accepts all three shapes | **Not assessable** — none exists |

### Intended architecture if no pre-existing implementation is introduced

1. **Finalise** the ingestion contract, `page_type` included.
2. **Then implement** the first GOTHAMITE ingestion layer against that frozen
   contract.
3. **No migration or compatibility rollout is required** — there is no existing
   validator to migrate.

Contingent, not settled. If a pre-existing GOTHAMITE implementation is later
introduced, the staged rollout in §3.4 becomes live again and the compatibility
review that could not be run must be run before the contract is frozen.

---

## 1. `darkweb-sandbox/AgentsDocs/API_CONTRACT.md` — §3

### 1.1 New field in the field-rules table

Insert one row:

| Field | Required | Notes |
|---|---|---|
| `page_type` | **yes** | Exactly `index` \| `item` \| `profile`. Closed enum, **no default**. Which page structure this artifact is |

**Placement matters.** It should sit next to `source_type`, not next to `persona` —
it describes the artifact, and it must be readable before a validator decides
whether `persona` is expected.

**Required, with no default (SD-021.1).** The field is mandatory and the enum is
closed. A validator must not infer a value from an absent field, and must
eventually reject both a **missing** `page_type` and an **unsupported** one.
Defaulting to `item` would be the worst available choice: it would demand a persona
that an index page cannot supply, converting a silent ambiguity into a spurious
`400`.

### 1.2 Two changed rows

Current:

| Field | Required | Notes |
|---|---|---|
| `persona.handle` | yes | As displayed on the page |
| `persona.observed_at` | yes | The post's own timestamp — **not** the scrape time |

Proposed:

| Field | Required | Notes |
|---|---|---|
| `persona` | **conditional** | Required for `item` and `profile`. **Omitted** for `index` |
| `persona.handle` | **conditional** | Required whenever `persona` is present. As displayed on the page |
| `persona.observed_at` | **conditional** | Required for `item` — the post's own timestamp. **Omitted** for `profile` |

`persona` is currently an implicit object with no row of its own; the proposal
needs one, because "the whole block is absent" is a distinct state from "a member
is absent".

### 1.3 New normative sub-section

§3 currently states the persona rules only in the table. The three-way split needs
prose, because the profile case carries two prohibitions a table cannot express:

> **Artifact page types**
>
> | `page_type` | Represents | `persona` | `persona.handle` | `persona.observed_at` |
> |---|---|---|---|---|
> | `index` | listing / index / navigation page | omitted | n/a | n/a |
> | `item` | thread, listing or post with one author | required | required | required — the item's own post timestamp |
> | `profile` | one persona's profile page | required | required | omitted |
>
> `page_type` is required. There is no default, and the three values above are the
> complete set.
>
> For `profile`, the join date **must not** be substituted for `observed_at`, and
> neither may the most-recent-post timestamp. A profile page has no single post
> timestamp; supplying an approximation would inject false timeline data into the
> temporal succession scoring described in §4.

### 1.4 `identifiers[].observed_at` — unchanged, and deliberately so (SD-021.2)

**No relaxation of this rule.** `observed_at` stays **required on every identifier
object that exists**. It is not made conditional on `page_type`, and it is not
defaulted. If `identifiers` is `[]` — already normal per §3, on every page type —
no identifier timestamp is required.

What §3 should gain is one explicit prohibition, because the absence of a stated
rule is what invites a surrogate:

> An identifier's `observed_at` is the timestamp of that observation on the page.
> It must **not** be derived from the profile "Joined" date, from the most recent
> post shown on a profile, from `collected_at`, or from any other surrogate value.

*Why this is a change to the document but not to the rule.* §4 already states that
the `observed_at` / `collected_at` distinction is load-bearing, and that temporal
succession scoring reads `observed_at`. Every surrogate listed above is a
page-scoped or collection-time value wearing an `observed_at` label — precisely the
conflation §4 warns silently breaks the B1 → B2 rebrand link. A surrogate fails
plausibly rather than loudly, which is why it is worth prohibiting by name rather
than leaving to judgement.

**The invariant this creates.** An identifier can only be emitted where a real
per-observation timestamp exists, which under SD-021's page types is `item` pages
alone. It follows that **a `profile` or `index` page must not carry an extractable
identifier** — if one did, the artifact could not be emitted in conformance,
because no permissible `observed_at` would exist for it.

The Phase-4 mock sites already satisfy this: neither index nor profile pages render
a PGP block or a wallet, so both yield `identifiers: []`. But they satisfy it as a
property of how they happen to be written, not as an asserted invariant. **No site
or test change is made now** — `mock_sites/` and both suites are untouched. §4
below names the Phase-5 test that would pin it.

### 1.5 Worked example

The §3 example is a `/thread/14` artifact — an `item`. It needs `"page_type": "item"`
adding. **Two further examples are needed**, one `index` and one `profile`, because
the example is what implementers copy, and neither of the two new shapes can be
inferred from the `item` one.

The `item` example otherwise stays valid, including its `observed_at` of
`2026-03-11T09:14:00Z`, which the Phase-4 mock sites already match exactly.

### 1.6 Error responses — §4

No structural change. The `400` example already carries a per-field error list, so
`page_type` violations fit the existing shape. Worth adding sample messages so the
rejections are legible, covering the four cases SD-021.1 and SD-021.2 create:

- `"page_type: required"` — missing
- `"page_type: must be one of index, item, profile"` — unsupported value
- `"persona: must be omitted when page_type is index"`
- `"identifiers[0].observed_at: required"`

---

## 2. `darkweb-sandbox/AgentsDocs/SCRAPER_AGENT_SPEC.md`

### 2.1 §3 — crawl behaviour

The crawl already walks index → threads/listings → profiles. What is missing is the
mapping from that structure to `page_type`, which should be stated so it is not
re-derived per implementer:

- `/` → `index`
- `/thread/<id>`, `/listing/<id>` → `item`
- `/user/<handle>` → `profile`

Since `page_type` is required with no default (SD-021.1), this mapping is total:
every fetched page must map to exactly one value before it can be POSTed.

### 2.2 §4 — extraction

The **Handle** rule currently reads: *"From the post's author field or the profile
page path."* Under the proposal it needs a third case — index pages, where no
handle is extracted at all — and should say that the multiple handles visible on an
index page are deliberately **not** collected into a persona.

The **Timestamps** rule currently maps *"the post's own displayed timestamp →
`persona.observed_at`"*. It needs to say this applies to `item` only.

A third clause is needed for identifiers under SD-021.2: an extracted identifier
takes its `observed_at` from the observation itself, and the scraper must **not**
fall back to a page-level or collection-time value when none is available. If no
per-observation timestamp exists, the identifier is not emitted.

### 2.3 §8 — acceptance criteria

- Criterion 3 (*"All six seed personas found, with correct handles"*) — should say
  **exactly** six, so a phantom persona from an index page fails rather than passes.
- Criterion 7 (*"Every payload validates against `API_CONTRACT.md`"*) — should name
  all three page types, so validation of the two new shapes is actually exercised.

### 2.4 §7 — run summary

The template shows `Pages fetched: 47` and `Artifacts sent: 47`. Under the
proposal these stay equal — index pages are still sent, just without a persona —
so **no change is required**. This is worth recording explicitly, because it is the
line that would have had to change under the "just don't POST index pages" option
that was rejected.

---

## 3. GOTHAMITE side — required behaviour, not an inspected diff

> **Read §0 first.** No GOTHAMITE implementation exists to review. What follows
> specifies what an ingestion layer must do to satisfy SD-021; it does not
> describe, and must not be taken to describe, any current code. Where this
> section says "stop treating `persona` as unconditionally required" or "no
> change", those phrase the requirement against the **contract as written today**,
> which is the only artefact that exists.

Three acceptance behaviours, as requested, plus two cross-cutting rules from
SD-021.1 and SD-021.2. All are on the ingest path of whatever layer is built.

### 3.1 Accept `page_type: index` with no `persona`

- **Validator:** stop treating `persona` as unconditionally required. Reject
  `persona` if *present* on an `index` artifact — silence there would let a
  scraper bug through unseen.
- **Persona upsert:** create **no** `Persona` row. Not a null-handled row, not a
  placeholder — none. The uniqueness constraint is (`handle`, `source_id`), so a
  null handle would either violate it or, worse, collide across sites.
- **Artifact storage:** unchanged. `DATA_MODEL.md` §2's Artifact entity has no
  persona column, so an artifact with no persona is storable as-is. §5 rule 1
  ("store `raw_content` before parsing anything") already covers it.

### 3.2 Accept `page_type: item` with `persona` + `observed_at`

- **No change.** This is today's behaviour and today's payload shape, plus one new
  field. The only requirement is that adding `page_type` does not itself trigger a
  rejection — see §3.4.

### 3.2a Validate `page_type` itself (SD-021.1)

Independent of the three per-type behaviours, the validator must:

- **reject a missing `page_type`** — no default, no inference
- **reject an unsupported value** — the enum is closed at `index`, `item`,
  `profile`

Both are eventual-state requirements, reached at step 3 of the rollout in §3.4.

### 3.2b Keep `identifiers[].observed_at` strict (SD-021.2)

- **No relaxation.** `observed_at` stays required on every identifier object, on
  every page type. It does **not** become conditional on `page_type`.
- **Do not synthesise it.** GOTHAMITE must not backfill a missing identifier
  `observed_at` from `collected_at`, from the persona, or from any page-level
  value. Reject instead — a synthesised timestamp corrupts the temporal succession
  pass silently, which is the one failure mode §4 of the contract singles out.
- `identifiers: []` remains valid and normal on all three page types.

### 3.3 Accept `page_type: profile` with `persona` but no `observed_at`

This is the case most likely to break quietly, because the block is present and
only a member is missing.

- **Validator:** `persona.observed_at` becomes conditional. Reject it if *present*
  on a `profile` artifact — that rejection is what enforces the "do not substitute
  the join date" rule at the boundary rather than by convention.
- **Persona upsert:** create or update the `Persona` row from `handle` +
  `source_id` as normal, but **do not** advance `first_seen`, `last_seen` or
  `post_count` from a profile artifact. Those fields are derived from `item`
  artifacts. A profile page asserts that a persona exists; it does not assert when
  it posted.
- **Correlation:** `API_CONTRACT.md` §5 rule 3 already forbids creating
  relationships at ingest time, so nothing changes there. But the temporal
  succession pass must not treat a profile-sourced persona as having no activity —
  it should read `observed_at` from `item` artifacts only.

### 3.4 Cross-cutting: unknown-field handling — **does not currently apply**

**Per §0, this risk is dormant.** It exists only where a *deployed* validator would
meet a required new field. No ingestion layer exists, so there is nothing to
migrate and **no staged rollout is required**. If the contract is frozen before the
first implementation is written, `page_type` is simply part of it from day one.

The rest of this sub-section is retained because it **becomes live again** the
moment a pre-existing GOTHAMITE implementation is introduced.

---

*Conditional — applies only if an ingestion layer already exists when SD-021 is
adopted.*

SD-021.1 settles that `page_type` is required with no default, so the
optional-field escape route is closed by decision rather than left open. If such a
validator rejects unknown fields, adding a required `page_type` makes it `400`
**every** artifact until it ships an update. `SCRAPER_AGENT_SPEC.md` §6 instructs
the scraper to log a 400 and continue — so an entire run would be lost while the
run summary still printed a clean "Errors: none" shape with a nonzero `failed`
count.

That would argue for a deployment order rather than a simultaneous switch:

1. The ingestion layer accepts and ignores `page_type`, and relaxes `persona` to
   conditional
2. The scraper starts sending `page_type`
3. The ingestion layer begins enforcing the per-type rules and the closed enum

With no default and a closed enum, there is no form of the change that a stale
validator tolerates — which is why a naive simultaneous rollout would fail in the
direction that looks like success.

---

## 4. Sandbox tests

**No existing test needs to change.** Verified against the current suites:

- **`tests/test_phase1.py` (38 tests)** — routing, crypto and the visibility table.
  Nothing touches `API_CONTRACT.md`. Unaffected.
- **`tests/test_phase4.py` (41 tests)** — mock-site content and reachability.
  Unaffected, because the proposal changes the ingestion boundary, not the pages.
  SD-021.2's invariant (no identifiers on `index` or `profile` pages) is already
  true of the sites as built, so nothing regresses.

One test is worth naming explicitly to confirm it is *not* in conflict:
`test_profile_pages_state_the_documented_window` asserts profile pages render
`Joined <date>`. SD-021 forbids the scraper from **substituting** that date for
`observed_at`; it does not forbid the page from **displaying** it. The page is
unchanged and the assertion stands.

**New tests would be needed at Phase 5**, not before:

- one payload-shape test per `page_type`, asserting the required/omitted fields
- a negative test that no persona is emitted for an `index` artifact
- a negative test that `persona.observed_at` is absent from a `profile` artifact
- a test that every emitted identifier carries an `observed_at`, and that none of
  them equals `collected_at`, the profile join date, or the latest profile post
  timestamp — the assertion that pins SD-021.2's no-substitution rule
- a test that `index` and `profile` artifacts emit `identifiers: []`, pinning the
  invariant in §1.4 that the mock sites currently satisfy only by construction
- an assertion that exactly six personas are produced across a full run — the
  check that catches a phantom persona

---

## 5. Summary

| Repository | File | Change |
|---|---|---|
| darkweb-sandbox | `AgentsDocs/API_CONTRACT.md` | §3: 1 new required field row (closed enum, no default), 3 conditional `persona` rows, 1 new page-type sub-section, 1 new no-substitution prohibition on `identifiers[].observed_at`, 2 new examples; §4: 4 sample error messages |
| darkweb-sandbox | `AgentsDocs/SCRAPER_AGENT_SPEC.md` | §3 page-type mapping (total); §4 handle, timestamp and identifier-timestamp rules; §8 criteria 3 and 7. §7 unchanged |
| darkweb-sandbox | `AgentsDocs/SPEC_DECISIONS.md` | SD-021 (with SD-021.1, SD-021.2) flipped from proposed to resolved; OPEN-4 closed |
| GOTHAMITE *(to be built)* | ingest validator | `persona` and `persona.observed_at` conditional on `page_type`; reject when wrongly present; accept the new field; reject missing or unsupported `page_type`; keep `identifiers[].observed_at` strict and never synthesise it |
| GOTHAMITE *(to be built)* | persona upsert | No row for `index`; row without timeline advancement for `profile` |
| GOTHAMITE *(to be built)* | correlation pass | Read `observed_at` from `item` artifacts only |

**Nothing above has been done.** No contract modified, no implementation written,
Phase 5 not started, OPEN-4 still open, OPEN-5 / OPEN-6 / OPEN-9 untouched, no
commit. The GOTHAMITE rows describe an ingestion layer that **does not yet
exist** — see §0.
