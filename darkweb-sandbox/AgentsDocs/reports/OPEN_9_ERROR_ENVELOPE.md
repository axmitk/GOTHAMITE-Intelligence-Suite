# OPEN-9 — Error Envelope and Response Discriminator

**Date:** 2026-09-07
**Status:** **PROTOCOL-DESIGN ANALYSIS ONLY. NOTHING DECIDED, NOTHING IMPLEMENTED.**
**Companion to:** `AgentsDocs/reports/OPEN_9_DECISION_BRIEF.md`

Nothing was modified to produce this. `RELAY_PROTOCOL.md`, `SPEC_DECISIONS.md`,
`API_CONTRACT.md`, `DATA_MODEL.md`, all code, all tests and `mock_sites/` are
untouched. Phase 5 has not started. OPEN-4, OPEN-5 and OPEN-6 are untouched. No
SD-024 has been created.

No cryptographic mechanism is invented below. Every design reuses the AES-GCM and
RSA-OAEP primitives already fixed by `RELAY_PROTOCOL.md` §2 and §5.2, and none of
them claims any anonymity property beyond what `RELAY_PROTOCOL.md` §6 and §10
already state.

---

## 1. Four categories that must stay distinct

The rest of this document depends on keeping these apart. They are easy to conflate
and the existing documents already treat them differently.

| Category | Definition | Where it is decided today | On the relay wire? |
|---|---|---|---|
| **Application response** | Whatever the mock site returned, **including its own 4xx and 5xx**. A site returning `404` is a *successful* protocol exchange | `SCRAPER_AGENT_SPEC.md` §6: *"Page returns 404 → Log, continue"* — handled by the scraper, not the relay layer | Yes, as an ordinary sealed response |
| **Protocol error** | A relay-layer failure the protocol must report: `RELAY_PROTOCOL.md` §9 bullets 1, 2, 4 | §9, plus SD-011's `reported_by` rule | Yes — **this is what OPEN-9 is about** |
| **Transport failure** | A TCP or HTTP failure between two hops (connection refused, reset, timeout) | Not named in §9; becomes a protocol error at the detecting relay | Only after conversion |
| **Client-side failure** | Directory unreachable (§9 bullet 3), entry relay unreachable, malformed path response | §9 bullet 3; SD-011's `OnionPathError` | **No.** Never reaches the wire |

**A discriminator design that cannot keep "application response" and "protocol
error" apart is disqualified**, because the exit relay seals *the destination's own
bytes* and those bytes are, in the real-world analogue this sandbox models,
attacker-controlled. This is the criterion that decides D3 in §6.

---

## 2. What the protocol does today — the implicit discriminator

There is already a discriminator. It is implicit, and naming it makes the options
comparable.

**Success envelope (SD-002):** `{ "nonce": …, "ciphertext": … }`, nesting so that
the exit relay seals the site's raw response bytes and each upstream relay seals
**the JSON bytes of the envelope it received**.

**The current client discriminates by depth.** `client/onion_client.py::unwrap`
iterates exactly `len(session_keys)` times, treats every intermediate decryption as
"parse a nested envelope", and treats the **last** decryption as "these are the raw
response bytes". Nothing in the payload says which is which — the client knows
because it counts.

Call this **D0**. It works only because a success always carries exactly
`len(path)` layers. The previous brief established that under E2 an error carries
**fewer** layers — at most `1 … k−1` for a failure at hop *k*, because the failing
relay either holds no key (decryption failure) or is unreachable. **D0 therefore
cannot survive E2.** That, not aesthetics, is why a discriminator is needed at all.

D0 is also silently fragile today: an error at hop 2 of 3 would leave the client
attempting a third decryption that must fail, and it would surface as
`could not open response layer 2` — a crypto-shaped message for a routing-shaped
problem.

---

## 3. D1 — a type field in the outer envelope

### 3.1 Wire shape

```json
{ "kind": "<value>", "nonce": "<b64>", "ciphertext": "<b64>" }
```

`kind` is **plaintext** — it must be, or it could not be read without the key.

**Two sub-variants, and they differ enormously.** The blocker's phrasing does not
distinguish them, and the distinction turns out to decide whether D1 is viable.

- **D1a — `kind` describes the innermost content and is copied upward.** A relaying
  relay must know whether what it is sealing is an error, and set `kind`
  accordingly.
- **D1b — `kind` describes only what *this* relay contributed.** Values are
  `relayed` (I sealed an opaque blob from my successor), `ok` (I am the exit relay
  and this is the destination's response), `error` (I generated this error myself).

### 3.2 What each relay can see

**D1a leaks, and disqualifies itself.** For a relaying relay to copy `kind` upward,
it must *read* the field on the blob it received — so relay A learns "an error
occurred somewhere at or below B". A already knows it forwarded to B successfully,
so A learns the failure is at B or beyond. §6's table gives A no entitlement to
anything past B, and the previous brief's §7.6 finding — that plaintext error
information can tell an upstream relay about the destination — applies directly.

**D1b does not leak.** Each relay writes only about itself:

- `relayed` tells A nothing it did not already know (A knows B returned something).
- `error` tells A that **B** failed — which SD-011 explicitly permits, since a relay
  may identify itself and the client may learn the last relay it successfully
  reached.

Critically, in the return path a relay **does not decrypt what it receives** (§7:
*"B encrypts what it received"*), so under D1b a relaying relay is structurally
unable to know whether the inner content is an error. `relayed` is the only honest
value it can write, and that is exactly the non-leaking one.

### 3.3 What the client can distinguish

Unwrap outer-to-inner, reading `kind` before each decryption:

- `relayed` → decrypt, expect another envelope, continue
- `ok` → decrypt, the plaintext is the raw HTTP response — **stop**
- `error` → decrypt, the plaintext is the error object — **stop**

Depth becomes self-terminating; the client no longer needs to count.

### 3.4–3.12 Assessment

| Dimension | D1b |
|---|---|
| **4. Preserves layered encryption** | Yes. Encryption is untouched; one plaintext field is added alongside |
| **5. Forwards an error without learning downstream identity** | Yes — a relaying relay cannot read the sealed body at all |
| **6. Leaks error/destination info upstream** | **D1b: no.** D1a: yes, disqualifying |
| **7. Interaction with E2** | Good. Solves E2's variable-depth problem directly |
| **8. SD-001 / SD-002 / SD-003 / SD-011** | **Amends SD-002** (new envelope field). SD-001's non-2xx status becomes redundant and should be retired to avoid two competing signals. SD-003 unaffected. SD-011 still required, since a relay generating an error still writes `reported_by` |
| **9. Backward compatibility** | Breaks D0. Relay and client both change |
| **11. Application/protocol ambiguity** | **None.** `kind` sits outside the sealed content, so a destination cannot influence it |
| **12. Simplicity** | Highest of the four. One field, three values, no nested parsing rules |

---

## 4. D2 — typed inner plaintext

### 4.1 Wire shape

The envelope is **unchanged**: `{ "nonce", "ciphertext" }`. What changes is the
plaintext sealed inside it, which becomes a typed object at every layer:

```json
{ "type": "relayed",  "inner": { "nonce": "<b64>", "ciphertext": "<b64>" } }
{ "type": "response", "body":  "<b64 of the destination's raw HTTP response>" }
{ "type": "error",    "error": "<code>", "reported_by": "<relay_id>" }
```

Every decryption yields exactly one of these three, so unwrapping is uniform.

### 4.2 What each relay can see

**Nothing.** The discriminator is inside the ciphertext. A relaying relay sees an
opaque `{nonce, ciphertext}` pair and cannot tell an error from a success, a short
stack from a long one, or a destination failure from a hop failure.

This is the strongest confidentiality property of the four designs and it closes the
previous brief's §7.6 leak **structurally** rather than by discipline: a relay cannot
forward information it cannot read.

One precise qualification. Under E2, a relay that fails to decrypt has no key and
must return **plaintext** to its predecessor. That predecessor *can* read it, and
must rewrite `reported_by` per SD-011 before sealing it as `type: "error"`. So D2
does not make SD-011 redundant — it makes it unnecessary for *relayed* errors while
leaving it necessary for that one adjacency.

### 4.3 What the client can distinguish

Decrypt, parse, branch on `type`. `relayed` → recurse into `inner`. `response` →
done, the body is the application response. `error` → done, raise `OnionPathError`.
No counting, no shape-sniffing.

### 4.4–4.12 Assessment

| Dimension | D2 |
|---|---|
| **4. Preserves layered encryption** | Yes, most faithfully — the nesting model is unchanged and only the sealed content gains a type tag |
| **5. Forwards an error without learning downstream identity** | Yes, and **enforced by construction** rather than by rule |
| **6. Leaks error/destination info upstream** | **No. Zero plaintext signal** |
| **7. Interaction with E2** | Excellent. D2 is close to what E2 needs on its own |
| **8. SD-001 / SD-002 / SD-003 / SD-011** | SD-002's **wire shape is untouched**, but its stated consequence — *"what falls out of the innermost envelope is the raw HTTP response"* — becomes false: what falls out is a typed object containing it. **That is an amendment in substance and should be recorded as one.** SD-001's non-2xx status should be retired as above. SD-003 unaffected. SD-011 narrowed but still required |
| **9. Backward compatibility** | Breaks D0. Relay and client both change; slightly more client work than D1b |
| **11. Application/protocol ambiguity** | **None.** The destination's bytes are base64-carried in a `body` field and never parsed as protocol |
| **12. Simplicity** | Slightly more machinery than D1b — an extra JSON object per layer — but one uniform rule with no plaintext side-channel to reason about |

---

## 5. D4 — a separate error envelope

*(Taken before D3, because D4 is a near-neighbour of D1 and D3 needs the contrast.)*

### 5.1 Wire shape

Two envelope types, discriminated by **which keys are present** rather than by a
value:

```json
{ "nonce": "<b64>", "ciphertext": "<b64>" }                    // success
{ "error_nonce": "<b64>", "error_ciphertext": "<b64>" }        // error
```

### 5.2–5.12 Assessment

Structurally D4 is D1 with the discriminator moved from a field's *value* to the
envelope's *shape*, so the leak analysis is identical: if a relaying relay must
choose the error shape for a downstream error, it leaks like D1a; if each relay
chooses its own outer shape, it is as safe as D1b.

What D4 adds is cost without benefit:

- **Two parsers instead of one**, and shape-sniffing is more brittle than reading a
  field — a malformed envelope missing `nonce` is indistinguishable from an error
  envelope missing `error_nonce`.
- **It fragments SD-002** into two formats where SD-002's own rationale was that
  keeping the return envelope identical to the forward one *"means one implementation
  handles both directions"*.
- It offers **no confidentiality advantage over D1b** and is strictly worse than D2.

**D4 is dominated.** It is analysed for completeness and not carried forward.

---

## 6. D3 — reserved ciphertext or payload convention

### 6.1 Wire shape

No new field and no new shape. The discriminator is a **convention inside the
existing bytes** — a magic prefix on the decrypted plaintext, a sentinel value, or a
reserved length such as a zero-length ciphertext.

### 6.2 Why this is disqualified

**The exit relay seals the destination's raw response bytes verbatim** (SD-002,
§6). Under D3 the discriminator lives in those same bytes. Therefore:

> **A destination can forge a protocol error.** A mock site whose page begins with
> the reserved prefix produces a response the client will interpret as a relay-layer
> failure.

That is the §1 disqualification exactly: it collapses **application response** into
**protocol error**, and it does so in the direction that matters — the content is
supplied by the least trusted participant in the system.
`SCRAPER_AGENT_SPEC.md` §5 makes the threat model explicit: *"In the real system
this crawler would be reading attacker-controlled pages"*, and treats scraped content
as inert data that is never interpreted as instruction. A content-based protocol
discriminator does precisely the opposite.

Secondary problems, any one of which would also weigh against it: a zero-length or
reserved-length convention constrains AES-GCM output handling for no gain;
`raw_content` must reach GOTHAMITE *"verbatim, not cleaned, not stripped,
not truncated"* per `API_CONTRACT.md` §3, so any escaping scheme to make forgery
impossible would have to be undone perfectly before ingestion; and the convention
would be invisible in the wire format, making the protocol unreadable from its own
specification.

**D3 is rejected on security grounds, not on style.** It is the only one of the four
that creates the ambiguity item 11 asks about.

---

## 7. Side-by-side

| | D1a | **D1b** | **D2** | D3 | D4 |
|---|---|---|---|---|---|
| Discriminator location | outer plaintext | outer plaintext | **inside ciphertext** | inside destination bytes | envelope shape |
| Visible to relays | **yes — leaks** | self-only, safe | **nothing** | n/a | self-only, safe |
| Destination can forge | no | no | no | **YES** | no |
| App/protocol ambiguity | none | none | none | **yes** | none |
| Amends SD-002 | shape | shape | **content semantics only** | no | shape, and fragments it |
| Solves E2 variable depth | yes | yes | yes | yes | yes |
| Client complexity | low | **lowest** | low-moderate | low | moderate |
| Verdict | **disqualified** | viable | **recommended** | **disqualified** | dominated |

---

## 8. The §9 taxonomy question

`RELAY_PROTOCOL.md` §9 names four causes. Mapping them against the five the
follow-up asks about:

| Cause | In §9? | Status |
|---|---|---|
| Next-hop unreachable | **Yes** — bullet 1 | Supported by the specification |
| Decryption failure | **Yes** — bullet 2 | Supported |
| Destination unreachable | **Yes** — bullet 4 | Supported |
| Directory unreachable | Yes — bullet 3 | Supported, but **client-side only**; never on the wire (§1) |
| **Hop timeout** | **No** | **Not supported.** `HOP_TIMEOUT` was introduced by SD-011, not by §9 |
| **Malformed / unparseable response** | **No** | **Not supported.** No document mentions it |

**Finding: the existing specification supports a three-code wire taxonomy and no
more.** Only bullets 1, 2 and 4 are both named in §9 and present on the wire.
Timeout and malformed-response are real conditions the implementation must handle,
but no document names them, so **defining codes for them is a residual decision, not
a reading.** I am not deciding it.

Two observations that bear on that future decision, recorded without settling it:

1. **A timeout is arguably not a fifth cause.** From the detecting relay's point of
   view, a hop that does not answer within `HOP_TIMEOUT` is indistinguishable from
   bullet 1's "relay unreachable". Folding it in would need no new code; treating it
   separately would need §9 amended. Both are defensible.
2. **Taxonomy granularity interacts with the discriminator choice.** Under D1b the
   code sits in sealed content, so a fine-grained taxonomy costs nothing in
   confidentiality. Under any design that put codes in plaintext, each additional
   code would be additional information leaked to upstream relays — the previous
   brief's §7.6 finding, scaled. This is another reason the discriminator decision
   should come first.

---

## 9. Recommendation

### Recommended discriminator: **D2 — typed inner plaintext**

Three reasons, in order of weight:

1. **It leaks nothing.** The discriminator is sealed, so an upstream relay learns
   neither that an error occurred nor anything about the destination. This closes the
   §7.6 leak the previous brief identified *structurally* — a relay cannot forward
   what it cannot read — rather than by requiring every implementer to remember a
   normalisation rule.
2. **It leaves SD-002's wire format untouched.** `{nonce, ciphertext}` stays exactly
   as specified, in both directions, preserving SD-002's own rationale that one
   implementation handles both. What changes is the sealed content's semantics — a
   real amendment, but a smaller one than a new envelope field.
3. **It cannot be forged by the destination** (unlike D3) and creates no ambiguity
   between application responses and protocol errors, because the destination's bytes
   are carried in a `body` field and never parsed as protocol.

### Strongest argument against D2

**It moves protocol discrimination behind decryption, and therefore behind
parsing.** Under D1b the client reads a plaintext `kind` and knows what it is
holding before spending a key. Under D2 it must decrypt, then parse JSON, then
branch — so a corrupted or hostile layer surfaces as a parse failure that the client
must correctly attribute. That is a genuine increase in the number of places the
client can be confused, in exactly the component §1 says the whole design serves.

**D1b is a legitimate alternative** on those grounds, and its leak profile is safe —
provided the `relayed` / `ok` / `error` distinction is implemented exactly as
described in §3.1, with each relay writing only about its own contribution. The
failure mode is that a plausible-looking implementation which copies `kind` upward
silently becomes D1a, which leaks. D2 has no equivalent trap. That asymmetry —
D1b's simplicity is conditional on getting one rule right, D2's safety is
unconditional — is what decides it for me.

**Confidence: moderate.** Both D2 and D1b are defensible; D1a, D3 and D4 are not.

### Can E2 be safely adopted alongside D2?

**Yes — and the two are close to the same decision.** E2 says a relay seals whatever
it returns upstream; D2 supplies the typed content that makes a sealed error
distinguishable once opened. E2 without a discriminator is not implementable, since
D0 breaks on short stacks (§2). D2 without E2 is possible but pointless. They should
be decided together.

Two conditions on the pairing, both stated in the analysis above and neither
resolved here:

- **SD-011 remains necessary** for the one adjacency where a decryption-failing relay
  returns plaintext to its predecessor. D2 narrows SD-011's scope; it does not retire
  it.
- **SD-001's non-2xx status should be explicitly retired** as a protocol signal, or
  the protocol will carry two competing discriminators — an HTTP status and a sealed
  type — that can disagree.

---

## 10. Remaining protocol questions

None of these is decided here.

1. **The timeout and malformed-response codes** (§8). Not supported by any document;
   requires a human decision, and requires amending §9 if they are to be named.
2. **Does the number of layers still leak the failure position to the client?** Under
   D2 the client learns how deep it got before hitting an error. SD-011 explicitly
   permits the client to learn the last relay it successfully reached, so this appears
   consistent — recorded so it is a deliberate consequence rather than an incidental
   one.
3. **What does a relay do with an unparseable response from its successor?** Still
   undefined under every design, and it is the condition D2's parse-then-branch makes
   most visible.
4. **Should the error object carry anything beyond `error` and `reported_by`?** A
   timestamp or a hop index would each be a new disclosure and would need weighing
   against §6.
5. **Retiring the non-2xx status** (§9), which touches SD-001.
6. **Whether §6's pseudocode gains an error branch**, carried over from the previous
   brief. Whatever is decided, §6 currently reads as though failures cannot occur.

---

## 11. Files that would eventually change

Under **D2 + E2**:

| File | Change |
|---|---|
| `AgentsDocs/RELAY_PROTOCOL.md` | §7 gains the typed-content definition; §6's pseudocode gains an error branch; §9 gains the cross-reference. **The authoritative document, changed first** |
| `AgentsDocs/SPEC_DECISIONS.md` | SD-024 recording the decision; OPEN-9 annotated; SD-002's consequence amended; SD-001's status signal retired; SD-011's scope narrowed |
| `relay/relay_node.py` | Wrap responses as `relayed` / `ok` / `error`; seal errors; handle a plaintext error from a successor |
| `client/onion_client.py` | `unwrap` branches on `type` instead of counting `session_keys` |
| `common/onion_crypto.py` | Only if the typed object is given helper constructors; **no change required** to the envelope functions |
| `tests/test_phase1.py` | `TestFailureHandling` rewritten against the sealed form; `unwrap`-related assertions in `TestEndToEnd` reviewed for the depth assumption |
| `AgentsDocs/reports/PHASE_1_REPORT.md` | Deviation note and test results updated after re-running |
| `API_CONTRACT.md`, `DATA_MODEL.md`, `SCRAPER_AGENT_SPEC.md`, `mock_sites/`, `tests/test_phase4.py` | **No change** — errors never reach the ingestion seam |

Under **D1b**, the same list with `common/onion_crypto.py` **required** (the envelope
gains a field) and `client/onion_client.py` slightly simpler.

---

**Nothing above has been done.** No specification modified, no code modified, no
tests modified, no contract modified, no SD-024 created, Phase 5 not started, OPEN-4
/ OPEN-5 / OPEN-6 untouched, no commit.
