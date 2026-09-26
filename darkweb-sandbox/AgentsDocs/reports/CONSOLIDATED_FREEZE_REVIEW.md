# Consolidated Specification Freeze Review — SD-021 … SD-024

**Date:** 2026-09-07
**Status:** **READ-ONLY REVIEW. NOTHING DECIDED, NOTHING AMENDED, NOTHING IMPLEMENTED.**

No specification, contract, code or test file was modified. No OPEN blocker was
closed. Phase 5 has not started.

**Update 2026-09-07 — blocker A2 resolved.** A human decision selected **O2**,
recorded as `SPEC_DECISIONS.md` **SD-025** (PROPOSED, not in force):
`API_CONTRACT.md` is self-authoritative for the wire format, and neither internal
model overrides the boundary. **A2 is reclassified from BLOCKS FREEZE to CAN BE
RESOLVED DURING SPEC AMENDMENT.** `API_CONTRACT.md` itself is unedited — the
amendment happens at freeze. **A1 and A3 still block.** Sections §8.2, §9 and §10
below are annotated accordingly; the original analysis is preserved.

**Update 2026-09-07 — blocker A1 resolved.** A human decision selected **W2**,
recorded as `SPEC_DECISIONS.md` **SD-026** (PROPOSED, not in force): `DATA_MODEL.md`
§2 and §3 are scope-marked descriptive and non-normative for GOTHAMITE, and
`Artifact.url` is corrected to the absolute URL. `DATA_MODEL.md` is unedited — the
amendment happens at freeze. **A1 is reclassified from BLOCKS FREEZE to CAN BE
RESOLVED DURING SPEC AMENDMENT. A3 is now the only remaining freeze blocker.**

**Update 2026-09-07 — blocker A3 resolved. NO FREEZE BLOCKERS REMAIN.** A human
decision selected **T5**, recorded as `SPEC_DECISIONS.md` **SD-027** (PROPOSED, not
in force): A2's wallet is removed from D1's listing 44, eliminating the only
cross-persona identifier in the corpus. The decision was confirmed with its full
scope stated — **six files**, including a passing Phase-4 test and the reopening of a
closed phase, and the demo dropping from four seed scenarios to three. Nothing is
edited yet. The root ambiguity (`persona_id` undefined between ownership and
observation) is **dormant, not resolved**; §3.3 below stands as the analysis of why.

**All four decisions under review are PROPOSED and NOT IN FORCE.** They are treated
below as proposals, never as authority. The distinction between **proposal**,
**contract freeze**, **implementation** and **verification** is preserved
throughout, and no GOTHAMITE implementation detail is invented — none exists.

**One new contradiction was found that none of the four decisions records.** It is
§3.3 below, and it is the single most consequential finding in this review.

---

## 1. SD-021 × SD-022 — page types against handle semantics

### 1.1 Does H1 work cleanly for all three page types?

**Yes, and better than cleanly — the two decisions are mutually reinforcing.**

| `page_type` | `persona` | H1 effect | Result |
|---|---|---|---|
| `index` | absent | no handle identifier | Consistent. Index pages display several handles; none is emitted, and `raw_content` still carries them verbatim, so nothing is lost |
| `item` | handle + `observed_at` | no handle identifier | Consistent, no duplication |
| `profile` | handle, **no** `observed_at` | no handle identifier | **Consistent, and this is the load-bearing case** |

The profile case is where the two decisions interlock. `OPEN_5_HANDLE_SEMANTICS.md`
§4 found that **H3 (handle identifiers on profile pages) directly contradicts
SD-021.2**: every identifier requires an `observed_at`, a profile page has no post
timestamp, and SD-021 forbids substituting the join date, the latest post, or
collection time. H1 removes that contradiction rather than managing it. **Had H2 or
H3 been chosen, SD-021 and SD-022 would be in conflict today.**

### 1.2 Remaining handle/timestamp contradictions

**None between the two decisions.** One **latent constraint** they jointly create is
not stated in either:

> Because every identifier object requires an `observed_at`, and because SD-021
> gives `profile` and `index` artifacts no legitimate timestamp, **a `profile` or
> `index` page must carry no extractable identifier at all** — otherwise the artifact
> cannot be emitted in conformance.

The Phase-4 corpus satisfies this: profile pages render only post links, index pages
only titles, handles and dates. Neither renders a PGP block or a wallet. But **it is
satisfied by how the pages happen to be written, not by any asserted rule.** A future
edit to `mock_sites/` could break conformance silently.

This was recorded in SD-021's residual list; it is repeated here because it is a
*joint* consequence and belongs in the amendment, not only in a decision record.
→ **CAN BE RESOLVED DURING SPEC AMENDMENT**, plus a Phase-5 test.

### 1.3 Does the reserved `handle` enum create contract ambiguity?

**A mild one, and it is worth closing at amendment time.**

`DATA_MODEL.md` §2 lists `handle` and `contact` as valid `Identifier.type` values,
while SD-022 says neither is ever emitted and SD-022.3 declines to narrow the enum.
The result is a **permissive-but-unused** type set: a validator built from the enum
would accept a `handle` identifier that the scraper never sends.

That is not a contradiction — a closed enum may legitimately contain values no
current producer emits — but it invites a future implementer to infer that handles
*are* emitted. One sentence in `API_CONTRACT.md` §3 stating that Phase 5 emits only
`pgp_fingerprint` and `wallet` closes it.
→ **CAN BE RESOLVED DURING SPEC AMENDMENT**

---

## 2. SD-021 × SD-023 — page types against the URL form

### 2.1 Does `page_type` affect URL requirements?

**No.** SD-023's form `http://<mock-host>/<path>` is uniform across all three page
types. The two decisions are orthogonal, which is the desirable outcome: a validator
does not need `page_type` to check `url`, nor `url` to check `page_type`.

### 2.2 Are index and profile URLs representable under U2?

**Yes, all 57.**

| Type | Example | Note |
|---|---|---|
| `index` | `http://alpha7fq2mx9k.onion.mock/` | Path is `/` |
| `item` | `http://alpha7fq2mx9k.onion.mock/thread/14` | Matches `API_CONTRACT.md` §3's worked example modulo the scheme |
| `profile` | `http://forum-gamma-host/user/nightjarr` | Straightforward |

### 2.3 Trailing slash

**Determined by SD-023's own rules, but not stated.** Rule 4 requires a route path;
`http://alpha7fq2mx9k.onion.mock` has none. Therefore the index form must be
`http://alpha7fq2mx9k.onion.mock/` with the slash. This is a derivation from rule 4,
not a new choice — but it should be written down, because `.../` versus `...` are
different strings and three artifacts per run depend on it.
→ **CAN BE RESOLVED DURING SPEC AMENDMENT**

### 2.4 Is `Artifact.url` = "mock-site path" a blocking contradiction?

**Yes. BLOCKS FREEZE — and SD-023 says so itself**, not merely as this review's
inference:

> *"SD-023 resolves the ingest boundary representation … It does not resolve the
> ownership or wording of the stored `Artifact.url` field, which remains a
> contract/data-model wording question to be reconciled **before contract freeze**."*

`DATA_MODEL.md` §2 line 51 still reads `url | str | mock-site path`. Read strictly,
"path" means `/thread/14` — no host, no scheme — which is incompatible with both
`API_CONTRACT.md`'s existing host requirement and with SD-023.

Freezing a contract while its own stated authority describes the field differently
would freeze the contradiction, not resolve it.

---

## 3. SD-021 × identifier semantics

### 3.1 Can every Phase-4 page produce a conforming payload?

**Verified against the corpus, not asserted.** Counted directly from
`mock_sites/seed_data.py`:

```
forum-alpha        index=1 items=16 profiles=2  -> 19
marketplace-beta   index=1 items=16 profiles=2  -> 19
forum-gamma        index=1 items=16 profiles=2  -> 19
TOTAL artifacts = 57   (index=3, item=48, profile=6)
distinct (handle, source_id) personas = 6
```

**57 artifacts, 6 personas, no phantom personas.** Index artifacts create none
(SD-021: `persona` absent). Mentioned handles create none (SD-022.4). The 6 personas
come from 48 item and 6 profile artifacts collapsing onto 6 distinct
(`handle`, `source_id`) pairs, exactly as `DATA_MODEL.md` §2's uniqueness constraint
requires.

### 3.2 Are `identifiers[]` semantics satisfiable for every page type?

**Yes as the corpus stands**, subject to §1.2's latent constraint:

| Type | Count | `identifiers[]` | `observed_at` available? |
|---|---|---|---|
| `index` | 3 | `[]` | n/a — none emitted |
| `item` | 48 | PGP and/or wallet where planted | Yes — the post timestamp |
| `profile` | 6 | `[]` | n/a — none emitted |

`API_CONTRACT.md` §3 already declares an empty `identifiers` array normal, so the 9
index and profile artifacts are conforming.

### 3.3 A contradiction none of the four decisions records — counterparty wallet attribution

**This is new to this review and it is the most serious finding in it.**

A scan of the corpus for identifiers appearing on a page belonging to a *different*
persona returns **exactly one** result:

```
WALLET  marketplace-beta/44  by bellwether  carries wallet of ['nightjar', 'n1ghtjar_']
```

That is D1's listing 44, which `MOCK_SITES_SPEC.md` §5 **requires**: *"D1: at least
one post referencing A2's wallet as a counterparty, phrased as a transaction, not as
its own address."* The corpus is correct. The problem is downstream of it.

**The chain:**

1. `SCRAPER_AGENT_SPEC.md` §4's wallet rule is a regex over the page. It matches
   `1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6` on listing 44.
2. `DATA_MODEL.md` §2 gives every `Identifier` a required `persona_id` FK. The only
   persona for that artifact is **D1**.
3. So a spec-conformant scraper emits *A2's wallet as D1's identifier*.
4. `DATA_MODEL.md` §3 scores **"Identical wallet address → 0.45, supporting"**, and
   a relationship is created at **≥ 0.30**.
5. D1 and A2 would therefore receive a **`same_actor_suspected`** edge at 0.45.

**`DATA_MODEL.md` §4, Actor D says the opposite, in bold:** *"Creates a
`transacted_with` edge only. **Must not produce `same_actor_suspected`.**"*

**Nothing in the current specifications resolves this.** SD-022.4 covers *mentioned
handles* — a handle in another persona's content is not that persona's identifier —
but says nothing about mentioned **wallets**, and the regex cannot distinguish "my
address" from "I paid this address". The disclaiming sentence in listing 44 ("*That
address is theirs, not mine*") is prose the extractor does not read, and
`SCRAPER_AGENT_SPEC.md` §4's rule-based-only constraint means it never will.

**This is not a Phase-4 defect** — the corpus follows `MOCK_SITES_SPEC.md` exactly,
and `tests/test_phase4.py` asserts the disclaimer is present. It is a gap in the
**extraction-attribution rule**, of the same class as OPEN-5 but not covered by it.

**It is not resolved here.** It needs a human decision, and at least three shapes are
available without inventing anything: extend SD-022.4's principle to all identifier
types; add a counterparty/ownership distinction to the payload; or accept the edge
and amend `DATA_MODEL.md` §4's expected output. Each has different consequences for
the demo's headline claims.

**Classification: BLOCKS FREEZE.** Freezing `identifiers[]` while what it means to
attribute an identifier to a persona is undefined would freeze an ambiguity that
produces a wrong graph — and it would do so *silently*, since the payload validates
either way.

---

## 4. SD-022 × future GOTHAMITE entity resolution

*No GOTHAMITE implementation exists; this assesses only whether the specified data
would suffice.*

### 4.1 Is `persona.handle` sufficiently represented?

**Yes.** It appears on 54 of 57 artifacts — all 48 `item` and all 6 `profile`. The 3
`index` artifacts carry none, and need none: `Persona` is unique on
(`handle`, `source_id`), and every persona is established by its own posts. Index
pages' `raw_content` still contains the handles verbatim, so no information is
destroyed.

### 4.2 Does H1 remove any required evidence?

**No.** `DATA_MODEL.md` §3's only handle-based signal is *"Handle similarity
(Levenshtein ≤ 2)"*, computed **between `Persona.handle` values**, which H1 leaves
fully populated. No `Identifier` row is needed for it. `DATA_MODEL.md` §1 rule 2
(*"every derived claim traces to an artifact"*) is satisfied because the persona is
derived from artifacts that each carry `persona.handle`.

### 4.3 Are PGP and wallet sufficient for the Phase-4 linkage scenarios?

| Scenario | Signals | Expected | Sufficient? |
|---|---|---|---|
| A1 ↔ A2 | shared PGP 0.70 + shared wallet 0.45 → capped | 0.95 very strong | **Yes** |
| B1 → B2 | shared wallet 0.45 + temporal succession 0.15 | 0.60 strong | **Yes** |
| C1 vs A1 | handle similarity 0.05 + activity overlap −0.30 | below threshold, no edge | **Yes** — and it depends on H1 leaving `Persona.handle` intact |
| D1 → A2 | should be `transacted_with` only | no `same_actor_suspected` | **NO — see §3.3** |

Three of the four demo scenarios are sound under the proposed decisions. The fourth
is broken by §3.3.

---

## 5. SD-023 × the API contract

### 5.1 Can U2 be stated without redefining GOTHAMITE's stored data model?

**Yes.** SD-023 constrains a field of the `POST /api/v1/ingest` **request body**,
which is `API_CONTRACT.md`'s own scope — §1 calls it *"the only point of contact
between the two repos"*. Stating the wire form says nothing about how GOTHAMITE
stores it, and per SD-014 this repository has no authority over that.

### 5.2 The exact wording conflict to resolve before freeze

Two sentences, currently incompatible:

- `API_CONTRACT.md` §3: `url` | yes | *"Including the `.onion.mock` host"* — plus
  SD-023's scheme requirement.
- `DATA_MODEL.md` §2 line 51: `url` | str | *"mock-site path"*.

Resolution requires a human choice between two readings, and this review does not
make it:

1. **Amend `DATA_MODEL.md`** so `Artifact.url` describes the same absolute URL —
   simplest, and keeps the evidence locker's value identical to what was sent.
2. **Scope-split**: `API_CONTRACT.md` governs the transmitted value,
   `DATA_MODEL.md` governs the stored one, with normalisation between them. Coherent,
   but it makes stored ≠ sent, which sits awkwardly with an *"evidence locker"* whose
   defining property is verbatim retention.

Reading 2 also runs into the authority ambiguity in §8.2 — deciding it requires
knowing whose model `Artifact` belongs to.

---

## 6. SD-024 × the existing relay decisions

Every prior relay-layer decision, assessed for what D2+E2 does to it:

| Decision | Status under SD-024 | What must happen |
|---|---|---|
| **SD-001** — HTTP/1.1 `POST /relay` per hop | **AMENDED (narrowed)** | Transport unchanged. Its use of non-2xx as the *protocol* signal is retired; non-2xx survives only where a relay cannot seal (SD-024 §E) |
| **SD-002** — response envelope `{nonce, ciphertext}` | **AMENDED in substance, twice** | (a) Wire shape unchanged — good. (b) *"what falls out of the innermost envelope is the raw HTTP response"* becomes **false**: a typed object carrying it falls out. (c) *"each upstream relay seals the JSON bytes of the envelope it received"* becomes **false**: it seals a `relay` wrapper containing base64 of those bytes |
| **SD-003** — `request_id` relay-local, off the wire | **MERELY REFERENCED** | Unaffected. §7's "keyed by `request_id`" remains a local-correlation statement |
| **SD-011** — failure propagation, `reported_by`, `HOP_TIMEOUT` | **PRESERVED, NARROWED** | Rewriting applies to exactly one adjacency — the predecessor of a relay that could not decrypt. Its recorded *"known deviation"* is retired **on adoption**, not now |
| **SD-021 / SD-022 / SD-023** | **UNAFFECTED** | All three are ingest-boundary. Relay errors never reach the ingestion seam: `SCRAPER_AGENT_SPEC.md` §6 skips a failed page rather than POSTing it |

**No prior decision is contradicted.** Two require amendment (SD-001, SD-002), one is
narrowed (SD-011), one is untouched (SD-003).

---

## 7. SD-024 × the Phase-1 implementation and tests

### 7.1 A behavioural change worth flagging before it surprises anyone

Under the pre-E2 build, each relay rewrote `reported_by` to itself as a plaintext
error propagated upstream, so **the client always saw the entry relay**. Under E2 the
detecting relay seals its error and upstream relays cannot read it, so **the client
sees the relay that actually detected the failure**.

> **Corrected 2026-09-08 — documentation only; the invariant is unchanged.** The
> sentence that stood here said *"for a middle-hop failure the named relay changes from
> `path[0]` to `path[1]`."* That is wrong as stated, and the implementation showed why.
> Two different failures were being conflated:
>
> - **An unreachable successor.** The relay that *detects* it is the one **before** it.
>   A failure at `path[1]` is therefore detected and reported by **`path[0]`** — the
>   same relay as before E2. What changed is only how the report travels: sealed rather
>   than plaintext. Verified by
>   `tests/test_phase1.py::TestSealedErrorAtEveryPathLength` at 2, 3, 4 and 5 hops,
>   which asserts `reported_by` is the hop before the broken one and that the broken
>   relay is never named.
> - **A relay that cannot decrypt** — SD-029's case. That relay holds no key, so it
>   cannot seal its own error and answers its predecessor in plaintext. The
>   **predecessor** then reports, naming itself. Here the reporting relay genuinely is
>   one hop further along than the pre-E2 behaviour would have produced, because the
>   relay that failed cannot speak for itself.
>
> **The invariant is untouched in both cases: the failed downstream relay is never
> named**, and `reported_by` means the reporter, not the failer (SD-024 §D).

### 7.2 Tests that become invalid

| Test | Why | Property still valid? |
|---|---|---|
| `TestFailureHandling::test_unreachable_middle_relay_raises_a_controlled_error` | Asserts `reported_by={path[0].relay_id}` — becomes `path[1]` per §7.1; error text now comes from a decrypted object | **Yes** — including `assertNotIn(path[2].relay_id, message)` |
| `TestFailureHandling::test_unreachable_destination_raises_a_controlled_error` | Same; the exit relay is now named rather than the entry | Yes |
| `TestEndToEnd` — assertions depending on fixed-depth unwrap | `unwrap` iterates `len(session_keys)` and treats the last decryption as raw bytes; both assumptions are replaced by the terminal-type rule | Yes |

### 7.3 Tests that remain valid unchanged

`test_unreachable_entry_relay_raises_a_named_error` and
`test_directory_unreachable_fails_with_a_clear_error` (both client-side);
`TestInvalidInput`'s garbage-fed-relay test — **SD-024 §E preserves the non-2xx
plaintext response for a relay that cannot decrypt**, which is exactly that case;
`TestNonceDiscipline`, `TestLogHygiene`, `TestLayerConstruction`, `TestRegistration`,
`TestPathSelection`; and **all 41 tests in `tests/test_phase4.py`** — unaffected by
SD-024, though **SD-027 separately deletes one of them (41 → 40)** and requires
Phase-4 re-verification.

### 7.4 Implementation changes required

- `relay/relay_node.py` — emit `relay` / `success` / `error` typed content; seal
  errors when a key is held; on receiving a non-2xx plaintext error from a successor,
  emit its own sealed error per SD-011.
- `client/onion_client.py` — `unwrap` branches on `type` rather than counting;
  classify the four outcomes of SD-024 §G.
- `common/onion_crypto.py` — **no change.**

### 7.5 Are any cryptographic primitives affected?

**None.** AES-GCM parameters, nonce generation and the fresh-nonce-per-encryption
rule, RSA-OAEP forward key delivery, and retained-`K` return sealing are all
unchanged. SD-024 changes **which bytes are sealed, not how**. The forward path
(§5.1, §5.2, §5.3) is entirely untouched.

---

## 8. Authority audit

### 8.1 Where authority is clear

| Domain | Authority | Basis |
|---|---|---|
| Relay protocol | `RELAY_PROTOCOL.md` | Line 7: *"the authoritative spec for the routing layer. If code and this document disagree, this document is correct"* |
| Mock-site behaviour | `MOCK_SITES_SPEC.md`, conforming to `DATA_MODEL.md` | `DATA_MODEL.md`'s authority line names it explicitly |
| Scraper behaviour | `SCRAPER_AGENT_SPEC.md` | No explicit clause, but no competing document |
| Sandbox seed data | `DATA_MODEL.md` §4 | SD-014 |

### 8.2 Where authority is currently ambiguous

**Two places, and they are the root of the freeze blockers.**

**(a) `API_CONTRACT.md` defers to a document that does not exist.** Line 4: *"Conforms
to: GOTHAMITE `docs/DATA_MODEL.md` — that file is authoritative. If this contract and
the data model disagree, the data model wins and this file gets corrected."* Per the
SD-021 project-state clarification, no GOTHAMITE repository is present in this
workspace or the owning account. **The contract's stated authority is missing.**

> **RESOLVED by SD-025 (proposed) — O2.** `API_CONTRACT.md` is self-authoritative for
> the wire format; GOTHAMITE's model keeps authority over GOTHAMITE's storage and the
> sandbox model over sandbox ground truth; neither overrides the boundary. A
> disagreement becomes a change request against the contract, not an automatic
> override.
>
> The review missed one thing worth recording: **this was not a fresh ambiguity.**
> SD-014 — already **in force** — states that the two models *"must remain compatible
> at the API boundary, which is `AgentsDocs/API_CONTRACT.md`. Neither repository owns
> the other's model."* Line 4 subordinates that boundary to one side's internal model,
> so SD-014 and line 4 were already in tension; line 4 was simply never updated. The
> missing GOTHAMITE file made the tension visible rather than causing it.
>
> `API_CONTRACT.md` is **unedited**; the wording change lands at freeze.

**(b) Whether `Artifact.url` is sandbox or GOTHAMITE model.** SD-014 gives the local
`DATA_MODEL.md` authority over *"the sandbox data model"* but expressly not over
GOTHAMITE's ingestion representation — and `Artifact` is an entity GOTHAMITE stores.
SD-014's wording does not determine which side it falls on. This is exactly what
blocks §5.2's resolution.

> **NARROWED, NOT RESOLVED, by SD-025.** With the contract self-authoritative, the
> **transmitted** `url` is settled by SD-023 and is no longer in question. What
> remains open is what the **stored** `Artifact.url` should say and which model owns
> that entity. **A1 still blocks freeze.**

**On the missing counterparty:** the recorded architecture (SD-021's project-state
clarification) is *finalise the contract first, then implement GOTHAMITE against it*,
so GOTHAMITE's absence **does not block a freeze**. But absence is **not agreement**,
and freezing must be an explicit human act — not something inferred from there being
nobody to object.

---

## 9. Freeze-readiness classification

Every remaining issue, in exactly one class.

### A. BLOCKS FREEZE

> **All three resolved as of 2026-09-07 (SD-025, SD-026, SD-027 — all PROPOSED, not
> in force). No blocker remains. The freeze is a human act that may now proceed once
> the §10 amendments are applied.**


| # | Issue | Source |
|---|---|---|
| ~~**A1**~~ **RESOLVED** | ~~`Artifact.url` = "mock-site path" vs the contract's host+scheme requirement.~~ **Closed 2026-09-07 by SD-026 (W2, proposed):** §2/§3 scope-marked descriptive, `Artifact.url` corrected to the absolute URL. Moves to **B10** below — the edit is an amendment-time task | SD-023's own text; §2.4, §5.2 |
| ~~**A2**~~ **RESOLVED** | ~~`API_CONTRACT.md`'s authority clause points at a non-existent GOTHAMITE `docs/DATA_MODEL.md`.~~ **Closed 2026-09-07 by SD-025 (O2, proposed):** the contract is self-authoritative for the wire format. Moves to **B9** below — the line-4 edit is an amendment-time task. A1 is now *decidable*, but still undecided | §8.2 |
| ~~**A3**~~ **RESOLVED** | ~~Counterparty identifier attribution (D1 → A2's wallet).~~ **Closed 2026-09-07 by SD-027 (T5, proposed):** A2's wallet removed from listing 44; Actor D's transaction scenario withdrawn. Moves to **B11** below. Root ambiguity dormant, not resolved | §3.3 |

### B. CAN BE RESOLVED DURING SPEC AMENDMENT

> **APPLIED.** B1–B3 and B5–B12 landed 2026-09-07 at the freeze. **B4** (SD-029) and
> **B13** (SD-030) landed 2026-09-08 under OPEN-9 — specification, implementation and
> tests together. **All thirteen items are done.** Both decision records remain
> **IN FORCE as of 2026-09-08**, adopted after verification. Three bookkeeping
> corrections were made to this list in the course of applying it, recorded here rather
> than silently:
>
> 1. **SD-028 had no B-item.** This review predates it. Its `DATA_MODEL.md` §2 edits
>    were folded into **B10** so §2 is touched once, and its corpus rule and guard
>    test became a new **B12**.
> 2. **B11's `(41 → 40)` was wrong.** SD-027's R2 addendum adds a replacement test,
>    so the net across B11 and B12 is **41 → 42**, not 41 → 40.
> 3. **SD-030 had no B-item either**, for the same reason — it postdates this review,
>    having been found while deciding B4. It is added below as **B13**.

| # | Issue | Status |
|---|---|---|
| B1 | Index-page trailing slash — determined by SD-023 rule 4, needs stating (§2.3) | **DONE** — `API_CONTRACT.md` §3, `url` rule 3 |
| B2 | Normative constraint that `index` and `profile` pages carry no extractable identifier (§1.2) | **DONE** — `MOCK_SITES_SPEC.md` §2 rule 7, restated in `API_CONTRACT.md` §3 and `SCRAPER_AGENT_SPEC.md` §4 |
| B3 | One sentence in `API_CONTRACT.md` §3: Phase 5 emits only `pgp_fingerprint` and `wallet`; `handle` and `contact` are reserved (§1.3) | **DONE** — §3, "Which identifier types are actually emitted" |
| B4 | Whether the plaintext non-2xx body of SD-024 §E carries a `code` — SD-024 residual 1 | **DONE** — **SD-029 (P3)** adopted and verified 2026-09-08; spec, code and tests landed under OPEN-9, which is now closed |
| B5 | Exact amendment wording for `RELAY_PROTOCOL.md` §6, §7, §9 | **DONE** — §6 error branch, §7 typed-content table, new §§9.1–9.5 |
| B6 | SD-002's two false consequences and SD-001's retired protocol signal (§6) | **DONE** — both annotated in `SPEC_DECISIONS.md`, neither reversed |
| B7 | `API_CONTRACT.md` §3 and `README.md` §4 examples still show the scheme-less `url` | **DONE** — both examples now absolute, both gained `page_type` |
| B8 | `MOCK_SITES_SPEC.md` §5's B1/B2 "strictly before/after" bullets, inconsistent with `DATA_MODEL.md` §4 — recorded in SD-018, document never corrected | **DONE** — bullets now give SD-018's exact boundary timestamps |
| B9 | **`API_CONTRACT.md` line 4** — replace the deferral clause with SD-025's wording | **DONE** |
| B10 | **`DATA_MODEL.md` §2** — SD-026's scope sentence and the `Artifact.url` row, **plus SD-028's `persona_id` gloss and attribution scope note** | **DONE** |
| B11 | **SD-027 + R2** — `mock_sites/seed_data.py` listing 44; `MOCK_SITES_SPEC.md` §5; `DATA_MODEL.md` §4 Actor D and summary table; `tests/test_phase4.py`; `PHASE_4_REPORT.md` re-run | **DONE** |
| B12 | **SD-028** — `MOCK_SITES_SPEC.md` §2 rule 6 and the rendered-page guard test | **DONE** |
| B13 | **SD-030** — `unusable_layer` as the fourth closed protocol error code: SD-024 §C, `RELAY_PROTOCOL.md` §6 and §9.1 | **DONE** — **SD-030 (M1)** adopted and verified 2026-09-08; spec, code and tests landed under OPEN-9, which is now closed |

**B4, why it was deferred, and how it was answered.** SD-024 §E retains a plaintext
non-2xx response for the one case where a relay holds no key and cannot seal anything.
Whether that plaintext body carries a `code` from the closed set was a **protocol
design question inside OPEN-9's implementation scope**, so deciding it at amendment
time would have been inventing protocol semantics rather than applying a recorded
decision. It was deferred, and `RELAY_PROTOCOL.md` §9.3 was written to state the
deferral explicitly, so the gap sat in the authoritative document rather than only in
this review.

> **DECIDED 2026-09-07 — `SPEC_DECISIONS.md` SD-029 (option P3).** The plaintext
> fallback carries `HTTP 400` and a body of exactly
> `{"error": "decryption_failure", "reported_by": "<own relay_id>"}`.
> `decryption_failure` is the **only** permitted value there, because the other two
> §C codes are unreachable in a channel that exists only when the relay holds no key.
> The response travels exactly one hop and is never forwarded as protocol content; it
> carries no downstream identity, destination, path position, `request_id`, or
> decryption diagnostics. **SD-024 §E is the only section amended, and SD-024 residual
> 1 is closed.** §C is untouched — it governs the field `code`, and this body's field
> is `error`. Analysis: `AgentsDocs/reports/B4_DECISION_BRIEF.md`.
>
> **B4 is now discharged.** Under OPEN-9 on 2026-09-08, `RELAY_PROTOCOL.md` §9.3 was
> amended to define the fallback body, `relay/relay_node.py` and
> `client/onion_client.py` were changed to match, and `tests/test_phase1.py` gained six
> tests covering it. **SD-029 was adopted on 2026-09-08** by explicit human decision,
> after verification at Phase 1 61/61, Phase 4 42/42 and combined 103/103. It is
> **IN FORCE**.

**B13, and why it is not in the original list.** SD-030 postdates this review. It was
found while deciding B4: `relay_node.py:137` returns a plaintext `400` for a layer that
**decrypted successfully** but proved structurally unusable, and SD-024's closed
three-code set had no value for that condition. B4 could not absorb it — B4 concerns
the *unsealed* channel, this concerns the *sealed* one — so it is tracked separately.

> **DECIDED 2026-09-07 — `SPEC_DECISIONS.md` SD-030 (option M1).** `unusable_layer` is
> added as the **fourth** closed protocol error code.
>
> **Trigger, precisely.** After the relay has **successfully decrypted and
> authenticated its own layer**, it cannot use it: `next_port` cannot be coerced to an
> integer, or `payload` cannot be decoded as base64. Everything earlier — a bad base64
> field, a wrong nonce length, a failed RSA unwrap, a failed AES-GCM tag, unparseable
> JSON, a missing required field — is caught inside `open_layer` and is a
> **decryption failure**, not this. Because the GCM tag has already verified the
> plaintext, the layer came from whoever holds `K`: this is a client construction
> fault, never attacker-injected.
>
> **The relay holds the key and therefore MUST seal**, per SD-024 §A/E2 — no exception,
> and no discarding of the key to avoid the obligation. The response is **HTTP 200**,
> per §E's first bullet, because a sealed envelope is returned:
>
> ```json
> { "type": "error", "code": "unusable_layer", "reported_by": "<detecting relay>" }
> ```
>
> **Amends SD-024 §C** (closed set 3 → 4) **and `RELAY_PROTOCOL.md` §6 and §9.1** —
> §6 to make the validation boundary explicit in the pseudocode, §9.1 to change
> "closed set of three" to "four", add the code, state that it maps to no §9 bullet,
> and distinguish it from the `malformed_response` exclusion two paragraphs above it.
> The name is deliberately **not** `malformed_layer`, which would sit one word from
> that exclusion and be misread. Analysis:
> `AgentsDocs/reports/LAYER_MALFORMED_DECISION_BRIEF.md`.
>
> **SD-024 residual 3 remains OPEN and unchanged.** *"Malformed responses remain
> permanently uncodeable"* concerns a **successor's response** — relayed content, which
> no relay parses and none is positioned to detect. SD-030 concerns a relay's **own
> authenticated layer**, which the protocol requires it to parse. They are different
> conditions in different channels, and SD-030 neither closes nor contradicts residual
> 3.
>
> **B13 is now discharged.** Under OPEN-9 on 2026-09-08, `RELAY_PROTOCOL.md` §6 and
> §9.1 were amended, `relay/relay_node.py` now seals `unusable_layer` with HTTP 200 and
> no longer emits `layer_malformed`, and `tests/test_phase1.py` gained six tests
> covering it. **SD-030 was adopted on 2026-09-08** by explicit human decision, after
> verification at Phase 1 61/61, Phase 4 42/42 and combined 103/103. It is
> **IN FORCE**.

### C. POST-FREEZE IMPLEMENTATION DETAILS

C1 relay typed-response emission · C2 client typed-response parsing · C3 Phase-1 test
rewrites (§7.2) · C4 `scraper/` construction · C5 `SCRAPER_AGENT_SPEC.md` §7's
run-summary counts, whose illustrative figures do not reconcile with the corpus ·
C6 re-running and re-reporting Phase 1

### D. FUTURE / OUT OF SCOPE

D1 mentioned handles as a signal (SD-022.4) · D2 `contact` semantics (SD-022.2/.3) ·
D3 malformed-response codeability under a future design that has relays parse
relayed content · D4 HTTPS (SD-023 rule 7) · D5 narrowing the Identifier enum
(SD-022.3) · D6 OPEN-8's `format/AGENT_TASK_SPLIT.md` sequencing note

---

## 10. Proposed specification amendment order

> **PERFORMED 2026-09-07**, in the order below. Steps 1–3 were already decided;
> steps 4–8 have now been applied. `SCRAPER_AGENT_SPEC.md` (step 6) is not a B-item
> but is part of this sequence, and was amended with the page-type mapping, the
> identifier-emission rules and the attribution rule. **Step 7 flipped SD-021, SD-022,
> SD-023, SD-025, SD-026, SD-027 and SD-028 to IN FORCE and closed OPEN-4, OPEN-5 and
> OPEN-6.** SD-024 is **not** in force: its specification landed, its implementation
> did not, and OPEN-9 stays open.

Ordered so each step's authority is settled before it is relied on.

1. ~~**Resolve A2**~~ — **DONE (SD-025, proposed).** The clause is decided; applying
   the replacement wording to `API_CONTRACT.md` line 4 is now amendment task **B9**,
   folded into step 5.
2. ~~**Resolve A1**~~ — **DONE (SD-026, proposed).** Applying the scope sentence and
   the corrected `Artifact.url` row to `DATA_MODEL.md` §2 is now amendment task
   **B10**.
3. ~~**Resolve A3**~~ — **DONE (SD-027, proposed).** Applying it is amendment task
   **B11**: six files, including `mock_sites/seed_data.py` and a Phase-4 test.
   **Sequence B11 last among the ingest-boundary edits and re-verify Phase 4
   immediately after**, since it is the only task that changes verified content.
4. **Amend `RELAY_PROTOCOL.md`** (B5) — §6 error branch, §7 typed content, §9 code set
   and timeout mapping. **Independent of steps 1–3 and may proceed in parallel**;
   it is the authoritative document for SD-024 and must land before any relay code.
5. **Amend `API_CONTRACT.md` §3** — `page_type` (SD-021), the `url` rule and trailing
   slash (SD-023, B1), the identifier-type note (B3), the no-identifiers constraint
   (B2), and the examples (B7).
6. **Amend `SCRAPER_AGENT_SPEC.md`** — page-type mapping, handle/identifier emission
   rules (SD-022), §8 criteria.
7. **Update `SPEC_DECISIONS.md`** — SD-001, SD-002 consequences (B6); SD-011 narrowed;
   SD-021…SD-024 flipped from proposed to in force; OPEN-4, OPEN-5, OPEN-6 closed on
   freeze; **OPEN-9 closed only after step 11's verification**.
8. **Correct `MOCK_SITES_SPEC.md` §5** (B8).

---

## 11. Regression plan

After the specification and code changes, before closing OPEN-9:

```bash
python -m unittest tests.test_phase1 -v          # rewritten failure tests + all others
python -m unittest tests.test_phase4 -v          # 42/42 after B11 + B12
python -m unittest tests.test_phase1 -v          # 61/61 after OPEN-9
python -m unittest discover -s tests -t . -v     # full suite
python -m scripts.phase1_demo                    # visibility table on real bytes
python -m scripts.phase4_demo                    # planted ground truth
docker compose -f docker-compose.yml -f mock_sites/docker-compose.sites.yml up -d --build
curl http://localhost/                           # MUST fail
docker compose run --rm --entrypoint python directory -m client.onion_client \
    --directory http://directory:8000 --hops 3 \
    --host alpha7fq2mx9k.onion.mock --resource /thread/14
```

**New tests required before OPEN-9 can close** — *all seven areas covered as of 2026-09-08; OPEN-9 closed*:

1. A sealed error opened correctly by the client at each of `hops=2..5`.
2. A relay asserted **unable to read** a sealed error from its successor — the
   property E2 exists for.
3. A middle-hop failure naming `path[1]` and **not** `path[2]` (§7.1).
4. A malformed layer classified as a **client-side** failure, not a relay error.
5. A destination-returned 404 classified as an **application success**, not a
   protocol error.
6. Nonce discipline re-verified across error layers — fresh nonce, no reuse.
7. Log hygiene re-verified on the error path: no keys, nonces, ciphertext,
   destination or payload content.

---

## 12. Phase-5 readiness

**Superseded in part on 2026-09-07.** The paragraph below described the state before
the amendments were applied; it is kept because its reasoning is what the amendments
answered.

> Adopting SD-021…SD-024 and completing OPEN-9 would make the **relay layer**
> deterministic. It would **not**, on its own, make the sandbox/GOTHAMITE boundary
> deterministic, because **A3 remains open**: what it means to attribute an identifier
> to a persona is undefined, and the one artifact that exercises it (listing 44)
> produces a graph edge the data model forbids. A scraper built today would emit a
> validating payload that yields a wrong answer — the failure mode that is hardest to
> detect.

**Current state.** The boundary *is* now determinate: SD-028 defines
`Identifier.persona_id` as ownership, `MOCK_SITES_SPEC.md` §2 rule 6 makes the corpus
guarantee it, and a rendered-page test enforces it. Listing 44 no longer carries A2's
wallet. What still blocks Phase 5 is **OPEN-9 alone** — the relay implementation does
not match the specification it was just given.

### Conditions required before authorising Phase 5

1. ~~**A1, A2, A3 resolved**~~ — **all three done** (SD-025, SD-026, SD-027, all proposed).
2. **The contract frozen** — an explicit act, not inferred from GOTHAMITE's absence.
3. **`API_CONTRACT.md` and `SCRAPER_AGENT_SPEC.md` amended** per steps 5–6.
4. **OPEN-4, OPEN-5, OPEN-6 closed** on freeze; SD-021, SD-022, SD-023 in force.
5. **OPEN-9 closed** — `RELAY_PROTOCOL.md` amended, implementation complete, §11's
   regression plan green.
6. **Phase-1 and Phase-4 suites both passing** after the relay changes.
7. **B1–B3 stated normatively**, since Phase 5 depends on all three directly.

Conditions 1–4 and 7 concern the ingest boundary; 5–6 the relay layer. **They are
independent and may proceed in parallel** — OPEN-9 needs no counterparty, while
A1–A3 need human decisions on the boundary.

---

**Status as of 2026-09-08.** **All thirteen B-items are applied** — B1–B3 and B5–B12
at the 2026-09-07 freeze, B4 and B13 under OPEN-9 the following day. **SD-029 and
SD-030 are IN FORCE**, and **OPEN-9 is closed**: all seven required test areas of §11
are covered, at Phase 1 61/61, Phase 4 42/42 and combined 103/103. `API_CONTRACT.md`, `DATA_MODEL.md`, `RELAY_PROTOCOL.md`,
`SCRAPER_AGENT_SPEC.md`, `MOCK_SITES_SPEC.md`, `SPEC_DECISIONS.md`, `README.md`,
`mock_sites/seed_data.py`, `scripts/phase4_demo.py` and `tests/test_phase4.py` all
modified. OPEN-4, OPEN-5 and OPEN-6 closed; **OPEN-9 open**; Phase 5 not started; no
commit.
