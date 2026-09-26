# OPEN-5 — Handle Semantics: H1 / H2 / H3

**Date:** 2026-09-07
**Status:** **ANALYSIS ONLY. NO DECISION MADE, NOTHING IMPLEMENTED.**
**Companion to:** `AgentsDocs/reports/OPEN_5_DECISION_BRIEF.md`

Nothing was modified to produce this. `API_CONTRACT.md`, `SCRAPER_AGENT_SPEC.md`,
`SPEC_DECISIONS.md`, `mock_sites/` and all implementation files are untouched.
Phase 5 has not started. OPEN-4, OPEN-6 and OPEN-9 are untouched, and OPEN-4's
page-type semantics are **not** resolved here.

---

## 0. A correction to the earlier brief

`OPEN_5_DECISION_BRIEF.md` §7 recommended **H2**, and its first and load-bearing
argument was that H2 *"is the only pair requiring no contract change"*. On the
instruction to treat the current `API_CONTRACT.md` wording as evidence of a
proposal rather than proof of intent, that argument does not survive, and neither
does the recommendation built on it.

Two facts found on re-reading change the analysis materially. Both were available
before and neither was weighed:

**(a) `Identifier.persona_id` is a required FK to Persona.** `DATA_MODEL.md` §2
gives every Identifier row a `persona_id`. An identifier is therefore always
*already attached* to a persona.

**(b) The handle extraction rule only ever yields the persona's own handle.**
`SCRAPER_AGENT_SPEC.md` §4 states it in full:

> ### Handle
> From the post's author field or the profile page path. Verbatim, case preserved.

The author's field, or the profile's own path. Never a handle *mentioned* in body
text.

Together these mean a handle identifier emitted under the current extraction rule
is necessarily `Identifier(type=handle, value=V, persona_id=P)` where
`P.handle == V`. It restates the persona's primary key back at the persona. That is
not duplication in the harmless sense of belt-and-braces; it is a row that carries
**zero information** not already present in the Persona it points at.

This reframes the comparison, and the strongest option changes. §8 states the
revised position.

---

## 1. The structural asymmetry the scoring table encodes

`DATA_MODEL.md` §3:

| Signal | Weight | Matching |
|---|---|---|
| **Identical** PGP fingerprint | 0.70 | exact value equality |
| **Identical** wallet address | 0.45 | exact value equality |
| Temporal succession | 0.15 | timeline comparison |
| Handle **similarity** (Levenshtein ≤ 2) | 0.05 | edit distance |
| Activity overlap conflict | −0.30 | timeline comparison |

PGP and wallet link personas by **identity of a shared value**. Handle links them by
**similarity of two different values**. These are not the same kind of thing, and
the seed data is built to prove it:

- A1 `nightjar` and A2 `n1ghtjar_` are the **headline link**, and their handles
  **do not match**. They link on PGP and wallet.
- C1 `nightjarr` and A1 `nightjar` have handles one character apart and share
  **nothing** else. They must **not** link.

If handles were cross-site identifiers in the sense PGP and wallet are, the demo's
central pair would not link and its central non-pair would be indistinguishable
from a real one. The 0.05 weight — the smallest supporting signal in the table,
worth one sixth of a wallet — is the data model saying a handle resemblance is
nearly worthless as evidence.

`DATA_MODEL.md` §2 reinforces this: *"A persona is per-site"*, unique on
(`handle`, `source_id`). **A handle is a persona's name, not a fact observed about
it.** PGP fingerprints and wallets are facts observed about a persona; the handle
is the label the persona is filed under.

That distinction is the spine of the comparison below.

---

## 2. H1 — never emit `handle` in `identifiers[]`

**1. Semantic meaning of `identifiers[]`.** Clean and single-purpose: *values
observed on a page that could be shared with another persona*. Every entry is a
candidate for exact-match linkage. PGP and wallet both qualify; the handle, which is
the persona's key, does not.

**2. Is duplication justified?** No duplication occurs. `persona.handle` carries the
handle; `identifiers[]` carries observations about it.

**3. Compatibility with proposed SD-021 page types.** Compatible with all three
without conditions. `index` (no persona), `item` (persona + timestamp) and
`profile` (persona, no timestamp) all emit zero handle identifiers, so the page-type
split never has to be consulted for this question. **H1 is the only option whose
correctness does not depend on how OPEN-4 settles.**

**4. Can `observed_at` be supplied without inventing timestamps?** Vacuously yes —
there is no handle identifier needing one.

**5. Multiple handles on one artifact.** An index page lists several handles; H1
emits none, which is consistent rather than arbitrary. It does not *capture* the
multiplicity either — see §5 of this document.

**6. Phantom personas or duplicate identity evidence.** Neither. No Identifier rows,
so no risk of an identifier implying a persona that does not exist.

**7. Scraper extraction and normalisation.** The handle is still extracted — it is
needed for `persona.handle`. `API_CONTRACT.md` §3's normalisation row (*"Verbatim.
Case-sensitive"*) still applies and is still doing work; under H1 it governs
`persona.handle` rather than an `identifiers[]` entry. This is the reading that
dissolves the apparent contradiction the first brief treated as decisive: the
`handle` row is not evidence of emission if it is read as the normalisation rule for
the handle field that certainly is sent.

**8. GOTHAMITE ingestion.** Simplest case. Persona rows derive from
`persona.handle`; handle-similarity scoring runs Levenshtein over
`Persona.handle` pairs, which requires no Identifier rows at all. Nothing is lost.

**9. Future stylometry / entity resolution.** Stylometry is cut by the
`MASTER_CONTEXT.md` scope lock and is not a consideration. For future entity
resolution, H1 leaves the cleanest slate: if *mentioned* handles later become
interesting (see §5), they can be introduced as a genuinely new signal without first
having to disentangle them from tautological self-handle rows.

**10. Contract/spec changes required.** `API_CONTRACT.md` §3 needs a clarifying
sentence that the `handle` normalisation row governs `persona.handle` and that
`handle` is not emitted in `identifiers[]` in Phase 5. `SCRAPER_AGENT_SPEC.md` §4
likewise. `DATA_MODEL.md`'s enum keeps `handle` as reserved-but-unused — the same
posture the brief recommends for `contact`.

**11. Phase-4 corpus and tests.** No effect. No page changes, no test changes.

**12. Clean distinction preserved?** **Yes, maximally.** `persona.handle` = who the
page is by. `identifiers[]` = what shared values were seen on it. The two never
overlap.

---

## 3. H2 — emit `handle` on every authored `item` artifact

**1. Semantic meaning of `identifiers[]`.** Becomes two things at once: shared-value
observations (PGP, wallet) *and* a restatement of the artifact's authorship. The
category loses its single meaning.

**2. Is duplication justified?** **This is H2's central problem.** The row is
`Identifier(type=handle, value=V, persona_id=P)` with `P.handle == V` — derivable
from the Persona row by definition. The usual defence is the evidence trail
(`DATA_MODEL.md` §1 rule 2, *"every derived claim traces to an artifact"*), but that
does not apply: `Identifier.artifact_id` records where a value was seen, and the
artifact already carries `persona.handle`, so the provenance exists without the row.
The claim "persona P had handle V on artifact A" is already fully traced.

**3. Compatibility with SD-021 page types.** Compatible, because H2 is scoped to
`item` only — the one page type that has both a persona and a post timestamp. It
sidesteps the hard cases by construction rather than by resolving them.

**4. `observed_at` without inventing timestamps.** Yes. An `item` artifact's post
timestamp is the correct, real value.

**5. Multiple handles on one artifact.** Not applicable — an `item` has exactly one
author. H2 captures no multiplicity.

**6. Phantom personas or duplicate identity evidence.** No phantom personas, since
the handle is always the authoring persona's own. But it **does** create duplicate
identity evidence: ~48 rows across the Phase-4 corpus, each asserting a persona has
the handle it is keyed by. If GOTHAMITE ever counted identifier rows as
corroboration, this would inflate a persona's apparent evidential weight purely as
a function of how much it posted.

**7. Scraper extraction and normalisation.** No new extraction work — the handle is
already parsed for `persona.handle`. Only the emission step is added.

**8. GOTHAMITE ingestion.** Must store rows it cannot use for exact-match linkage,
and must be careful not to treat a `handle` identifier the way it treats a `wallet`
one. Two personas sharing a handle *value* across sites would be a genuine signal —
but the scoring table has no "identical handle" row, so there is nowhere for that to
go. The rows are stored and inert.

**9. Future stylometry / entity resolution.** Mildly negative: a future
implementer inspecting `identifiers[]` would see `handle` rows and reasonably infer
they are meant for matching, which the scoring table does not support.

**10. Contract/spec changes required.** None to `API_CONTRACT.md` — this is the
option the current wording most readily admits. `SCRAPER_AGENT_SPEC.md` §4 would
gain a sentence making the emission explicit.

**11. Phase-4 corpus and tests.** No effect.

**12. Clean distinction preserved?** **No.** `identifiers[]` comes to contain both
the persona's key and observations about the persona, with nothing in the payload
distinguishing them except the `type` value.

---

## 4. H3 — emit `handle` only on `profile` artifacts

**1. Semantic meaning of `identifiers[]`.** Arguably the most defensible of the
three emitting designs: a profile page's *subject matter* is the handle, so
recording it as an observation has a rationale an item page's byline does not.

**2. Is duplication justified?** Weakly. Six rows instead of forty-eight, and each
says "this handle has a profile page here" — marginally more than a byline. Still
tautological against the Persona it points at.

**3. Compatibility with SD-021 page types.** **This is where H3 breaks.** It emits
identifiers on precisely the page type that proposed SD-021 says has **no
`persona.observed_at`**, because a profile page has no single post timestamp.

**4. `observed_at` without inventing timestamps.** **No — and this is decisive.**
Every Identifier object requires an `observed_at` (`DATA_MODEL.md` §2, and
`API_CONTRACT.md` §3 as reaffirmed by proposed SD-021.2). A profile page offers only
the join date, the latest post timestamp, or collection time — **all three named
explicitly as forbidden surrogates** by SD-021.2. H3 therefore has no permissible
value to supply.

This is not a coupling to be managed; as things stand it is a direct contradiction.
H3 can only be adopted if OPEN-4 resolves in a way that grants profile artifacts a
legitimate identifier timestamp, and SD-021.2 as proposed does the opposite. Noted
without resolving OPEN-4: **H3 and SD-021.2 as currently proposed cannot both
hold.**

**5. Multiple handles on one artifact.** Not applicable — one profile, one handle.

**6. Phantom personas or duplicate identity evidence.** No phantoms; six duplicate
rows.

**7. Scraper extraction and normalisation.** Requires a page-type-conditional
emission rule — the only one of the three options that needs the scraper to branch
on page type for this field.

**8. GOTHAMITE ingestion.** Would need to accept an identifier whose `observed_at`
is absent or somehow special, which no current contract text permits.

**9. Future stylometry / entity resolution.** Neutral.

**10. Contract/spec changes required.** The largest of the three: a page-type
restriction in `API_CONTRACT.md` §3, an exception to the identifier-timestamp rule,
and a conditional emission rule in `SCRAPER_AGENT_SPEC.md` §4.

**11. Phase-4 corpus and tests.** No effect.

**12. Clean distinction preserved?** Partially. Fewer blurred rows than H2, but the
category still mixes key and observation.

---

## 5. A gap none of the three options fills

All three concern the **authoring** persona's own handle, because that is all
`SCRAPER_AGENT_SPEC.md` §4 extracts.

None captures a **mentioned** handle — one persona naming another in body text.
That is the case that would carry real information, and the corpus already contains
its wallet-shaped analogue: D1 `bellwether`'s listing 44 names A2's wallet as a
counterparty, producing a `transacted_with` edge. A handle mention would be the
same shape of evidence.

Two reasons it is out of scope here, both recorded rather than acted on:

- `Identifier.persona_id` is a FK to Persona. A mentioned handle belongs to a
  *different* persona than the artifact's author, so emitting one would either
  mis-attribute it to the author or **create a phantom persona** for a handle that
  may not exist on that site. This is the one place phantom personas genuinely
  threaten, and it is a design question no current document answers.
- `DATA_MODEL.md` §3 has no scoring signal a mentioned handle would feed.

Flagged as a distinct future question, not folded into OPEN-5.

---

## 6. Comparison summary

| | H1 (never) | H2 (item) | H3 (profile) |
|---|---|---|---|
| 1. `identifiers[]` stays single-purpose | **Yes** | No | Partly |
| 2. Duplication justified | N/A — none | **No** | Weakly |
| 3. SD-021 page-type compatible | **All three** | `item` only, by construction | **Contradicts SD-021.2** |
| 4. `observed_at` without invention | **Vacuously yes** | Yes | **No** |
| 5. Captures multiple handles | No | No | No |
| 6. Phantom personas | None | None | None |
| 6b. Duplicate identity evidence | None | ~48 rows | 6 rows |
| 7. Scraper effect | None beyond today | Emission step | Conditional branch |
| 8. GOTHAMITE effect | Simplest | Stores inert rows | Needs a timestamp exception |
| 9. Future entity resolution | **Cleanest slate** | Mildly misleading | Neutral |
| 10. Contract changes | Clarifying sentence | None | Largest |
| 11. Phase-4 corpus/tests | None | None | None |
| 12. Clean key/observation split | **Preserved** | Lost | Partial |

---

## 7. On "no contract change required"

The first brief treated H2's zero-contract-change property as decisive. It is not,
for two reasons.

First, it proves only that the current wording *admits* H2 — not that H2 was
intended. The `handle` row in the normalisation table is equally well explained as
the rule governing `persona.handle`, which is unambiguously sent on every artifact
and unambiguously needs a normalisation rule. Under that reading the table is not
evidence of emission at all.

Second, the cost being avoided is one clarifying sentence. Weighing that against a
semantic distinction the data model spends its scoring table establishing is a bad
trade, and it is precisely the reasoning the instruction for this document warns
against: preferring the cheap edit to the correct model.

---

## 8. Strongest option

**H1 — never emit `handle` inside `identifiers[]`.**

It is the only option that keeps `identifiers[]` meaning one thing (shared values
that could link personas), the only one that creates no tautological rows, the only
one whose correctness is independent of how OPEN-4 resolves, and the only one that
preserves the distinction the scoring table is built on: PGP and wallet match by
identity, handles by similarity, and a handle is a persona's key rather than an
observation about it.

H3 is additionally ruled out for now by a hard contradiction with proposed SD-021.2
(§4, point 4). H2 is coherent and harmless but adds ~48 rows per corpus that restate
their own foreign key.

**This reverses the earlier brief's recommendation of H2.** The reversal is
recorded rather than quietly applied, and the reasoning is in §0 and §7.

---

## 9. Strongest argument against H1

**The `handle` enum value becomes reserved-but-unused, and the current contract
does read more naturally as admitting emission.**

`DATA_MODEL.md` §2 lists `handle` as an Identifier type. Under H1 it joins `contact`
as a declared type nothing ever produces — two of four enum values inert. A reader
may reasonably conclude the model intended handles to be identifiers and that H1 is
a narrowing of the design rather than a reading of it.

The counter-argument to my own §7 also deserves stating: my reinterpretation of the
normalisation row as governing `persona.handle` is a **reading**, not a
certainty. The table is headed *"Identifier normalisation"*, and `persona.handle` is
not, strictly, an identifier object. If the original author meant that heading
literally, H2 is what they intended and H1 overrides an intent I am inferring away.

A secondary cost: if the extraction rule is ever widened to mentioned handles (§5),
H1 would need reversing — though that would be a new signal warranting its own
decision regardless.

---

## 10. Unresolved dependency on OPEN-4

**H1 has none.** It is correct under every possible resolution of OPEN-4's page-type
semantics, because it emits no handle identifiers on any page type.

**H2 has a weak one.** It is defined over `item` artifacts, so it presupposes that
"item" is a meaningful category — which is proposed SD-021's contribution and not
yet in force. If OPEN-4 resolves differently, H2's scope needs restating in whatever
terms replace it.

**H3 has a blocking one.** It requires an `observed_at` for an identifier on a
profile artifact, and proposed SD-021.2 forbids every available candidate — join
date, latest post, collection time. **H3 cannot be adopted while SD-021.2 stands as
proposed.** OPEN-4 is not resolved here; this records the dependency only.

---

## 11. Exact human decision still required

One decision, with a second contingent on it:

> **Decision 1 — required.** Is `handle` emitted inside `identifiers[]`?
> Choose **H1** (never), **H2** (on `item` artifacts), or **H3** (on `profile`
> artifacts, only viable if OPEN-4 resolves to permit an identifier timestamp on
> profile pages).

> **Decision 2 — contingent, only if H1 is chosen.** Does `handle` stay in
> `DATA_MODEL.md` §2's Identifier enum as reserved-but-unused, alongside `contact`,
> or is the enum narrowed to the types actually produced?

Not requested, not decided, and recorded only so it is not mistaken for part of
OPEN-5: whether **mentioned** handles should ever become a signal (§5). That would
be a new capability with its own phantom-persona risk, not an interpretation of the
existing documents.

---

**Nothing above has been done.** No contract modified, no spec modified, no
`SPEC_DECISIONS.md` entry created, no implementation written, Phase 5 not started,
OPEN-4 / OPEN-6 / OPEN-9 untouched, no commit.
