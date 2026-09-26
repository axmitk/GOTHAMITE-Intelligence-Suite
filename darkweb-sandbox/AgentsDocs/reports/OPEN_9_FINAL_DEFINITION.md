# OPEN-9 — Final Protocol Definition (proposal text for SD-024)

**Date:** 2026-09-07
**Status:** **RECORDED AS SD-024 — PROPOSED, NOT IN FORCE, NOT IMPLEMENTED.**
This document's normative content was adopted as `SPEC_DECISIONS.md` **SD-024** on
2026-09-07, with two of its §12 items resolved by the decision: `code` is retained
(SD-024 §C) and the continuation type is named `relay` (SD-024 §B). See §13 below
for what changed and what remains open. `RELAY_PROTOCOL.md` has **not** been
amended, no code has been written, and **OPEN-9 remains open**.
**Inputs:** `OPEN_9_DECISION_BRIEF.md`, `OPEN_9_ERROR_ENVELOPE.md`,
`RELAY_PROTOCOL.md`, `SPEC_DECISIONS.md` (SD-001, SD-002, SD-003, SD-011).

Nothing was modified to produce this document. `RELAY_PROTOCOL.md`,
`relay/relay_node.py`, `client/onion_client.py`, `common/onion_crypto.py`, all
tests, all contracts and `mock_sites/` remain untouched, and Phase 5 has not
started. `SPEC_DECISIONS.md` now carries **SD-024** recording this proposal.

No cryptographic mechanism is invented or redesigned. Every construction below is
the one already fixed by `RELAY_PROTOCOL.md` §2, §5.2 and §7.

---

## 0. One structural finding that resolves two of the open questions

Under D2 + E2, **a relaying relay never parses what it relays.** It receives bytes
from its successor and seals those bytes; it does not decode them, does not validate
them, and cannot read them. `RELAY_PROTOCOL.md` §7 already says this — *"B encrypts
what it received"* — and SD-002 already treats the inner content as opaque bytes.

Two consequences follow, and both remove questions rather than answering them:

1. **No relay can ever detect a malformed successor response.** Malformation is
   therefore not a relay-generated protocol error and needs no wire code. It is
   detected only by the client, after decryption — a **client-side failure**, in the
   same category as "directory unreachable". This answers Q1's second half and Q7
   without inventing anything.
2. **A relay cannot leak what its successor reported**, because it cannot read it.
   The §7.6 leak identified in the first brief closes structurally.

This is the reason the proposal below keeps the `relay` wrapper carrying its inner
content as **base64 bytes** rather than as a nested JSON object: an object would
force every hop to parse, re-creating the detection point this design removes.

---

## 1. Error taxonomy — three codes, no more

### Recommendation

| Code | §9 basis | Emitted by |
|---|---|---|
| `next_hop_unreachable` | Bullet 1, *"Relay unreachable"* | The predecessor of the unreachable relay |
| `decryption_failure` | Bullet 2, *"Decryption failure"* | See §3 — reported by the **predecessor** of the relay that could not decrypt |
| `destination_unreachable` | Bullet 4, *"Mock site unreachable"* | The exit relay |

**The set is closed.** §9's bullet 3 (directory unreachable) is client-side and
never appears on the wire.

### Hop timeout — folded, not added

**No new code.** A hop that does not answer within `HOP_TIMEOUT` is, from the
detecting relay's position, indistinguishable from an unreachable one. §9 bullet 1
already covers "relay unreachable" without qualifying the mechanism, and SD-011
introduced `HOP_TIMEOUT` as a bound *"so no failure can hang"* — a mechanism, not a
new cause. A timeout maps by position:

- timeout waiting on the next relay → `next_hop_unreachable`
- timeout waiting on the destination → `destination_unreachable`

This invents nothing and needs no amendment to §9.

### Malformed / unparseable response — not a protocol error

**No code, by §0.** No relay is in a position to detect it, so there is no relay to
emit it. The client detects it and raises a **client-side failure**. Collapsing it
into a remote protocol error would misattribute a local condition to a relay, and no
document supports doing so.

**Residual, stated rather than decided:** if a future design gave relays a reason to
parse relayed content, malformation would become detectable at a hop and would then
need a code that §9 does not currently supply. That is a consequence of a design
change, not a gap in this one.

---

## 2. Error plaintext schema — exactly three fields

```json
{
  "type": "error",
  "code": "next_hop_unreachable | decryption_failure | destination_unreachable",
  "reported_by": "<relay_id of the emitting relay>"
}
```

**No additional fields are justified.** Each candidate was assessed and rejected:

| Candidate | Assessment |
|---|---|
| Free-text `message` / `detail` | **Rejected on safety.** A natural error string tends to name what could not be reached — e.g. a destination host and port. §6 gives no upstream party that information, and §8 already forbids logging the destination. A closed code set cannot leak by accident; a free-text field can |
| `hop_index` / position | **Rejected as redundant.** The client necessarily knows how many layers it opened (§5), so position is already implicit. An explicit field would be additional disclosure for no additional information |
| Timestamp | **Rejected.** No document requires it, and it is a new disclosure |
| Failed relay's id | **Forbidden** by SD-011 |

The three fields are the minimum that satisfies §9's *"clear error"* and
`IMPLEMENTATION_PLAN.md` Phase 3 criterion 6's *"clear named error"*.

---

## 3. `reported_by` semantics

**SD-011 is authoritative and is restated, not altered:**

1. **The detecting relay may identify itself.** `reported_by` is always the emitting
   relay's own `relay_id`.
2. **A downstream relay's identity must never be revealed** — not to the predecessor,
   not to the client.
3. **An upstream relay must not learn more than §6 permits.** Under D2+E2 this is
   structural: a relaying relay receives an opaque sealed blob (§0).

### The one case that needs a stated convention

When relay C fails to decrypt, it holds no key and cannot seal (this is
`OPEN_9_DECISION_BRIEF.md` §4's finding). It returns plaintext to B. B **can** read
that, and must not propagate C's identity.

**Convention:** B emits `{"type":"error", "code":"decryption_failure",
"reported_by":"relay-B"}` and seals it.

`reported_by` therefore means **"the last relay that successfully processed this
request"**, and `code` describes the condition observed *at or immediately after*
that point. This is SD-011's own wording — *"an error naming the last relay it
successfully reached as the point from which the path broke"* — so no new semantics
are introduced.

**It does not mislead the client.** The client built the path and knows that the hop
after B is C; it may legitimately hold that knowledge. What it never receives is C's
identity *from the protocol*, and relay A never learns anything, because B's error is
sealed.

---

## 4. Success plaintext schema — typed, and yes it is needed

Three types, one of which is a continuation:

```json
{ "type": "relay",   "inner": "<base64 of the successor's response bytes>" }
{ "type": "success", "body":  "<base64 of the destination's raw HTTP response>" }
{ "type": "error",   "code": "...", "reported_by": "relay-X" }
```

**Success must be explicitly typed.** Leaving it implicit would force the client to
distinguish "a nested envelope" from "raw response bytes" by shape — and the raw
bytes are supplied by the destination, which in the threat model
`SCRAPER_AGENT_SPEC.md` §5 states is attacker-controlled. Shape-sniffing over
attacker-supplied bytes is the ambiguity D3 was rejected for in
`OPEN_9_ERROR_ENVELOPE.md` §6; an explicit `type` outside the destination's control
removes it.

**`body` and `inner` are base64.** This keeps the destination's bytes strictly data
— never parsed as protocol — and preserves `API_CONTRACT.md` §3's requirement that
`raw_content` reach GOTHAMITE *"verbatim, not cleaned, not stripped, not
truncated"*.

**The outer envelope is unchanged:** `{ "nonce", "ciphertext" }`, exactly as SD-002
specifies, in both directions.

---

## 5. Layer depth

### Normative rules

1. **Layer count MUST NOT be used to classify success versus error.**
2. The client decrypts **in path order A → B → C**, using the keys it generated, as
   §7 already requires.
3. **Type is determined only after successful decryption and successful parsing.** A
   `relay` type means continue; `success` and `error` are terminal.
4. The client stops at the first terminal type. It MUST NOT require the layer count
   to equal the path length before accepting a terminal type.
5. Receiving a terminal type is the only valid stop condition. Exhausting the
   expected path without one is a **malformed response** (§7), not a protocol error.

### On exposing failure position — it is not a choice

The instruction asks to prefer not exposing depth. **It cannot be hidden**: the
client counts its own decryptions, so opening *k−1* layers before a terminal error
tells it the break was at hop *k*. This is structural, not a design decision.

It is also already sanctioned: SD-011 states the client *"may therefore learn the
last relay it successfully reached"*, which is exactly this. The correct response is
therefore **not to add anything further** — no `hop_index` field (§2), no position
marker. The implicit depth is what SD-011 permits, and nothing beyond it is
disclosed.

---

## 6. HTTP status — Option B, with one bounded exception

**Recommendation: HTTP status is transport-only. The sealed `type` is the sole
protocol discriminator.**

| Situation | Status | Body |
|---|---|---|
| A relay produced a sealed response — **success or error alike** | **`200`** | The sealed `{nonce, ciphertext}` envelope |
| A relay could not produce a sealed response at all | **non-2xx** | Plaintext `{"type":"error", "code":"decryption_failure", "reported_by":"<self>"}` |

**The exception is bounded and unavoidable.** A relay that cannot decrypt holds no
key and therefore cannot seal (§3). It must signal that to its predecessor somehow,
and the HTTP status is the only channel outside the sealed layer. Crucially:

- This plaintext form is seen **only by the immediate predecessor**, never propagated
  and never seen by the client.
- The status **never distinguishes success from error** — that is always the sealed
  `type`. It distinguishes only *"here is a sealed protocol response"* from *"I could
  not produce one"*.

So there are not two competing sources of truth. There is one protocol discriminator
(the sealed `type`) and one transport signal with a single, non-overlapping meaning.

SD-001's `POST /relay` transport is otherwise unchanged. Its current use of non-2xx
as the client's failure signal is **retired**.

---

## 7. Malformed protocol response — four outcomes kept distinct

The client classifies exactly four ways, and they must not collapse into each other:

| Outcome | Detection | Category |
|---|---|---|
| **Valid encrypted protocol error** | Decrypt succeeds, parse succeeds, `type == "error"` | **Protocol error** — raise `OnionPathError` naming `code` and `reported_by` |
| **Valid encrypted application success** | Decrypt succeeds, parse succeeds, `type == "success"` | **Application response** — return `body`. Includes the site's own 4xx/5xx, which are *not* protocol errors |
| **Malformed / unparseable** | AES-GCM decryption fails, JSON parse fails, `type` unknown, a required field is missing, or the path is exhausted with no terminal type | **Client-side failure.** Distinct exception. MUST NOT be reported as a remote protocol error, and MUST NOT name a relay as having failed |
| **Transport timeout / unreachable** | The client's own connection to the entry relay fails or times out | **Client-side failure**, as §9 bullet 1 already treats an unreachable entry relay |

**AES-GCM helps here and no new mechanism is needed.** The construction is
authenticated, so a tampered or truncated layer fails decryption outright rather
than decrypting to plausible garbage. "Decryption failed" and "decrypted but did not
parse" are therefore cleanly separable with the primitives already in use.

---

## 8. Cryptographic consequences — none

| Item | Change required |
|---|---|
| `common/onion_crypto.py` | **None.** `seal_response` / `open_response` take and return bytes; D2 changes *which* bytes are sealed, not how. Typed-object construction belongs in the relay and client modules |
| Nonce handling | **None.** §7's rule — a fresh nonce for every encryption, forward and return, never reused with the same key — is untouched and still applies to error layers |
| AES-GCM usage | **None.** Same key size, same nonce size, same authenticated mode |
| Key derivation / distribution | **None.** RSA-OAEP forward delivery per §5.2; the return leg reuses the retained `K` per §7 |
| New primitives | **None introduced.** No new cipher, no key schedule, no signature scheme |

**D2 + E2 is a payload-format decision, not a cryptographic one.** It touches only
the return path; the forward path (§5.1, §5.2, §5.3) is entirely unchanged.

---

## 9. What SD-011 still governs

**Still in force, unchanged:**

- `reported_by` is always the emitting relay's own id, never a downstream one (§3).
- The client may learn the last relay it successfully reached, and never the identity
  of a failed relay further down the path.
- Every hop is bounded by `HOP_TIMEOUT`, so no failure can hang.
- The failed hop is named in the detecting relay's **own log**, per §8.

**Narrowed:** SD-011's rewriting rule was written for plaintext propagation at every
hop. Under D2+E2 a relaying relay cannot read a sealed error, so rewriting is neither
possible nor needed there. It applies to **exactly one adjacency**: the predecessor
of a relay that returned plaintext because it could not decrypt (§3).

**Retired:** SD-011's recorded *"known deviation"* — plaintext errors at every hop,
against §9 bullet 4 — is resolved by adopting E2 and should be marked as such.

**Untouched:** SD-003 (`request_id` relay-local, off the wire) is unaffected. SD-002's
wire shape is unaffected; its stated consequence changes (§11).

---

## 10. Backward compatibility

### Phase-1 assumptions that become invalid

1. **Fixed-depth unwrap.** `client/onion_client.py::unwrap` iterates exactly
   `len(session_keys)` times and treats the last decryption as raw bytes. Replaced by
   §5's terminal-type rule.
2. **Non-2xx as the client's failure signal.** Replaced by §6.
3. **Plaintext error bodies readable at the client.** Errors become sealed.
4. **The innermost envelope containing the raw HTTP response directly.** It now
   contains a typed object carrying it.

### Current tests that would need updating

| Test | Why | Property still valid? |
|---|---|---|
| `TestFailureHandling::test_unreachable_middle_relay_raises_a_controlled_error` | Asserts `next_hop_unreachable` and `reported_by=<entry>` in the message, and absence of the third relay's id. The message now comes from a decrypted object | **Yes** — every property it checks survives; only the source of the string changes |
| `TestFailureHandling::test_unreachable_destination_raises_a_controlled_error` | Same reason | Yes |
| `TestEndToEnd` (unwrap-related assertions) | Depend on fixed-depth unwrap | Yes |
| `TestFailureHandling::test_unreachable_entry_relay_raises_a_named_error` | Client-side failure, never sealed | **No change needed** |
| `TestFailureHandling::test_directory_unreachable_fails_with_a_clear_error` | Client-side | **No change needed** |
| `TestNonceDiscipline`, `TestLogHygiene`, `TestLayerConstruction`, `TestPathSelection`, `TestRegistration`, `TestInvalidInput` | Forward path and logging only | **No change needed** |
| All 41 tests in `tests/test_phase4.py` | Page content and reachability | **No change needed** |

**New tests that would be required:** a sealed error opened correctly by the client;
a relay asserted unable to read a sealed error from its successor (the §0 property);
a malformed layer classified as a client-side failure and **not** as a relay error;
and a site-returned 404 classified as an application success, not a protocol error.

---

## 11. Documents that would need amendment

| File | Change |
|---|---|
| `AgentsDocs/RELAY_PROTOCOL.md` | §6 pseudocode gains an error branch; §7 gains the typed-content definition and the three types; §9 gains the code set and the timeout mapping. **Authoritative — changed first** |
| `AgentsDocs/SPEC_DECISIONS.md` | SD-024 recording this; OPEN-9 annotated; **SD-002's consequence amended** (the innermost envelope now yields a typed object, not raw bytes — the wire shape is unchanged); **SD-001's non-2xx protocol signal retired**; **SD-011 narrowed and its deviation retired** |
| `relay/relay_node.py` | Emit `relay` / `success` / `error` typed content; seal errors; handle a non-2xx plaintext error from a successor |
| `client/onion_client.py` | `unwrap` branches on `type`; classify the four outcomes of §7 |
| `tests/test_phase1.py` | Per §10 |
| `AgentsDocs/reports/PHASE_1_REPORT.md` | Deviation note retired; results updated after re-running |
| `common/onion_crypto.py`, `API_CONTRACT.md`, `DATA_MODEL.md`, `SCRAPER_AGENT_SPEC.md`, `mock_sites/`, `tests/test_phase4.py` | **No change** |

---

## 12. Unresolved — stated, not chosen

1. **Whether `code` should be omitted entirely**, leaving only `type: "error"` and
   `reported_by`. This would be maximally conservative: §9 names three causes but
   never says the client is entitled to know *which*. The proposal includes `code`
   because §9 calls for a *"clear"* error and Phase 3 criterion 6 for a *"named"*
   one, which reads more naturally as naming the condition than merely signalling
   failure. **Genuinely underdetermined; a human may prefer the narrower form.**
2. **Whether malformed responses should remain permanently uncodeable**, or whether a
   future design that has relays parse relayed content would need a code §9 does not
   supply (§1).
3. **Whether `relay` is the right name** for the continuation type, versus `relayed`
   or `next`. Cosmetic, but it becomes normative once written into §7.
4. **Whether the plaintext non-2xx form of §6 should carry `code` at all**, or only
   signal "could not seal". Including it lets the predecessor report accurately;
   omitting it discloses marginally less to that one peer. **Underdetermined.**

Everything else in this document follows from `RELAY_PROTOCOL.md` §6, §7 and §9,
SD-002 and SD-011 without invention.

---

**Nothing above has been done.** No specification modified, no code modified, no
tests modified, no SD-024 created, Phase 5 not started, OPEN-4 / OPEN-5 / OPEN-6
untouched, no commit.

---

## 13. Status after SD-024

**Recorded 2026-09-07 as `SPEC_DECISIONS.md` SD-024 — PROPOSED, NOT IN FORCE.**

The decision adopts this document's proposal: E2 transport (§A), D2 discriminator
with the three plaintext types (§B), the closed three-code set with timeout folded
and malformed excluded (§C), `reported_by` as the last relay that successfully
processed the request (§D), HTTP status demoted to transport-only (§E), the
layer-depth rules (§F), the four-way malformed classification (§G), no
cryptographic change (§H), and relay-protocol-only scope (§I). SD-011 is expressly
preserved.

**Two of §12's open items are resolved by the decision:**

- **§12.1** — `code` is **retained**, not omitted. SD-024 §C defines the closed set.
- **§12.3** — the continuation type is named **`relay`**. SD-024 §B fixes it.

**Two remain open:**

- **§12.4** — whether the plaintext non-2xx body carries a `code`. SD-024 §A defers
  to SD-011, whose recorded form includes one, so the reading is that it does — but
  SD-024 does not state it in so many words. **Narrowed, not settled.**
- **§12.2** — malformed responses stay permanently uncodeable under this design; a
  future design that had relays parse relayed content would need a code §9 does not
  supply.

**One item added by the recording:** the exact amendment wording for
`RELAY_PROTOCOL.md` §6, §7 and §9 has still to be drafted, and must land **before**
any implementation.

**Nothing here has been implemented or verified.** OPEN-9 stays open until
`RELAY_PROTOCOL.md` is amended and the implementation and tests are updated and
pass.
