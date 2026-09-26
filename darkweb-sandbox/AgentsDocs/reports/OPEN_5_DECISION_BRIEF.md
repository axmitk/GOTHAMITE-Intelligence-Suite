# OPEN-5 — Decision Brief

**Date:** 2026-09-07
**Status:** **SUPERSEDED IN PART.** A human decision has since been recorded as
`SPEC_DECISIONS.md` **SD-022** — **PROPOSED, NOT IN FORCE**. The decision is
**H1 + C1**, which **reverses this brief's §7 recommendation of H2 + C1**. The
handle half of §4a and §7 is superseded; see `OPEN_5_HANDLE_SEMANTICS.md` for the
analysis that changed it, and §7a below for the short version. Everything about
`contact` (§4b, C1) stands and was adopted as decided.
**Blocks:** Phase 5. **OPEN-5 remains open** — the decision is recorded, contract
adoption is pending.

No file was modified to produce this brief. `API_CONTRACT.md`,
`SCRAPER_AGENT_SPEC.md`, `DATA_MODEL.md`, `mock_sites/` and all implementation
files remain untouched, and Phase 5 has not started. OPEN-4, OPEN-6 and OPEN-9 are
untouched. A human has since chosen, so a proposal entry now exists in
`SPEC_DECISIONS.md` as **SD-022** — recorded, not adopted.

---

## 1. What OPEN-5 says

Verbatim from `AgentsDocs/SPEC_DECISIONS.md` §2:

> | **OPEN-5** | Whether `handle` and `contact` are ever emitted as `identifiers[]`
> entries, and how `contact` is extracted and normalised. | Phase 5 |

Two questions bundled into one row. They have very different evidence bases and
are best decided separately, so this brief splits them: **§4a** covers `handle`,
**§4b** covers `contact`.

---

## 2. Documents and sections creating the ambiguity

| Document | Section | What it says | Effect |
|---|---|---|---|
| `DATA_MODEL.md` | §2, Identifier | `type` enum is `pgp_fingerprint` \| `wallet` \| `handle` \| `contact` | All four are **valid identifier types** |
| `API_CONTRACT.md` | §3, example | `identifiers[]` contains only `pgp_fingerprint` and `wallet` | Suggests only two are emitted |
| `API_CONTRACT.md` | §3, normalisation table | Rows for `pgp_fingerprint`, `wallet`, **`handle`** — headed *"Identifier normalisation — scraper's job, before sending"* | **`handle` is expected in `identifiers[]`.** No `contact` row |
| `API_CONTRACT.md` | §3, field rules | `persona.handle` required, *"As displayed on the page"* | The handle already travels **outside** `identifiers[]` |
| `SCRAPER_AGENT_SPEC.md` | §4, Extraction | Rules for PGP fingerprint, Wallet, **Handle**, Timestamps | Handle is extracted. **No rule for `contact`** |
| `SCRAPER_AGENT_SPEC.md` | §7, run summary | `Identifiers extracted:  PGP 12 \| wallet 19 \| handles 6` | Handles are **counted as extracted identifiers** |
| `DATA_MODEL.md` | §3, Scoring | Signals are PGP, wallet, temporal succession, handle similarity (Levenshtein ≤ 2), activity overlap | `handle` feeds scoring. **`contact` feeds nothing** |
| `DATA_MODEL.md` | §4, Seed data | Each persona has a handle, a PGP fingerprint and a wallet | **No persona has a contact value** |

**The decisive asymmetry.** `contact` appears **exactly once in the entire
repository** — in the enum on `DATA_MODEL.md:75`. A repository-wide grep for
"contact" across `AgentsDocs/`, `format/` and `README.md` returns that line,
OPEN-5's own text, and one unrelated prose use ("point of contact"). There is no
extraction rule, no normalisation row, no seed value, no scoring signal and no
acceptance criterion for it anywhere.

`handle`, by contrast, is named in four places as something the scraper produces.

---

## 3. Competing interpretations

### 3a. `handle`

| | Interpretation | Support |
|---|---|---|
| **H1** | Never emitted in `identifiers[]`. `persona.handle` is the sole carrier | The §3 example shows only PGP and wallet |
| **H2** | Emitted in `identifiers[]` **in addition to** `persona.handle`, on every artifact where a handle is displayed | The normalisation table, the run summary, the enum |
| **H3** | Emitted only where the handle is the page's **subject** (profile pages), not on every authored page | The run summary's `handles 6` = one per persona |

### 3b. `contact`

| | Interpretation | Support |
|---|---|---|
| **C1** | Never emitted in Phase 5. The enum value is reserved but unused | Absence of any rule, value, signal or criterion |
| **C2** | Define an extraction rule and emit it | The enum lists it as a valid type |

---

## 4. Which interpretation fits the authoritative documents

### 4a. `handle` — H2 or H3, not H1 *(SUPERSEDED — the recorded decision is H1; see §7a)*

**H1 is the weakest.** Its only support is an example, and an example that omits
something is not a rule that forbids it — the same example also omits `handle`
identifiers while `API_CONTRACT.md` three lines later tells the scraper how to
normalise them. A normalisation rule for a value that is never sent would be dead
text in a contract that is otherwise tight.

Two further points favour emission:

- `DATA_MODEL.md` §2 gives Identifier an `artifact_id` — *"where it was seen"*.
  `persona.handle` says which persona an artifact belongs to; a `handle` identifier
  says this handle was **observed on this page**. Those are different claims.
- `DATA_MODEL.md` §1 rule 2: *"Every derived claim traces to an artifact."*
  Handle-similarity scoring (§3, weight 0.05) is a derived claim about handles, and
  it is the signal that must correctly **fail** for the C1 decoy. Artifact-level
  evidence for it is exactly what an Identifier row provides.

**H2 versus H3 is genuinely undetermined by the documents.** The only evidence
separating them is the run summary's `handles 6`, which equals the persona count —
suggestive of H3. But that line should not be leaned on: its companion figures are
`PGP 12` and `wallet 19`, while the seed data contains only **5 distinct
fingerprints and 4 distinct wallets**. The numbers are illustrative and do not
reconcile with §4 under either an occurrence or a distinct-value reading. Treating
`handles 6` as normative would be reading precision into a placeholder.

Between them, **H2 is the more defensible default**: it follows the contract's own
phrasing ("as displayed on the page") mechanically, needs no special case, and
produces strictly more evidence rows. H3's appeal is that it avoids emitting the
same handle 8 times per persona — a storage concern, not a correctness one, and one
`content_hash` deduplication does not address because the rows differ by artifact.

### 4b. `contact` — C1, clearly

C2 would require inventing all of the following, none of which exists:

1. **A definition.** "Contact" is undefined — email, XMPP/Jabber, session ID,
   messenger handle? The scope differs wildly by choice.
2. **An extraction rule** in `SCRAPER_AGENT_SPEC.md` §4.
3. **A normalisation rule** in `API_CONTRACT.md` §3, where `handle` has one and
   `contact` does not.
4. **Seed data.** No persona in `DATA_MODEL.md` §4 has a contact value, and the
   Phase-4 sites carry none — `tests/test_phase4.py::test_no_real_network_identifiers`
   asserts no `@` appears anywhere on any page. Adding contact values would mean
   **reopening a closed phase** and editing `mock_sites/seed_data.py`.
5. **A purpose.** `DATA_MODEL.md` §3's scoring table has no contact signal, so an
   emitted contact identifier would be stored and never used.

There is also a safety argument. `SCRAPER_AGENT_SPEC.md` §4 warns that *"a
false-positive wallet creates a fake link in the graph, which is worse than missing
a real one."* An undefined `contact` type is the worst case for that failure mode:
a loose pattern over prose would match ordinary text, and every false positive
becomes a spurious identifier with no scoring purpose to justify the risk.

---

## 5. Downstream impact of each option

| Option | Sandbox code | Sandbox tests | Contract | GOTHAMITE |
|---|---|---|---|---|
| **H1** (no handle) | Scraper omits handle identifiers | Phase-5 tests only | `API_CONTRACT.md` §3 must **delete** the `handle` normalisation row, or mark it unused | Nothing to store |
| **H2** (handle everywhere) | Scraper emits one handle identifier per authored artifact | Phase-5 tests assert presence and verbatim casing | No change — the row already exists | Must store `handle` identifiers; must not treat them as duplicates of `persona.handle` |
| **H3** (handle on profiles) | Scraper emits handle identifiers only for profile artifacts | Phase-5 tests assert presence on profiles, absence on items | Needs a new sentence stating the restriction | Same as H2, fewer rows |
| **C1** (no contact) | None | None | Optional note that `contact` is reserved and unused in Phase 5 | Must accept that no `contact` ever arrives |
| **C2** (emit contact) | New extractor + normaliser | New extraction tests, plus **`mock_sites/seed_data.py` edits and Phase-4 test changes** | New normalisation row, new extraction rule | New validation; new scoring signal or a stored-and-unused type |

**No existing test is affected by any option.** `tests/test_phase1.py` (38) and
`tests/test_phase4.py` (41) cover routing and page content; neither asserts payload
shape. The exception is **C2**, which would require adding contact values to the
mock sites and would therefore break
`test_no_real_network_identifiers` — the only path here that reopens Phase 4.

---

## 6. Ownership: sandbox, boundary, or both

**Both, and the split is clean.**

- **Sandbox-side.** What the scraper extracts and emits is
  `SCRAPER_AGENT_SPEC.md` §4 and Phase-5 code — wholly inside this repository.
  Whether seed data grows a contact value is `DATA_MODEL.md` §4, which SD-014 makes
  authoritative here.
- **Boundary.** Which identifier `type` values may appear in `identifiers[]` is
  `API_CONTRACT.md`, the single seam. Any option that changes the set of types on
  the wire is a contract change.
- **GOTHAMITE-side.** How a `handle` identifier is stored, and whether it is
  reconciled against `persona.handle`, belongs to GOTHAMITE's ingestion
  representation. Per the OPEN-4 project-state clarification, **no GOTHAMITE
  implementation currently exists**, so no compatibility review of that half is
  possible. This brief specifies required behaviour only; it asserts nothing about
  existing code.

The recommended pair below is chosen partly because it minimises the boundary
half: it needs **no change to `API_CONTRACT.md`'s type set at all**.

---

## 7a. Superseded — what the recorded decision says

**Recorded 2026-09-07 as SD-022 (PROPOSED, not in force): H1 + C1.**

- **H1** — the scraper does **not** emit the persona's own handle in
  `identifiers[]`. `persona.handle` is the sole carrier.
- **C1** — `contact` is reserved, not extracted, not emitted. **Unchanged from
  this brief's recommendation.**
- The Identifier enum is **not** narrowed; `handle` and `contact` stay reserved.
- Mentioned handles are explicitly out of scope.

**Why §7 below was wrong on the handle half.** Its first and load-bearing argument
was that H2 required no contract change. That mistakes what the current wording
*admits* for what it *intends*, and the cost avoided was one clarifying sentence.
Two facts settle it against H2:

1. `DATA_MODEL.md` §2 makes `Identifier.persona_id` a **required FK to Persona**.
2. `SCRAPER_AGENT_SPEC.md` §4 extracts only the persona's **own** handle.

So an emitted handle identifier necessarily points at the persona whose key it
already is — a tautological row. The brief's "evidence trail" defence does not
rescue it: the artifact already carries `persona.handle`, so the provenance exists
without the row.

The original recommendation is preserved unedited below, so the reasoning that
produced it — and the correction to it — both remain legible.

---

## 7. Recommendation *(superseded on the handle half — see §7a)*

**H2 + C1**, as one decision:

> **`handle` IS emitted** as an `identifiers[]` entry, verbatim and
> case-preserved per `API_CONTRACT.md` §3, on every artifact where the scraper
> attributes the page to a single persona — in addition to, not instead of,
> `persona.handle`.
>
> **`contact` is NOT emitted** in Phase 5. The enum value stays in
> `DATA_MODEL.md` as reserved and unused. No extraction rule, normalisation rule
> or seed value is created for it.

**Rationale.**

1. **It is the only pair requiring no contract change.** `API_CONTRACT.md` already
   carries a `handle` normalisation row and no `contact` row. H2 + C1 makes the
   contract's existing text correct as written; every other combination requires
   editing it — H1 to delete a row, C2 to add one.
2. **It keeps a dead rule from staying dead.** A normalisation rule for a value
   never sent is a latent contradiction that would resurface the first time someone
   implements against the contract literally.
3. **It preserves the evidence trail** that `DATA_MODEL.md` §1 rule 2 requires for
   the handle-similarity signal, which is the signal that must correctly reject
   `nightjarr` — the seed case the data model calls the most important one.
4. **C1 costs nothing and avoids reopening Phase 4.** Nothing downstream consumes
   `contact`, so not emitting it loses no capability; emitting it would require
   inventing a definition, a rule, seed data and a purpose, and would break a
   passing Phase-4 test.
5. **C1 is reversible; C2 is not cheaply.** Leaving the enum value reserved keeps
   the option open for a later phase at zero cost. Adding contact values to the
   deterministic seed data is a one-way change to a closed phase.

**Confidence, stated honestly:** high on C1 — the evidence is one-sided. Moderate
on H2 over H3 — H2 follows the contract mechanically, but the run summary's
`handles 6` is the one artefact pointing the other way, and I have argued above why
I do not think it can bear that weight. If a human prefers H3, nothing in the
documents forbids it; it needs one added sentence in `API_CONTRACT.md` §3.

---

## 8. Residual ambiguities the decision would create

Recorded now so they are not discovered mid-Phase-5. **None is resolved here.**

1. **`observed_at` for a `handle` identifier.** Every identifier object requires
   one. On an item page the post timestamp is the obvious value. On a **profile**
   page there is no post timestamp — which is exactly the situation OPEN-4's
   proposal (SD-021.2) addresses by forbidding surrogates. **OPEN-5 and OPEN-4 are
   coupled here**, and under H2 the coupling is live: if profile artifacts carry a
   handle identifier, that identifier needs an `observed_at` that SD-021.2 says may
   not be synthesised. Flagged, not resolved — OPEN-4 is out of scope for this
   brief.
2. **Index pages under H2.** An index page displays several handles and has no
   single author. Whether it emits several handle identifiers, or none, depends on
   how OPEN-4 settles. Same coupling.
3. **Duplication semantics.** The same handle would arrive twice per artifact —
   once as `persona.handle`, once in `identifiers[]`. Whether GOTHAMITE stores both,
   reconciles them, or treats a mismatch as an error is undefined.
4. **Run-summary counts.** `SCRAPER_AGENT_SPEC.md` §7's `handles 6` will not match
   H2's output. Whether the summary counts occurrences or distinct values is
   undefined for all three identifier types, and its illustrative figures do not
   reconcile with the seed data under either reading.
5. **The reserved enum value.** Whether `contact` should stay in `DATA_MODEL.md`'s
   enum as reserved, or be removed until needed, is a small open question. Keeping
   it costs nothing but leaves the same OPEN-5 question re-askable later.

Items 1 and 2 are the ones with teeth: **the `handle` decision cannot be fully
implemented until OPEN-4 is settled**, because both turn on what a profile and an
index artifact look like.

---

## 9. Files that would eventually need changing

Under the recommended **H2 + C1**:

| File | Change |
|---|---|
| `AgentsDocs/SPEC_DECISIONS.md` | New SD entry recording the decision; OPEN-5 marked resolved |
| `AgentsDocs/SCRAPER_AGENT_SPEC.md` | §4 Handle rule to state the handle is emitted as an identifier, not only used for `persona.handle`; optionally a line that `contact` is not extracted in Phase 5 |
| `AgentsDocs/API_CONTRACT.md` | **No change required** — the `handle` normalisation row already exists and becomes correct as written |
| `scraper/` (Phase 5, not yet written) | Emit the handle identifier |
| `tests/test_phase5.py` (not yet written) | Assert handle identifiers present, verbatim, case-preserved; assert no `contact` identifier is ever emitted |
| `mock_sites/`, `tests/test_phase4.py`, `tests/test_phase1.py` | **No change** |

Under **C2** instead, add: `AgentsDocs/DATA_MODEL.md` §4 (new seed values),
`AgentsDocs/API_CONTRACT.md` §3 (normalisation row), `mock_sites/seed_data.py`
(contact strings in post bodies), and `tests/test_phase4.py`
(`test_no_real_network_identifiers` would need relaxing) — the only route that
reopens Phase 4.

---

**Nothing above has been done.** No contract modified, no implementation written,
no `SPEC_DECISIONS.md` entry created, Phase 5 not started, OPEN-4 / OPEN-6 /
OPEN-9 untouched, no commit.
