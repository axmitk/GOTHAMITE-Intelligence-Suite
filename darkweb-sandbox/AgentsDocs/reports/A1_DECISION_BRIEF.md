# A1 — Decision Brief: stored `Artifact.url` wording and ownership

**Date:** 2026-09-07
**Status:** **DECIDED — recorded as `SPEC_DECISIONS.md` SD-026 (PROPOSED, NOT IN
FORCE).** The human decision is **W2**: scope-mark §2 and §3 as descriptive and
non-normative for GOTHAMITE, and correct the `Artifact.url` note to the absolute URL.
`AgentsDocs/DATA_MODEL.md` is **unedited** — the amendment lands at freeze.
**A1 is reclassified from BLOCKS FREEZE to CAN BE RESOLVED DURING SPEC AMENDMENT.**
**Blocks:** contract freeze — **A3 is now the only remaining blocker.**

No contract, data model, code or test was modified by this brief. A human has since
chosen, so `SPEC_DECISIONS.md` carries **SD-026** — recorded, not adopted.

---

## 1. The question, as narrowed by SD-025

`DATA_MODEL.md` §2, Artifact:

```
| `url` | str | mock-site path |
```

`API_CONTRACT.md` §3 requires the `.onion.mock` host; SD-023 (proposed) fixes the
transmitted value as `http://<mock-host>/<path>`.

**SD-025 already settled half of this.** The contract is self-authoritative for the
wire format, so **the transmitted value is not in question**. What remains:

1. **Wording** — what should `Artifact.url`'s note say?
2. **Ownership** — whose model is `Artifact` in, and may this repository describe it?

---

## 2. A structural finding that A1 is a symptom of

`Artifact` is unambiguously a **GOTHAMITE-stored** entity. Its own description says
so: *"Raw scraped content, stored verbatim. The evidence locker."* It is keyed by
`artifact_id` (uuid) and holds `content_hash` and `collected_at`. **The sandbox never
stores an artifact — it sends one.** Confirmed: no file in `common/`, `directory/`,
`relay/`, `client/`, `mock_sites/`, `scripts/` or `tests/` references
`artifact_id`, `raw_content` or `content_hash`.

That makes `DATA_MODEL.md` §2 a mixture of two different kinds of content:

| Section | What it actually describes | Who owns it under SD-014 |
|---|---|---|
| §2 `Source`, `Artifact`, `Persona`, `Identifier` | GOTHAMITE's **storage** representation | GOTHAMITE |
| §2 `Relationship`, `Evidence`, `Actor` | GOTHAMITE's **intelligence** structures | GOTHAMITE |
| **§3 Scoring** (weights, thresholds, bands) | GOTHAMITE's **correlation logic** | GOTHAMITE |
| §4 Seed data, §5 Content volume | The sandbox's **simulated ground truth** | **darkweb-sandbox** |

SD-014 is in force and says this repository is authoritative for *"the sandbox's
simulated ground truth and sandbox data model"* and expressly **not** for GOTHAMITE's
internal representation — *"Do not invent or restate a GOTHAMITE data model in this
repository."*

**So A1 is the visible symptom of a category question**: §2 and §3 restate a model
SD-014 says this repository does not own, and §2 carries **no scope sentence** saying
otherwise — it opens with the heading and goes straight into tables.

`Artifact.url` is where the mismatch surfaces first because it is the only field in
§2 that also appears on the wire. It will not be the last: `Persona.first_seen` /
`last_seen` / `post_count` are already touched by SD-021's profile rules, and §3's
weights are the numbers the whole demo quotes.

**This brief does not propose re-litigating SD-014.** It flags the scope so the A1
choice can be made knowing whether it is a one-field fix or the first instance of a
pattern.

---

## 3. Options

### W1 — Correct the note to match the wire

```
| `url` | str | absolute mock-site URL, e.g. http://alpha7fq2mx9k.onion.mock/thread/14 |
```

One cell. Stored value equals sent value, which fits *"stored verbatim, the evidence
locker"* and `API_CONTRACT.md` §5 rule 1 (*"Store `raw_content` before parsing
anything"*).

**Against:** the repository is editing a field description of a GOTHAMITE-owned
entity without saying by what authority. It fixes the contradiction and leaves the
category question (§2) untouched, so the next field to diverge raises it again.

### W2 — Mark §2 and §3 descriptive, and correct the note *(recommended)*

Add a scope sentence at the head of §2 — that the entity tables and §3's scoring
describe the **expected** GOTHAMITE representation for context, are **non-normative
for GOTHAMITE**, and that where a field also appears on the wire, `API_CONTRACT.md`
governs — **and** apply W1's correction so the note stops contradicting the contract.

**For:** resolves A1 and the §2 category error together, consistent with SD-014's
"do not restate a GOTHAMITE data model" and SD-025's "neither internal model
overrides the boundary". Retains §2 and §3 as the useful context they are — the
scoring table is what makes the seed data checkable — without claiming authority
over them. Documentation-only.

**Against:** a larger edit than A1 strictly requires, and it changes the felt status
of §3's weights from specification to expectation. Since GOTHAMITE does not exist,
nothing depends on that today — but it is a real change in what the file claims.

### W3 — Scope-split: stored ≠ sent

`API_CONTRACT.md` governs the transmitted absolute URL; `DATA_MODEL.md` keeps
*"mock-site path"* as what GOTHAMITE stores after normalising on ingest.

**Against, and it is substantial:** it contradicts *"stored verbatim"*; it invents a
normalisation step no document requires; a stored `/thread/14` no longer identifies
its own source without joining `source_id`; and it makes the evidence locker's copy
differ from the evidence received, which is the one property an evidence locker
exists to preserve. Presented for completeness; the brief does not consider it
sound.

### W4 — Delete the note

Leave `| url | str | |` and let `API_CONTRACT.md` govern entirely.

**For:** the repository makes no claim about GOTHAMITE storage — maximally
conservative on ownership.
**Against:** removes documentation with nothing in its place, and readers of §2 lose
the only pointer to what the field holds. Solves the contradiction by silence.

---

## 4. Comparison

| | W1 | **W2** | W3 | W4 |
|---|---|---|---|---|
| Removes the contradiction | Yes | Yes | No — formalises it | Yes, by silence |
| Stored value = sent value | Yes | Yes | **No** | Undefined |
| Consistent with "evidence locker, verbatim" | Yes | Yes | **No** | Undefined |
| Addresses the §2 category error | No | **Yes** | No | Partly |
| Claims authority over GOTHAMITE's model | Implicitly | **No — explicitly disclaims** | Implicitly | No |
| Edit size | 1 cell | 1 cell + 1 paragraph | 1 cell + prose | 1 cell |
| Recurs on the next diverging field | **Yes** | No | Yes | Yes |

---

## 5. Impact — identical under all four

- **Code:** none. No sandbox file references `Artifact`.
- **Tests:** none. Phase-1 (38) and Phase-4 (41) touch neither `DATA_MODEL.md` §2 nor
  payload shape.
- **Phase 5:** unaffected in construction — the scraper emits the contract's value
  under SD-023 regardless of which option is chosen.
- **A3:** untouched. Counterparty identifier attribution is independent.

**A1 is documentation-only under every option.** What differs is what the repository
claims, and whether the question returns.

---

## 6. Residual after each option

1. **Under W1, W3, W4:** the §2/§3 category question stays open and will resurface —
   `Persona.first_seen` / `last_seen` / `post_count` are already implicated by
   SD-021's profile rules, and §3's weights are quoted throughout the demo.
2. **Under W2:** whether §3's scoring weights should stay in this repository at all,
   or move to GOTHAMITE when it exists. W2 makes them explicitly descriptive, which
   defuses but does not answer it.
3. **Under all:** whether `DATA_MODEL.md` should eventually split into a
   sandbox-owned seed-data document and a descriptive GOTHAMITE-model appendix.
   Larger than A1 and not proposed here.

---

**Nothing above has been done.** No contract, data model, code or test modified; no
SD entry created; A1 remains open; A3 remains open; Phase 5 not started.
