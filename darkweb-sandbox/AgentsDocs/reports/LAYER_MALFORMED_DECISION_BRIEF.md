# `layer_malformed` — Decision Brief

**Date:** 2026-09-07
**Status:** **DECISION BRIEF ONLY.** No specification, code or test modified; no SD
entry created or amended.
**Scope:** the protocol gap identified in `B4_DECISION_BRIEF.md` §6 — a relay that
successfully decrypts its layer but finds it structurally unusable has no defined
behaviour under SD-024.
**Blocks:** OPEN-9 implementation.
**Context:** B4/P3 is approved — the plaintext fallback carries `400` and
`{"error": "decryption_failure", "reported_by": "<own relay_id>"}`, with
`decryption_failure` as its only permitted value.

---

## 1. What `layer_malformed` actually means at `relay_node.py:137`

The branch is narrower than its name suggests. `open_layer`
(`common/onion_crypto.py:186`) already performs, **before returning**:

- base64 validation of `enc_key`, `nonce`, `ciphertext`;
- 96-bit nonce length check;
- RSA-OAEP unwrap and a 256-bit session-key length check;
- **AES-GCM decrypt with tag verification**;
- UTF-8 decode and JSON parse of the plaintext;
- `isinstance(layer, dict)`;
- **presence of all four required fields** — `next_hop`, `next_host`, `next_port`,
  `payload`.

Every one of those raises `EnvelopeError`, which lands in the **first** except block
at `relay_node.py:125` — the `decryption_failure` fallback, not this one.

So what remains for line 137? Only the second block:

```python
next_hop  = str(layer["next_hop"])
next_host = str(layer["next_host"])
next_port = int(layer["next_port"])
payload   = layer_payload(layer)
except (KeyError, TypeError, ValueError, EnvelopeError)
```

| Caught | Reachable? | Cause |
|---|---|---|
| `KeyError` | **No — dead code.** `open_layer` already verified all four fields are present | — |
| `TypeError` | **Yes** | `int()` of a list, dict, `None` for `next_port` |
| `ValueError` | **Yes** | `int()` of a non-numeric string, e.g. `"eight-thousand"` |
| `EnvelopeError` | **Yes** | `layer_payload` → `_b64d`: `payload` is not a string, or not valid base64 |

**The reachable condition is exactly two things: `next_port` is not coercible to an
integer, or `payload` is not decodable base64.** Everything else the name suggests is
already handled upstream as a decryption failure.

Two incidental observations, neither part of this decision: `int()` **silently
truncates** a float `next_port` (`8080.9` → `8080`) rather than rejecting it, and
`int(True)` yields `1`. Worth a look during OPEN-9 implementation; not a protocol
question.

## 2. Before or after the per-hop key is obtained?

**Strictly after, and this is the decisive fact.**

`open_layer` returns `(layer, session_key)`. Execution only reaches line 131 if that
returned successfully, so at line 137 the relay **holds `K`**. The current code then
deliberately discards it — `del session_key` at line 136 — immediately before
returning the plaintext error.

Stronger than "it holds the key": **the layer is authenticated.** AES-GCM is an AEAD
and the tag check passed, so the plaintext was produced by whoever holds `K` — the
client. A tampered or corrupted layer fails the tag and lands in the *first* block.

**Therefore a malformed layer at :137 is a client-side construction bug, never
attacker-injected.** That has consequences for §8 below.

## 3. Can the relay seal an error under E2?

**Yes, and E2 requires it to.** SD-024 §A: a relay seals the error response for its
predecessor *"when it still possesses the required encryption key."* It does. The
`del session_key` on line 136 is an implementation choice made before SD-024 existed,
not a constraint.

**This is what makes the gap real rather than cosmetic.** The relay must seal; the
sealed `error` object requires a `code`; §9.1's closed set has no value that fits.
The question is not *whether* to seal but *what code to seal*.

## 4. Options

### M1 — A fourth closed error code *(recommended)*

Add one value to §9.1, sealed under E2 as any other protocol error:

```json
{ "type": "error", "code": "malformed_layer", "reported_by": "<own relay_id>" }
```

**For:** it is the only option that is simultaneously E2-compliant and truthful. The
condition is genuinely distinct from the other three — the relay reached nobody and
failed to decrypt nothing; it decrypted successfully and cannot act on the result.
**Against:** it amends SD-024's closed set, 3 → 4. See §10.
**Naming hazard, and it is a real one:** §9.1 states *"`malformed_response` is NOT a
protocol error code"*, on the reasoning that no relay parses relayed content. A code
named `malformed_layer` sits one word away from that exclusion and will be misread.
The amendment must distinguish them explicitly: the exclusion is about **relayed
content** a relay must never parse; this is a relay's **own layer**, which it is
required to parse. `unusable_layer` reads less confusably if the naming collision is
judged too close.

### M2 — Map to `decryption_failure`

Seal, E2-compliant, no new code, set stays at three.

**For:** no SD-024 amendment; minimal surface.
**Against:** the code is inaccurate — decryption succeeded, and the tag proved it. It
also now collides with B4/P3: `decryption_failure` was just approved as the **single**
value meaning "I could not decrypt", carried in the plaintext fallback precisely
because the relay holds no key. M2 would make the same code mean "I *did* decrypt, and
the result was unusable" in the sealed channel. That is the one-code-one-meaning
property B4/P3 relied on, given up a week after acquiring it.

### M3 — Treat as a client-side malformed response

**Not actionable, and it misreads §9.1.** That exclusion applies because no relay
parses relayed content, so no relay is positioned to detect malformation in it. Here
the relay parses its **own** layer, which the protocol obliges it to do, and it is the
only party that can detect this. The client cannot: it built the layer and believes it
correct. And M3 gives the relay no wire behaviour at all — it must still answer
something.

### M4 — Use the B4/P3 plaintext fallback

Return `400 {"error": "decryption_failure", ...}` as today.

**Against:** directly contradicts E2. The relay holds `K`; E2's rule is that such a
relay seals. It also inherits M2's inaccuracy on top.

### M5 — Move the validation into `open_layer` so the branch cannot exist

Tighten `open_layer` to validate `next_port` integrality and `payload` decodability
before returning, so any structurally invalid layer raises `EnvelopeError` and takes
the existing `decryption_failure` plaintext path. Line 137 becomes genuinely
unreachable and is deleted.

**For:** no new code, no SD-024 amendment, and it removes a branch rather than adding
one. Superficially the tidiest.
**Against, and it is disqualifying:** it reaches the outcome by **deliberately
discarding a key the relay holds** so that E2's sealing rule no longer applies. That
is contorting the implementation to avoid a specification amendment. It also collapses
two distinct causes — "wrong key or tampering" and "right key, bad content" — into one
code, and it does so at the layer where the distinction is cheapest to keep. Recorded
because it is the obvious no-amendment route and someone will propose it; it should be
rejected on the merits, not overlooked.

## 5. Interaction with the existing decisions

| Decision | Effect under M1 |
|---|---|
| **SD-011** | **Satisfied.** `reported_by` is the emitting relay's own id, never a downstream one. The relay does not even know its successor's reachability — it never attempted the hop |
| **SD-024 §A / E2** | **Honoured, not excepted.** The relay holds `K` and seals, which is exactly what E2 prescribes. M4 and M5 are the options that strain it |
| **SD-024 §B / D2** | **Unchanged.** A `{"type": "error"}` object with a `code` and `reported_by` — the existing shape. No new field, no new type. Intermediate relays still forward opaquely and never parse |
| **B4 / P3** | **Preserved.** P3's single-value property survives: `decryption_failure` remains the only code that can appear in the plaintext fallback, because that fallback is still reachable only when the relay holds no key. M1 adds nothing to the plaintext channel |
| **§9.1 closed set** | Grows 3 → 4. The mapping to §9's bullets becomes: bullet 1 → `next_hop_unreachable`, bullet 2 → `decryption_failure`, bullet 4 → `destination_unreachable`, **plus one code with no §9 bullet** — because §9 never contemplated this case. That absence is the gap, stated plainly |
| **SD-001 / SD-002 / SD-003** | Unaffected. Transport, envelope shape and `request_id` locality all unchanged |

## 6. Does `reported_by` remain valid?

**Yes, and it is unambiguous here.** SD-024 §D defines it as *"the last relay that
successfully processed the request and is reporting the failure."* This relay
successfully processed the request as far as decrypting and authenticating its own
layer, and is the party reporting. It names itself.

No downstream identity is involved or available: the relay never resolved `next_hop`
into a forwarding attempt. There is no predecessor-translation step of the kind B4/P3
requires, because the error is sealed at the point of detection and travels the normal
return path opaquely.

## 7. Exact HTTP behaviour

**`HTTP 200`**, per §9.3: *"HTTP 200 whenever a sealed protocol response envelope is
successfully returned — regardless of whether the decrypted protocol type is `success`
or `error`."* A sealed envelope is returned, so the status is 200.

**This is a change from the current build**, which returns `400` here
(`relay_node.py:137`). The `400` is correct only for the B4/P3 fallback, where no
envelope exists. Conflating the two is what the current code does.

## 8. Security and information disclosure

**The branch is unreachable without the key, which changes its risk profile
entirely.** A relay only arrives here after a successful GCM tag check, so an attacker
without `K` cannot reach it. That has two consequences:

- **No decryption-oracle concern.** The objection that shaped `EnvelopeError`'s
  "callers must not distinguish between those cases" comment does not apply: an
  attacker cannot use this branch to learn anything about decryption, because reaching
  it already requires having succeeded at it.
- **The recipient is the client, and the client built the layer.** A sealed error
  discloses to the one party that already knows the content.

**What must still not appear on the wire:** which field was malformed, its value, the
exception text, byte lengths, `request_id` (SD-003), or any hop identity but the
relay's own. Not because of an oracle risk, but because §9's discipline is uniform and
diagnosis belongs in the relay's own log (§8), where the demo already reads it. The
current code logs the exception locally and returns only a fixed code — that part is
right and should be kept.

**Availability note:** this branch cannot be triggered remotely by a third party, so it
is not a denial-of-service surface. It is a correctness safeguard against a buggy or
compromised client.

## 9. Required tests

Additional to OPEN-9's seven and B4/P3's five:

1. A layer whose `next_port` is not integer-coercible produces a **sealed** error the
   client can open, with `code = malformed_layer` — **not** a plaintext `400`.
2. A layer whose `payload` is not valid base64 produces the same.
3. The response status is **200**, asserted directly, since this is the behaviour
   change from the current build.
4. The sealed error's `reported_by` is the detecting relay's own id.
5. An intermediate relay **cannot read** that sealed error from its successor — the
   E2 property, exercised on this code path specifically.
6. The sealed body carries **no** field name, field value, or exception text; log
   hygiene re-verified on this branch, which is the one with real diagnostics available
   to leak.
7. A tampered layer still yields `decryption_failure` via the **plaintext** fallback —
   the negative control proving the two paths stay separate.
8. The dead `KeyError` arm is confirmed unreachable, or removed with `open_layer`'s
   field-presence check cited as the reason.

## 10. Does this require amending SD-024, or only `RELAY_PROTOCOL.md`?

**Both, under M1 — and the amendment is strictly necessary.**

- **`RELAY_PROTOCOL.md` §9.1** — add the fourth code, with wording distinguishing it
  from the `malformed_response` exclusion two paragraphs above it.
- **`SPEC_DECISIONS.md` SD-024 §C** — the closed set is *stated there* as three
  values. Amending §9.1 without amending §C would leave the specification and the
  decision record contradicting each other, which is the failure mode SD-026 and B6
  were about.

**Why "strictly necessary" is met.** E2 determines that this case must be sealed; a
sealed error requires a `code`; the closed set contains no accurate value. The only
options that avoid touching SD-024 are M2 (make an existing code mean two things) and
M5 (throw away a held key to dodge E2). Both resolve a specification omission by
degrading the design.

The amendment is also **additive and narrow**: one value added to a closed set, no
existing value's meaning changed, no field added to any object, no transport or
cryptographic change. SD-024 §§A, B, D, E, F, G, H, I and J are untouched.

M2 and M5 are the routes that keep SD-024 frozen at three codes, and both are
available if holding the set fixed is judged more valuable than code accuracy. This
brief does not consider that trade favourable.

---

## Recommendation

**M1 — add a fourth closed error code, sealed under E2, HTTP 200, `reported_by` =
the detecting relay.** Amend `RELAY_PROTOCOL.md` §9.1 and SD-024 §C together, with
naming chosen to avoid collision with the `malformed_response` exclusion —
`unusable_layer` if `malformed_layer` is judged too close.

**Confidence: high on the analysis, medium on the naming.** The analysis is largely
forced: §2's finding that the relay holds an *authenticated* layer settles §3, which
settles that the response must be sealed, which leaves only the choice of code. The
naming is a judgement call and the collision risk with §9.1's existing exclusion is
real.

**Two things worth weighing before adopting.** First, the case is **defensively
reachable only** — our own client builds the layers, so in practice this fires only on
a client bug or a compromised client. A reader may reasonably ask whether it deserves
protocol surface at all; the answer is that `RELAY_PROTOCOL.md` specifies behaviour for
any implementation, and "undefined" is the one answer a protocol document should not
give. Second, adopting M1 means the closed set is no longer the closed set SD-024 was
approved with — small, but it is the first widening of anything in this freeze, and
that precedent is worth noticing rather than absorbing quietly.

---

**Nothing above has been done.** `AgentsDocs/RELAY_PROTOCOL.md`,
`AgentsDocs/SPEC_DECISIONS.md`, `relay/`, `client/`, `common/` and `tests/` are
unmodified. No SD entry created or amended. SD-021 through SD-028 not reopened.
OPEN-9 not started. Phase 5 not started. No commit.
