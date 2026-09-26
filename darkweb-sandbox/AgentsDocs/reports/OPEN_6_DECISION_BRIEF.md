# OPEN-6 — Decision Brief

**Date:** 2026-09-07
**Status:** **SUPERSEDED IN PART.** A human decision has since been recorded as
`SPEC_DECISIONS.md` **SD-023** — **PROPOSED, NOT IN FORCE**. The decision is **U2**,
a canonical absolute HTTP URL (`http://<mock-host>/<path>`), which **reverses this
brief's §9 recommendation of U1**. It turned on the counter-argument this brief
raised against its own recommendation — that a scheme-less value is not a URL in a
field named `url`. See §9a. Sections 1–8, 10 and 11 stand as written; the U3
exclusion is unaffected.
**Blocks:** Phase 5. **OPEN-6 remains open** — the decision is recorded, contract
adoption is pending.

Nothing was modified to produce this brief. `API_CONTRACT.md`,
`SCRAPER_AGENT_SPEC.md`, `DATA_MODEL.md`, `mock_sites/` and all implementation files
remain untouched, and Phase 5 has not started. OPEN-4, OPEN-5 and OPEN-9 are
untouched. A human has since chosen, so a proposal entry now exists in
`SPEC_DECISIONS.md` as **SD-023** — recorded, not adopted.

---

## 1. What OPEN-6 says

Verbatim from `AgentsDocs/SPEC_DECISIONS.md` §2:

> | **OPEN-6** | Whether `url` in the ingest payload includes a scheme. | Phase 5 |

---

## 2. Documents and exact sections

| Document | Line / section | Text | Status |
|---|---|---|---|
| `API_CONTRACT.md` | §3, field rules, line 74 | `url` \| yes \| **"Including the `.onion.mock` host"** | **Normative.** The only rule that constrains this field |
| `API_CONTRACT.md` | §3, example, line 44 | `"url": "alpha7fq2mx9k.onion.mock/thread/14"` | Example. Not marked normative |
| `README.md` | §4, line 108 | `"url": "alpha7fq2mx9k.onion.mock/thread/14"` | Example. `README.md` claims no authority over the contract |
| `DATA_MODEL.md` | §2, Artifact, line 51 | `url` \| str \| **"mock-site path"** | **Normative**, and from the authoritative file |
| `SCRAPER_AGENT_SPEC.md` | §2, line 23 | `onion_client.get(path, "alpha7fq2mx9k.onion.mock", "/thread/14")` | Illustrative call signature. Host and resource are **separate arguments** |
| `MOCK_SITES_SPEC.md` | §6, line 104 | *"The `.onion.mock` suffix is mandatory. These are not real onion addresses and must never be presentable as such."* | Normative, and bears on the scheme question |
| `API_CONTRACT.md` | §5 rule 2 | *"Treat every field as untrusted input… Sanitise before rendering anywhere in the dashboard"* | Normative on the receiving side |

**Not relevant, checked and excluded:** `url` is **not** a deduplication key.
`API_CONTRACT.md` §4 keys duplicates on `content_hash` **+** `source_id`, so no
correctness behaviour depends on the `url` string's exact form. This matters: it
means every option below is display-and-provenance only, and none can silently
corrupt matching.

---

## 3. Contradiction, omission, or underspecification?

**All three, in layers — and OPEN-6 as worded understates the problem.**

**(a) The scheme question is an omission.** `API_CONTRACT.md`'s only normative rule
for this field says the `.onion.mock` host must be included. It says nothing about
a scheme, in either direction. There is no contradiction here, just silence.

**(b) There is a genuine contradiction adjacent to it, about the host.**
`DATA_MODEL.md` §2 defines `Artifact.url` as **"mock-site path"**. Read strictly, a
path is `/thread/14` — with **no host at all**. That is directly incompatible with
`API_CONTRACT.md`'s *"Including the `.onion.mock` host"*.

This is a wider question than the one OPEN-6 asks. OPEN-6 asks "scheme or no
scheme"; the documents also disagree on "host or no host". **The second question
must be answered first**, because the answer to it determines whether the scheme
question is even reachable. Flagged rather than folded in: OPEN-6's wording does not
cover it.

**(c) The residual details are underspecified.** Trailing slash for index pages,
port, query strings — see §10.

---

## 4. Plausible interpretations

| | Form | Example | Textual support |
|---|---|---|---|
| **U1** | host + path, **no scheme** | `alpha7fq2mx9k.onion.mock/thread/14` | Both examples; satisfies `API_CONTRACT.md`'s host rule |
| **U2** | **scheme** + host + path | `http://alpha7fq2mx9k.onion.mock/thread/14` | Satisfies the host rule; makes the field a parseable URL |
| **U3** | path only | `/thread/14` | `DATA_MODEL.md`'s *"mock-site path"*, read strictly |

A fourth form — scheme + host with a port — is excluded: no document mentions a port
in any `.onion.mock` address, and `MOCK_SITES_SPEC.md` §6 maps addresses to
containers with no port component.

---

## 5. Consequences of each interpretation

### 5.1 Relay / network behaviour

**None, under all three options.** This is worth stating plainly because it bounds
the blast radius. `RELAY_PROTOCOL.md` §5.1 fixes the layer at four fields —
`next_hop`, `next_host`, `next_port`, `payload` — and the innermost layer carries a
raw HTTP request. The `url` string is a field in the *ingest payload* sent to
GOTHAMITE, which the relay chain never sees. **OPEN-6 cannot affect routing,
layering, the visibility table, or anything in Phases 1–3.**

### 5.2 Scraper behaviour

Trivial under all three, and equal in cost. `SCRAPER_AGENT_SPEC.md` §3's source
list holds `host` per source, and §2's call signature takes host and resource
separately, so the scraper already has both components and composes whichever form
is chosen. No new parsing, no new extraction.

### 5.3 Ingestion

| | Effect |
|---|---|
| **U1** | Stored as-is. **Not a valid URL** by RFC 3986 — a standard parser reads the whole string as a path with an empty host. GOTHAMITE must know to split on the first `/` rather than use a URL library |
| **U2** | Parseable by any standard URL library. Carries a small presentation risk — see §5.7 |
| **U3** | Stored as-is, but **not unique across sources**: `/thread/14` could belong to any of the three sites. `source_id` disambiguates, so nothing breaks, but the evidence locker's `url` alone stops identifying an artifact |

Under all three, dedup is unaffected (§2).

### 5.4 Data model

`DATA_MODEL.md` §2's *"mock-site path"* is satisfied literally only by **U3**.
**U1** and **U2** require reading "path" loosely as "location on the mock site" —
which is plausible prose but is not what the word says.

### 5.5 Tests

**No existing test is affected by any option.** `tests/test_phase1.py` (38) covers
routing and crypto; `tests/test_phase4.py` (41) covers page content and reachability.
Neither asserts anything about ingest payload shape, because no payload is produced
yet. Phase-5 tests would assert the chosen form.

### 5.6 Phase 5

Blocking but small. The scraper cannot emit a payload until the form is fixed, and
`SCRAPER_AGENT_SPEC.md` §8 criterion 7 (*"Every payload validates against
`API_CONTRACT.md`"*) cannot be evaluated against a rule that does not exist. No
other Phase-5 work depends on it.

### 5.7 Safety and presentability — the one asymmetric consequence

`MOCK_SITES_SPEC.md` §6: *"These are not real onion addresses and must never be
presentable as such."*

The `.onion.mock` suffix is the real guard, and it is present in U1 and U2 alike.
But a scheme-prefixed string is materially more likely to be **auto-linkified** by a
dashboard, a chat client, or a Markdown renderer, turning a synthetic address into
something that renders as a live link. `API_CONTRACT.md` §5 rule 2 already tells
GOTHAMITE to sanitise before rendering, which is the correct mitigation — but a
form that does not invite linkification is a second line of defence that costs
nothing.

This cuts against U2. It is a genuine consideration, not a decisive one: the address
is unresolvable either way, and the failure mode is cosmetic.

---

## 6. Which document is authoritative

The hierarchy, preserved as the repository states it:

- `API_CONTRACT.md:4` — *"Conforms to: GOTHAMITE `docs/DATA_MODEL.md` — that file is
  authoritative. If this contract and the data model disagree, the data model wins
  and this file gets corrected."*
- `DATA_MODEL.md` (local) — its authority line, as clarified by **SD-014**, makes it
  the single source of truth for the **sandbox's simulated ground truth and sandbox
  data model**, with `API_CONTRACT.md` and `MOCK_SITES_SPEC.md` conforming to it.

**This produces a real difficulty, and it should not be papered over.**
`API_CONTRACT.md` defers to *GOTHAMITE's* `docs/DATA_MODEL.md` — a file that, per the
OPEN-4 project-state clarification, **does not exist**; no GOTHAMITE repository is
present in this workspace or the owning account. Meanwhile SD-014 gives the *local*
`DATA_MODEL.md` authority over the sandbox data model, but explicitly **not** over
GOTHAMITE's internal ingestion representation.

`Artifact` is an entity GOTHAMITE stores. Whether `Artifact.url` falls under "the
sandbox data model" (local file authoritative) or "GOTHAMITE's ingestion
representation" (out of scope here) is **not determined by SD-014's wording**.

**Conclusion on authority: the hierarchy does not cleanly resolve (b).** The one
thing that can be said with confidence is that `API_CONTRACT.md`'s field rule —
*"Including the `.onion.mock` host"* — is the only normative statement written
specifically about the **ingest payload's** `url`, whereas `DATA_MODEL.md`'s
*"mock-site path"* is a two-word column note describing a **stored entity**. On
specificity of subject matter, the contract rule is the better evidence about the
payload. That is an argument, not an appeal to hierarchy.

---

## 7. Can OPEN-6 be resolved entirely within the sandbox specification?

**Yes for the text; no for adoption.**

Every document involved — `API_CONTRACT.md`, `DATA_MODEL.md`,
`SCRAPER_AGENT_SPEC.md` — lives in this repository. The wording can be fixed here
with no external input.

But `url` is a **payload field crossing the seam**, so the change is a contract
change and follows the same route as SD-021 and SD-022: recorded as proposed, then
adopted when the ingestion contract is frozen. Since no GOTHAMITE implementation
exists, there is no compatibility constraint to satisfy and no migration to stage —
the same conclusion the OPEN-4 clarification reached.

---

## 8. Does it affect the GOTHAMITE API boundary?

**Yes — it is a boundary field by definition**, being a member of the
`POST /api/v1/ingest` body defined in `API_CONTRACT.md` §3, which §1 calls *"the
only point of contact between the two repos"*.

What it does **not** affect: the relay protocol, the directory, the mock sites, or
anything in Phases 1–4 (§5.1).

---

## 9a. Superseded — what the recorded decision says

**Recorded 2026-09-07 as SD-023 (PROPOSED, not in force): U2.**

`url` is a **canonical absolute HTTP URL** at the ingestion boundary:
`http://<mock-host>/<path>`, e.g. `http://alpha7fq2mx9k.onion.mock/thread/14`.
Scheme required and `http` for the simulated sandbox; host required; path required;
bare `/path` invalid; scheme-less host-and-path invalid; no HTTPS unless the sandbox
implements it. `url` stays an ingestion-payload field only — not part of the relay
wire layer. No query-string, fragment or URL-dedup semantics are defined; duplicate
detection remains `content_hash` + `source_id`.

**Why §9 below was reversed.** Its recommendation of U1 was explicitly low
confidence, and it named its own strongest counter-argument: a scheme-less
host-and-path string **is not a URL** in a field called `url`, so an RFC 3986 parser
returns an empty host and silently swallows the whole value as a path. That
counter-argument is what the decision turned on. The safety point in §5.7 —
linkification risk — is real but was judged secondary to `API_CONTRACT.md` §5 rule 2,
which already requires sanitising before rendering.

**What did not change:** §3's diagnosis, the exclusion of **U3**, and the finding
that the specifications alone do not determine U1 versus U2. U2 was chosen on
engineering merit, **not** by treating the examples as normative — indeed it departs
from both examples, which would need updating on adoption.

**The preserved contradiction.** SD-023 resolves the **ingest boundary
representation** only. `DATA_MODEL.md` §2's *"mock-site path"* versus
`API_CONTRACT.md`'s host requirement — residual (1) in §10 — is **deliberately left
standing**, and `DATA_MODEL.md` was **not** edited. It must be reconciled before
contract freeze.

**Residual (2) is narrowed, not closed.** SD-023 rule 4 requires a route path, which
implies an index artifact is `http://alpha7fq2mx9k.onion.mock/` with the slash. The
decision does not say so explicitly.

The original recommendation is preserved unedited below.

---

## 9. Recommendation *(superseded — see §9a)*

**U1 — host + path, no scheme: `alpha7fq2mx9k.onion.mock/thread/14`.**

**Rationale.**

1. **It is the only form both examples show**, in the two documents an implementer
   is most likely to copy from. Per the instruction for this brief, examples are not
   normative — so this is corroboration, not proof. It is stated first because it is
   the most *visible* evidence, not the strongest.
2. **It satisfies the one normative rule written about this field.**
   `API_CONTRACT.md`'s *"Including the `.onion.mock` host"* is the only sentence in
   the repository that constrains the payload's `url`. U1 and U2 both satisfy it;
   **U3 violates it**, which is the firmest thing this brief can say.
3. **It does not invite linkification** (§5.7), giving `MOCK_SITES_SPEC.md` §6's
   "never presentable as such" a second line of defence at zero cost.
4. **U3 is excluded on merit as well as text.** Dropping the host makes `url`
   non-unique across sources and degrades the evidence locker, for no benefit.

**Confidence: low on U1 versus U2. The specifications do not determine it.**

That is the honest position, and it should be recorded as such rather than dressed
up. Once examples are set aside as non-normative — as instructed — the remaining
normative text is satisfied equally by U1 and U2. The recommendation rests on
example-consistency plus a modest safety preference, and a human choosing U2 would
not be contradicting any document.

**The strongest argument against U1**, stated plainly: `alpha7fq2mx9k.onion.mock/thread/14`
**is not a URL**, in a field named `url`. A standard RFC 3986 parser returns an
empty host and treats the entire string as a path, so any GOTHAMITE code reaching
for a URL library gets a wrong answer silently. U2 is correct by construction and
needs no special handling. If U1 is chosen, the contract should say **explicitly**
that the value is a host-and-path string, not a URL, so nobody parses it as one.

---

## 10. Residual ambiguities

None of these is resolved here.

1. **The host-vs-path contradiction (§3b).** `DATA_MODEL.md` §2's *"mock-site path"*
   versus `API_CONTRACT.md`'s *"Including the `.onion.mock` host"* is a **wider
   question than OPEN-6 as worded**, and answering the scheme question without
   answering it leaves the two documents still disagreeing. **This is the item most
   likely to be missed.**
2. **Index-page trailing slash.** Is an index artifact's url
   `alpha7fq2mx9k.onion.mock/` or `alpha7fq2mx9k.onion.mock`? Undefined. It matters
   more than it looks: if GOTHAMITE ever keys anything on url, the two forms are
   different strings for the same page.
3. **Whether `url` is guaranteed parseable.** See §9's counter-argument. Under U1
   the contract should state the parsing rule; under U2 no statement is needed.
4. **Field naming.** If U1 is adopted, `url` names something that is not a URL.
   Renaming would be a larger contract change and is not proposed here.
5. **Coupling to OPEN-4.** Whichever form is chosen applies to index, item and
   profile artifacts alike, so the page-type work does not change the answer — but
   residual (2) is specifically about index pages. **OPEN-4 is not resolved here.**
6. **Trailing content.** No mock-site page uses a query string or fragment, so the
   contract need not address them today. Left unstated rather than decided.

---

## 11. Files that would eventually need changing

Under the recommended **U1**:

| File | Change |
|---|---|
| `AgentsDocs/SPEC_DECISIONS.md` | New SD entry recording the decision; OPEN-6 annotated |
| `AgentsDocs/API_CONTRACT.md` | §3 field rule extended to state the exact form and that the value is a host-and-path string, not an RFC 3986 URL |
| `AgentsDocs/DATA_MODEL.md` | §2 Artifact — *"mock-site path"* corrected to match, **only if residual (1) is resolved in the contract's favour** |
| `scraper/` (Phase 5, not written) | Compose `f"{host}{resource}"` |
| `tests/test_phase5.py` (not written) | Assert the exact form; assert no scheme |
| `mock_sites/`, `tests/test_phase1.py`, `tests/test_phase4.py` | **No change** |

Under **U2**, the same list with `http://` prefixed and no parsing-rule sentence
needed. Under **U3**, `API_CONTRACT.md`'s host rule would have to be deleted rather
than extended.

---

**Nothing above has been done.** No contract modified, no spec modified, no
implementation written, no `SPEC_DECISIONS.md` entry created, Phase 5 not started,
OPEN-4 / OPEN-5 / OPEN-9 untouched, no commit.
