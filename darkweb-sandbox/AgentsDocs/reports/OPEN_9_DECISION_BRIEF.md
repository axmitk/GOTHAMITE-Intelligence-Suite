# OPEN-9 — Decision Brief

**Date:** 2026-09-07
**Status:** **DECIDED IN PRINCIPLE, NOT IN FORCE.** A human architectural decision
has since been recorded as `SPEC_DECISIONS.md` **SD-024** — **PROPOSED, NOT IN
FORCE**. It adopts **E2** (uniform layered sealing), which is this brief's §10
recommendation. `RELAY_PROTOCOL.md` has **not** been amended and nothing has been
implemented. The discriminator design is settled separately by
`OPEN_9_ERROR_ENVELOPE.md` (D2) and specified in `OPEN_9_FINAL_DEFINITION.md`.
**Blocks:** "Phase 2 onward; revisit before Phase 6 hardening" (as recorded).
**OPEN-9 remains open** until the spec is amended and the implementation and tests
are updated and verified.

Nothing was modified to produce this brief. `API_CONTRACT.md`, `DATA_MODEL.md`,
`SCRAPER_AGENT_SPEC.md`, `RELAY_PROTOCOL.md`, `mock_sites/` and all implementation
files remain untouched, and Phase 5 has not started. OPEN-4, OPEN-5 and OPEN-6 are
untouched. A human has since decided, so a proposal entry now exists in
`SPEC_DECISIONS.md` as **SD-024** — recorded, not adopted, not implemented.

---

## 1. The exact OPEN-9 ambiguity

From `AgentsDocs/SPEC_DECISIONS.md` §2, verbatim:

> **The error envelope is unspecified.** `RELAY_PROTOCOL.md` §5.2 defines the
> forward wire layer and §7 defines the return path, but neither defines what an
> *error* looks like on the wire. §9 says only "return an error" for three of its
> four cases, while the fourth — mock site unreachable — says the exit relay
> "returns an error response **through the normal return path**", which implies a
> sealed envelope for that case alone. The current Phase-1 build returns plaintext
> JSON with a non-2xx status at every hop, which deviates from that fourth bullet.
> Needs a human protocol decision: does an error travel sealed under the return-path
> layers, as a plaintext status, or sealed in some cases and plaintext in others —
> and if sealed, how does the client distinguish an error from a successful response
> before decrypting? SD-011's relay-identity invariant holds under any of those
> answers.

Two questions, and the second is the harder one: **what form does an error take on
the wire**, and **how does the client tell an error from a success**.

---

## 2. Documents and sections involved

| Document | Section | Relevance |
|---|---|---|
| `RELAY_PROTOCOL.md` | line 7 | *"This document is the authoritative spec for the routing layer. If code and this document disagree, this document is correct."* |
| `RELAY_PROTOCOL.md` | §5.2 | Forward wire layer: `{enc_key, nonce, ciphertext}`. No error variant |
| `RELAY_PROTOCOL.md` | §6 | Per-hop pseudocode and the **visibility table**. Has no error branch at all |
| `RELAY_PROTOCOL.md` | §7 | Return path: each relay seals with its retained `K` and a fresh nonce. Describes success only |
| `RELAY_PROTOCOL.md` | §8 | Logging rules. Permits naming the next hop; forbids logging keys, nonces, ciphertext, destination, payload contents |
| `RELAY_PROTOCOL.md` | **§9** | **The only normative text about failure.** Four bullets |
| `IMPLEMENTATION_PLAN.md` | §3 Phase 3, criterion 6 | *"A downed relay produces a clear named error, no hang"* |
| `SPEC_DECISIONS.md` | **SD-011** | Fixes `reported_by` to the emitting relay; explicitly defers the envelope to OPEN-9 |
| `SPEC_DECISIONS.md` | **SD-002** | Response envelope is `{nonce, ciphertext}` — no type or status field |
| `SPEC_DECISIONS.md` | **SD-001** | Transport is HTTP/1.1 `POST /relay` per hop — supplies the non-2xx status the current build uses |
| `SCRAPER_AGENT_SPEC.md` | §6 | *"Relay fails mid-request → Log naming the hop, skip that page, continue"* |

**Examples treated as non-normative**, per the instruction for this brief. This
costs OPEN-9 nothing: `RELAY_PROTOCOL.md` contains **no example of an error at
all**, in any section. The absence is total, not merely unmarked.

---

## 3. Contradiction, omission, or underspecification?

**Primarily an omission, containing one narrow contradiction.**

**(a) Omission — the dominant part.** §5.2, §6 and §7 define the success path
completely and never mention errors. §6's pseudocode has no error branch: it
decrypts, forwards or fetches, and returns `encrypt_response(response, K,
fresh_nonce)`. There is no path through that code for "something went wrong". The
error envelope is not underspecified — it is **absent**.

**(b) Contradiction — narrow but real.** §9's fourth bullet says the exit relay
*"returns an error response **through the normal return path**"*. The normal return
path is §7's sealed, layered one. The current build returns plaintext there. That is
a genuine contradiction between the specification and the implementation — already
recorded in SD-011 as a **known deviation**, not a new finding here.

**(c) Underspecification — the client side.** Even if sealing is chosen, nothing
says how the client distinguishes an error from a success. SD-002's response
envelope is `{nonce, ciphertext}` with no type field, so the distinction has
nowhere to live in the current format.

---

## 4. A decomposition the blocker's wording hides

OPEN-9 speaks of "an error" as one thing. §9's four bullets are **not** one thing,
and the difference is decisive. The question that separates them: **does the
detecting party still hold an AES key `K` with which it could seal anything?**

| §9 bullet | Detected by | Holds `K`? | Can the detector seal? | On the wire at all? |
|---|---|---|---|---|
| 1. Relay unreachable | The **predecessor** (or the client, if the entry relay is down) | **Yes** — its own forward-pass `K` | **Yes** | Yes, unless it is the entry relay |
| 2. Decryption failure | The **failing relay itself** | **No** — decryption is what failed | **No, structurally** | Yes |
| 3. Directory unreachable | The **client** | n/a | n/a | **No** — never on the relay wire |
| 4. Mock site unreachable | The **exit relay** | **Yes** | **Yes** | Yes |

Three findings follow, and they constrain the options more than the blocker's text
suggests:

- **Bullet 3 is out of scope entirely.** A directory failure happens before any
  layer is built. It is a client-side exception and no envelope decision touches it.
- **Bullet 2 cannot be sealed by the relay that detects it.** A relay that fails
  RSA-OAEP or AES-GCM decryption has no `K` — deriving one is exactly what failed.
  "All errors sealed by the detecting relay" is therefore **not an available
  option**; it is technically impossible, not merely undesirable.
- **Sealing is inherently partial.** Whatever is chosen, an error arising at hop *k*
  can be sealed by at most hops *1 … k−1*. A success carries `len(path)` layers; an
  error carries fewer. That asymmetry is unavoidable and drives the client-side
  question in §7.4 below.

---

## 5. Competing options

| | Rule | Bullet 4 satisfied? |
|---|---|---|
| **E1** | **Plaintext at every hop.** An error is a non-2xx HTTP response with a JSON body, propagated upstream unsealed, each relay rewriting `reported_by` | **No** — contradicts §9 bullet 4 |
| **E2** | **Uniform sealing.** *A relay always seals whatever it returns upstream, error or success.* A relay that cannot decrypt returns plaintext to its predecessor, which then seals it | **Yes** |
| **E3** | **Hybrid.** Bullet 4 sealed; bullets 1 and 2 plaintext | **Yes**, by construction |

E1 is the current build's behaviour. It is listed as an option, not as a baseline —
per the instruction, implementation behaviour is not evidence of intent.

---

## 6. Strongest evidence for each option

### For E1

- §9's bullets 1 and 2 say only "return an error" and constrain no form.
- SD-001 already establishes HTTP per hop, so a non-2xx status is available at no
  cost and needs no new machinery.
- It is the only option under which the client can detect failure **without
  decrypting anything**, which is the simplest possible client.
- `IMPLEMENTATION_PLAN.md` Phase 3 criterion 6 — *"a clear named error, no hang"* —
  is satisfied, as the passing Phase-1 suite demonstrates.

### For E2

- **It is the only option stated as a single rule with no case analysis:** *seal what
  you return.* §7 already says every relay seals what it returns; E2 is that
  sentence with the word "response" read to include error responses.
- It satisfies §9 bullet 4 — the **only normative statement in the repository about
  error transport** — without needing an exception clause.
- It closes an information leak that E1 leaves open. See §7.6; this is the strongest
  evidence for E2 and it is not recorded anywhere in the existing documents.
- It requires no change to SD-002's envelope: an error would be sealed in exactly
  the `{nonce, ciphertext}` form a success uses.

### For E3

- It is the **minimum change** that removes the recorded deviation: only bullet 4's
  behaviour moves, and bullets 1–2 keep the form §9 leaves unconstrained.
- It matches the literal reading of §9 most closely — the spec mandates sealing for
  exactly one case and is silent on the others, so a rule that mirrors that
  distribution is arguably the most faithful.

---

## 7. Effects

### 7.1 Relay behaviour

- **E1** — no change from the current build.
- **E2** — every relay's error path gains a sealing step. The relay that cannot
  decrypt still returns plaintext (§4), so a relay must handle *receiving* a
  plaintext error from its successor and sealing it before passing it up.
- **E3** — only the exit relay's destination-fetch failure changes; middle relays
  keep plaintext propagation.

Under all three, SD-011's `reported_by` rewriting is unchanged.

### 7.2 Client behaviour

- **E1** — none. The client reads a non-2xx status from the entry relay.
- **E2** — the client must unwrap a **variable number of layers** and detect that it
  has reached an error rather than the raw HTTP response. This is the substantive
  client change and the one genuinely unspecified point.
- **E3** — the client needs both paths: plaintext for hops, sealed for the
  destination case.

### 7.3 Scraper behaviour

**No effect under any option.** `SCRAPER_AGENT_SPEC.md` §6 requires only *"Log
naming the hop, skip that page, continue"*, which every option supports, since the
scraper consumes whatever exception `onion_client` raises rather than the wire form.

One pre-existing tension, **noted and not resolved here**: §6 says "naming the hop",
while SD-011 permits the client to learn only the last relay it successfully
reached. That tension is SD-011's, exists identically under all three options, and
OPEN-9 neither creates nor fixes it.

### 7.4 HTTP / API boundary

The **relay** HTTP boundary (SD-001's `POST /relay`) is affected: E1 and E3 use
non-2xx statuses as a signal; E2 could return `200` with a sealed error body, making
the HTTP status carry no protocol meaning.

The **GOTHAMITE** boundary is **entirely unaffected**. Errors never reach ingestion:
per `SCRAPER_AGENT_SPEC.md` §6 a failed page is *skipped*, not POSTed. No field of
`API_CONTRACT.md` §3 describes a relay error.

### 7.5 Data model

**No effect under any option.** `DATA_MODEL.md` has no entity, field or enum
representing a transport error. A failed fetch produces no Artifact.

### 7.6 Security and safety assumptions — the asymmetric consequence

**Under E1, error *codes* can leak destination information to relays not entitled to
it.** SD-011 requires each relay to rewrite `reported_by` to its own id. It says
**nothing about the error code**. So if the exit relay reports
`destination_unreachable` and that code propagates upstream in plaintext, the entry
relay learns that **the destination was unreachable** — a fact about the
destination, which §6's visibility table says relay A must not have ("Sees final
destination: **No**").

This is a real gap in the current arrangement, it is **not recorded in SD-011 or in
OPEN-9's text**, and it is the strongest single argument in this brief. Three ways
it could be closed, none chosen here: seal the error (E2), normalise every code to a
single opaque value before propagating, or extend SD-011 to require code rewriting
as well as `reported_by` rewriting.

Under E2 the leak does not arise: an upstream relay receives an opaque sealed blob
and learns only that *something* came back.

Against that, E2 has a modest counter-consideration: a sealed error means a relay
cannot distinguish an error from a success in transit, which removes a diagnostic
signal from the very logs §8 calls "a demo requirement". The detecting relay's own
log still names the failure, so what is lost is intermediate-hop visibility — which
is precisely what §6 says those hops should not have.

### 7.7 Tests

**This is the first OPEN blocker whose resolution would change existing, currently
passing code and tests.** OPEN-4, OPEN-5 and OPEN-6 all touch only unwritten Phase-5
work.

`tests/test_phase1.py::TestFailureHandling` asserts against the plaintext form
directly — for example that an exception message contains `next_hop_unreachable` and
`reported_by=<entry relay id>`, and does **not** contain the third relay's id. Under
E2 those assertions test a form that would no longer exist and would need rewriting
against the client-side exception instead of the wire body.

`tests/test_phase4.py` (41) is unaffected — it asserts page content and reachability.

**Consequence for the phase gates:** adopting E2 or E3 means re-running and partly
rewriting the Phase-1 suite. That does not invalidate the Phase-1 or Phase-4
reports, but it does mean OPEN-9 is not a documentation-only change, unlike the
three blockers decided before it.

### 7.8 Phase 5

**No blocking effect.** The scraper needs a named exception and no hang (§7.3), which
all three options provide. OPEN-9's recorded scope — *"Phase 2 onward; revisit before
Phase 6 hardening"* — remains accurate: it is a Phase-6 correctness item, not a
Phase-5 prerequisite.

---

## 8. Authority

**Clean, unlike OPEN-6.** `RELAY_PROTOCOL.md` line 7 states it outright:

> *"This document is the authoritative spec for the routing layer. If code and this
> document disagree, this document is correct."*

Errors between relays are routing-layer behaviour. `RELAY_PROTOCOL.md` therefore has
undisputed authority, and no other document competes for it — `DATA_MODEL.md` and
`API_CONTRACT.md` say nothing about transport errors, and the GOTHAMITE-side
authority question that complicates OPEN-4 and OPEN-6 does not arise.

The clause also settles the status of the current build directly: where the code and
§9 bullet 4 disagree, **the document is correct and the code is wrong**. That is a
statement about which side must change, not about which envelope to adopt.

---

## 9. Can OPEN-9 be resolved entirely within the sandbox?

**Yes, completely.** Every affected document and file is sandbox-owned:
`RELAY_PROTOCOL.md`, `SPEC_DECISIONS.md`, `relay/`, `client/`, `tests/`.

**No GOTHAMITE contract change is required** (§7.4). This is the only one of the four
open blockers that is entirely internal — OPEN-4, OPEN-5 and OPEN-6 are all
ingest-boundary questions. OPEN-9 needs no counterparty, and can therefore be decided
and adopted without waiting on the contract freeze that gates SD-021, SD-022 and
SD-023.

---

## 10. Recommendation

**A recommendation is supportable: E2 — uniform sealing.** Stated with the same
candour as the earlier briefs about what carries it and what does not.

1. **It satisfies the only normative statement about error transport.** §9 bullet 4
   is the sole sentence in the repository constraining the form of an error, and it
   requires the normal return path. E1 contradicts it; §8's authority clause says
   the document wins.
2. **It is one rule, not a case analysis.** *A relay seals whatever it returns
   upstream.* §7 already says relays seal what they return; E2 reads "response" to
   include error responses and adds no exception clause. E3 requires the
   implementation to branch on failure type, which is more surface for a mistake in
   the part of the system §1 calls "the entire point".
3. **It closes the §7.6 leak.** This is the argument I would put first on merit
   rather than on textual authority: E1 lets an intermediate relay learn that the
   *destination* was unreachable, which §6's table forbids. E2 removes the leak
   structurally rather than by remembering to normalise a string.

**What does not support it, stated plainly:**

- **E3 is textually defensible and cheaper.** §9 mandates sealing for exactly one
  case and is silent on two others; a rule mirroring that distribution is arguably
  the more faithful reading, and it changes less code.
- **E2 costs a rewrite of existing passing tests** (§7.7) and a real client change
  (§7.2). It is the only option here that is not free.
- **E2 does not answer the client-discrimination question.** §11 residual 1 remains
  open under it, and that question must be answered for E2 to be implementable at
  all.

**Confidence: moderate.** The textual evidence is genuinely thin — one bullet — and
the strongest argument (the code leak) is one this brief raises rather than one the
specifications make. A human choosing E3 would be reading §9 more literally than I
am, and would not be contradicting any document.

---

## 11. Residual ambiguities after each option

### Under E2 or E3 (any sealing)

1. **How does the client distinguish an error from a success?** *The central
   unresolved question.* SD-002's envelope is `{nonce, ciphertext}` with no type
   field. Candidate answers, none chosen: a marker inside the innermost plaintext; a
   new envelope field (**which would amend SD-002**); the HTTP status of the final
   hop; or inference from the layer count failing to match the path length. The last
   of these is fragile and is noted only for completeness.
2. **Variable layer depth.** An error sealed at hops 1…k−1 has fewer layers than a
   success. The client must stop unwrapping at the right point without treating a
   short stack as corruption.
3. **Does layer depth itself leak the failure position to the client?** It reveals
   which hop broke — which SD-011 explicitly permits the client to learn ("the last
   relay it successfully reached"), so this appears consistent. Recorded because it
   is the kind of inference that should be deliberate rather than incidental.
4. **What does a relay do when its successor returns something unparseable** — not a
   valid envelope and not a valid error? Undefined today under every option.

### Under E1

5. **The error-code leak (§7.6) stays open** and would need closing by another means
   — normalising codes, or extending SD-011.
6. **§9 bullet 4 stays contradicted**, so adopting E1 means *amending
   `RELAY_PROTOCOL.md` §9* to match, not merely recording a preference. E1 is the
   only option requiring the authoritative document to change.

### Under all options

7. **§6's pseudocode has no error branch.** Whichever option is chosen, §6 needs one
   added, or it will keep reading as though failures cannot occur.
8. **Timeout expiry is not in §9's list.** SD-011 introduced `HOP_TIMEOUT`, but §9
   enumerates four failure causes and a timeout is not among them. Which of the four
   a timeout is treated as — or whether it is a fifth — is undefined.

---

## 12. Effect on previously recorded decisions

| Decision | Affected? | Why |
|---|---|---|
| **SD-011** | **Yes, directly — and it anticipated this** | SD-011 fixes `reported_by` and explicitly defers the envelope to OPEN-9. Its relay-identity invariant holds under E1, E2 and E3 alike, so **no option contradicts it**. Adopting E2 or E3 would *retire* the "known deviation" SD-011 records; adopting E1 would require amending §9 instead. §7.6's code leak is a gap SD-011 leaves open and may warrant extending it |
| **SD-002** | **Conditionally** | Unaffected if the error/success distinction lives inside the innermost plaintext. **Amended** if a type or status field is added to the `{nonce, ciphertext}` envelope. Residual 1 decides this |
| **SD-001** | **Conditionally** | E1 and E3 give the non-2xx HTTP status protocol meaning; E2 could make every hop return `200` with a sealed body, leaving the status meaningless. Worth stating explicitly in whichever decision is taken |
| **SD-003** | No | `request_id` is relay-local and off the wire. Unchanged |
| **SD-021** | **No** | `page_type` is an ingest-payload field. Errors never reach ingestion (§7.4) |
| **SD-022** | **No** | Handle/contact identifier semantics. Ingest-side only |
| **SD-023** | **No** | Ingest payload `url` form. Ingest-side only |

**No previously recorded decision is contradicted by any OPEN-9 option.** The three
proposed-but-not-in-force decisions (SD-021, SD-022, SD-023) are all ingest-boundary
and entirely orthogonal to this one.

---

## 13. Dependencies on OPEN-4, OPEN-5, OPEN-6

**None, in either direction.**

Those three are all questions about the `POST /api/v1/ingest` payload — page types,
identifier semantics, and the `url` form. OPEN-9 is a relay-layer transport question
that never reaches the ingestion seam (§7.4, §7.5). OPEN-9 can be decided before,
after, or independently of them, and none of them is resolved or touched by this
brief.

---

## 14. Files that would eventually need modification

Under the recommended **E2**:

| File | Change |
|---|---|
| `AgentsDocs/RELAY_PROTOCOL.md` | §7 gains the error form; §6's pseudocode gains an error branch; §9 gains the cross-reference. **This is the authoritative document and the change belongs here first** |
| `AgentsDocs/SPEC_DECISIONS.md` | New SD entry; OPEN-9 annotated; SD-011's deviation note updated to point at it |
| `relay/relay_node.py` | Seal errors before returning upstream; handle a plaintext error received from a successor |
| `client/onion_client.py` | Unwrap variable depth; detect the error marker; raise `OnionPathError` as now |
| `common/onion_crypto.py` | Only if residual 1 is answered by adding an envelope field |
| `tests/test_phase1.py` | `TestFailureHandling` rewritten against the sealed form (§7.7) |
| `AgentsDocs/reports/PHASE_1_REPORT.md` | Deviation note and test count updated after re-running |
| `mock_sites/`, `tests/test_phase4.py`, `scraper/`, `API_CONTRACT.md`, `DATA_MODEL.md` | **No change** |

Under **E3**, the same list with narrower relay and client changes. Under **E1**,
`RELAY_PROTOCOL.md` §9 bullet 4 must be **amended** to match the implementation —
the only option that changes the authoritative spec to fit the code rather than the
reverse.

---

**Nothing above has been done.** No specification modified, no contract modified, no
implementation written, no `SPEC_DECISIONS.md` entry created, Phase 5 not started,
OPEN-4 / OPEN-5 / OPEN-6 untouched, no commit.
