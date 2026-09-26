# A3 — Decision Brief: counterparty identifier attribution

**Date:** 2026-09-07
**Status:** **DECIDED — recorded as `SPEC_DECISIONS.md` SD-027 (PROPOSED, NOT IN
FORCE).** The human decision is **T5**: remove A2's wallet from D1's listing 44. The
consequences in §3 (T5) and §6 were presented, plus the additional finding that
`DATA_MODEL.md` §4 must be amended as well — removing the wallet removes the only
evidence of the transaction — and the choice was confirmed with all of it stated.
Nothing is edited yet; six amendment tasks are deferred to freeze.
**A3 is reclassified from BLOCKS FREEZE to CAN BE RESOLVED DURING SPEC AMENDMENT.**
**No freeze blockers remain.**

No contract, data model, spec, code or test was modified by this brief. A human has
since chosen, so `SPEC_DECISIONS.md` carries **SD-027** — recorded, not adopted.

---

## 1. The mechanism, step by step

Every step is forced by a document currently in the repository. Nothing here is a
defect in the Phase-4 build.

1. `MOCK_SITES_SPEC.md` §5 **requires** it: *"D1: at least one post referencing A2's
   wallet as a counterparty, phrased as a transaction, not as its own address."*
   Listing 44 on `marketplace-beta` does exactly that — `bellwether` writes
   *"Sent to 1Hx4kQ… on the agreed terms … That address is theirs, not mine."*
2. `SCRAPER_AGENT_SPEC.md` §4's wallet rule is a **regex plus validation**, and §4
   opens *"Rule-based only. **No ML, no NLP, no LLM.**"* It matches `1Hx4kQ…` on that
   page. It cannot read the disclaimer.
3. `DATA_MODEL.md` §2 makes `Identifier.persona_id` a **required FK to Persona**. The
   only persona on that artifact is **D1**.
4. So the identifier is recorded as `wallet = 1Hx4kQ… , persona_id = D1`.
5. `DATA_MODEL.md` §3: **"Identical wallet address | 0.45 | supporting"**, and *"A
   relationship is created when `score ≥ 0.30`."*
6. **D1 ↔ A2 therefore receive a `same_actor_suspected` edge at 0.45** — "moderate".

`DATA_MODEL.md` §4, Actor D says the opposite, in bold:

> *"Transacts with A2's wallet. Creates a `transacted_with` edge only. **Must not
> produce `same_actor_suspected`.** Shows the system distinguishing interaction from
> identity."*

The corpus is correct, the extraction rule is correct, the scoring rule is correct,
and the expected output is correct. **They are jointly inconsistent.**

Scope: exactly one artifact in the corpus triggers it. A scan for identifiers
appearing on a page belonging to a different persona returns one row —
`marketplace-beta/44`. No handle and no PGP fingerprint is cross-referenced anywhere.

---

## 2. Two findings that shape the option space

### 2.1 `Identifier.persona_id` is undefined between two readings

`DATA_MODEL.md` §2 gives `artifact_id` an explicit gloss — *"FK → Artifact — **where
it was seen**"* — and gives `persona_id` **none**:

```
| `persona_id`  | uuid | FK → Persona |
| `artifact_id` | uuid | FK → Artifact — where it was seen |
```

So `persona_id` is silently ambiguous between:

- **ownership** — "this identifier *belongs to* that persona", or
- **observation** — "this identifier was *seen on an artifact of* that persona".

Step 4 above only produces a false conclusion under the **ownership** reading. Under
the observation reading the row is simply true: A2's wallet *was* seen on D1's page.
**The contradiction is created by an undefined field, not by a wrong rule.**

### 2.2 Nothing in any document says how a `transacted_with` edge is produced

`DATA_MODEL.md` §2 lists `transacted_with` in the `Relationship.type` enum, and §4's
summary table asserts D1 → A2 is one. But:

- **§3's scoring table has no signal that produces it.** All five signals — PGP,
  wallet, temporal succession, handle similarity, activity overlap — feed
  `same_actor_suspected`.
- **`Evidence.signal_type`'s enum has no value for it**: `shared_pgp | shared_wallet |
  handle_similarity | temporal_succession | activity_overlap_conflict`.

So the edge the demo promises for Actor D **has no production rule anywhere**. Every
option below leaves this open unless it is decided separately; it is listed as a
residual, not folded into A3.

### 2.3 What the payload actually carries

The `identifiers[]` entries in `API_CONTRACT.md` §3 carry **`type`, `value`,
`observed_at` — and no `persona_id`.** That field is assigned GOTHAMITE-side at
ingest, by joining `persona.handle` with `source_id`.

**This matters for freeze classification**: an option that only redefines
`persona_id`'s meaning and constrains correlation needs **no contract change at
all**, while an option that adds a role marker to `identifiers[]` **does**.

---

## 3. Options

### T1 — Ownership-marked identifiers

Add a role to each identifier, e.g. `"role": "self" | "counterparty"`, and have the
scraper populate it.

**The blocking problem is determination.** A rule-based extractor has no way to know
whose wallet it found. Three routes, each with a cost:

- **Structured markup on the page** — directly forbidden by `MOCK_SITES_SPEC.md` §2
  rule 4: identifiers must appear *"in post bodies, not in structured metadata or
  HTML attributes"*, precisely so extraction does real work. Requires relaxing that
  rule and re-seeding the corpus.
- **A phrase convention** (`payment to X` = self, `Sent to X` = counterparty) —
  brittle keyword matching over prose, and `SCRAPER_AGENT_SPEC.md` §4 warns *"a
  false-positive wallet creates a fake link in the graph, which is worse than missing
  a real one"*. It also edges toward the NLP the scope lock excludes.
- **A curated exception list** — hardcoding that listing 44's wallet is D1's
  counterparty. Deterministic, but it hands the scraper the answer, which §2 rule 4
  exists to prevent.

**Also: changes the contract** (a new `identifiers[]` field), so it must be settled
before freeze and requires GOTHAMITE to consume the field.

### T2 — Define `persona_id` as observational; require corroboration for identity *(recommended)*

Two clarifications, both to `DATA_MODEL.md`, which SD-026 has just marked
descriptive:

1. **`persona_id` means "observed on an artifact of this persona"**, not "owned by
   this persona". Emission asserts observation, never ownership.
2. **A single shared wallet does not, alone, create a `same_actor_suspected` edge.**
   Identity claims require corroboration — a second independent signal.

**Effect on all four seed scenarios:**

| Link | Signals | Under T2 | Matches §4? |
|---|---|---|---|
| A1 ↔ A2 | PGP 0.70 + wallet 0.45 → capped | 0.95, very strong | **Yes** |
| B1 → B2 | wallet 0.45 + temporal succession 0.15 | 0.60, strong | **Yes** |
| C1 vs A1 | handle 0.05 − overlap 0.30 | below threshold, no edge | **Yes** |
| D1 → A2 | wallet **alone** | **no identity edge** | **Yes** |

All four preserved. Note that B1 → B2 already relies on two signals, so the
corroboration rule costs the demo nothing.

**For:**
- **No contract change and no scraper change.** The payload is untouched; `persona_id`
  is GOTHAMITE-side (§2.3). Under this option **A3 stops blocking the contract
  freeze** — see §5.
- The observation is **retained**, not suppressed. D1's page still contributes the
  evidence that D1 and A2 transacted, which is what a `transacted_with` edge would
  need to rest on under `DATA_MODEL.md` §1 rule 2.
- It fixes the cause identified in §2.1 rather than working around it.
- It generalises: any future counterparty mention is handled without a new rule.

**Against:**
- It constrains **GOTHAMITE's correlation logic**, which SD-014 says this repository
  does not own and SD-026 has just marked descriptive. The sandbox can *record the
  requirement*; it cannot impose it. If a future GOTHAMITE ignores the corroboration
  rule, the D1 edge returns.
- "Corroboration" needs a precise form — *"at least two independent supporting
  signals"* is the obvious reading, but it is not currently written anywhere.

### T3 — Suppress the identifier at the scraper

Extend SD-022.4's handle principle to all identifier types: an identifier belonging to
another persona is not emitted.

**Two problems, either fatal:**

1. **Not implementable.** The scraper processes one page at a time and has no global
   view; "belongs to another persona" is knowledge it cannot have. Correlation is
   explicitly a separate pass (`API_CONTRACT.md` §5 rule 3).
2. **It would delete the D1 scenario.** With no identifier emitted, nothing links D1
   to A2 at all, and the `transacted_with` edge has no evidence — leaving three
   demo scenarios instead of four.

Presented because it is the obvious first idea and the natural reading of SD-022.4.
It does not survive contact with the extraction model.

### T4 — Accept the edge; amend §4's expected output

Record D1 → A2 as `same_actor_suspected` at 0.45, alongside or instead of
`transacted_with`.

**Against:** it deletes the point of Actor D. §4 states its purpose as *"Shows the
system distinguishing interaction from identity"* — the one seed case that proves the
system does not confuse a transaction with a shared identity. Accepting the edge
means the demo no longer shows that, and the summary table's "D1 → A2 | transacted_with"
row becomes false.

### T5 — Change the corpus

Remove A2's wallet from listing 44.

**Against:** contradicts `MOCK_SITES_SPEC.md` §5, which requires it; deletes Actor D's
scenario entirely; reopens closed Phase 4 and breaks
`tests/test_phase4.py::test_d1_names_a2_wallet_as_a_counterparty_not_its_own`. It
removes the symptom by removing the demo.

---

## 4. Comparison

| | T1 | **T2** | T3 | T4 | T5 |
|---|---|---|---|---|---|
| Preserves all four seed scenarios | Yes | **Yes** | No | No | No |
| Implementable rule-based | Only with a cost | **Yes — nothing to implement** | **No** | Yes | Yes |
| Requires a contract change | **Yes** | **No** | No | No | No |
| Requires a scraper change | Yes | **No** | Yes | No | No |
| Reopens Phase 4 | Likely | **No** | No | No | **Yes** |
| Addresses §2.1's root cause | Partly | **Yes** | No | No | No |
| Constrains GOTHAMITE logic | Yes (consumes a field) | **Yes (correlation rule)** | No | No | No |
| Still blocks freeze | **Yes** | **No** — see §5 | Yes | No | No |

---

## 5. Freeze consequence — the options differ

**T2 removes A3 from the freeze path.** Because the payload is unchanged (§2.3), the
contract can be frozen without waiting on it; what remains is a recorded requirement
against GOTHAMITE's correlation pass, and two clarifying edits to `DATA_MODEL.md`
sections SD-026 has already scoped as descriptive. A3 would move to **CAN BE RESOLVED
DURING SPEC AMENDMENT**, and **no blocker would remain**.

**T1 keeps A3 blocking**, since it adds a field to `identifiers[]` that GOTHAMITE must
consume — a boundary change that must be settled before the boundary is frozen.

T3, T4 and T5 also unblock the freeze, but each does so by giving up a demo scenario
or by reopening Phase 4.

---

## 6. Impact

| | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|
| `API_CONTRACT.md` | New field | — | — | — | — |
| `DATA_MODEL.md` | §2 | §2 `persona_id`, §3 corroboration | — | §4 expected output | §4 |
| `SCRAPER_AGENT_SPEC.md` | §4 role rule | — | §4 suppression rule | — | — |
| `MOCK_SITES_SPEC.md` | Possibly §2 rule 4 | — | — | — | §5 |
| `mock_sites/` | Possibly re-seed | — | — | — | Edit listing 44 |
| Existing tests | Phase-4 may change | **None** | None | None | **Phase-4 breaks** |
| Phase-5 scraper work | New extraction logic | **None** | New logic | None | None |

**T2 is the only option requiring no change to any existing code, test or corpus.**

---

## 7. Residual items — none resolved here

1. **How is a `transacted_with` edge produced?** (§2.2) No signal in §3, no value in
   `Evidence.signal_type`. Under **every** option, D1 → A2's promised edge has no
   production rule. This is arguably a second gap of the same family and may warrant
   its own decision; it is **not** folded into A3.
2. **Under T2, what exactly is "corroboration"?** Presumably ≥ 2 independent
   supporting signals, but the form is unwritten.
3. **Under T2, what happens if GOTHAMITE does not adopt the rule?** The sandbox can
   record the requirement; SD-014 and SD-026 mean it cannot impose it.
4. **`Evidence.signal_type` may need a transaction value** if residual 1 is resolved
   in favour of producing the edge.
5. **Whether SD-022.4's handle rule should be restated** in whatever terms A3 settles
   on, so handles and wallets are governed by one principle rather than two.

---

**Nothing above has been done.** No contract, data model, spec, code or test
modified; no SD entry created; A3 remains open; Phase 5 not started.
