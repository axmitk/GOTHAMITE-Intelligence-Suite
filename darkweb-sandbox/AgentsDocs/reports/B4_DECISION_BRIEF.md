# B4 — Decision Brief: the plaintext fallback response

**Date:** 2026-09-07
**Status:** **DECISION BRIEF ONLY.** No specification, code or test modified; no SD
entry created or amended. SD-021 through SD-028 are not reopened.
**Scope:** SD-024 residual 1 — *"Whether the plaintext non-2xx body of section E
carries a `code`."*
**Blocks:** OPEN-9. It is the last undecided question in the relay error protocol.

---

## 1. Exactly when this response happens

`RELAY_PROTOCOL.md` §9.3 retains a plaintext non-2xx response in **one** case:

> a relay that could not decrypt its own layer, holds no key, and therefore cannot
> seal anything for its predecessor.

Everything follows from that sentence, so it is worth being precise about what it
implies. A relay that **did** decrypt holds `K`, and SD-024 §A requires it to seal its
error. So every other failure — next hop unreachable, destination unreachable, hop
timeout — is a **sealed** error and never reaches this path.

Three structural consequences, all of which narrow the decision:

1. **The fallback travels exactly one hop.** It is read by the emitting relay's
   immediate predecessor, or — when the *entry* relay is the one that cannot decrypt —
   by the client directly. It is never forwarded.
2. **The emitting relay knows nothing to leak.** It failed before reading
   `next_hop`, `next_host` or `next_port`. It does not know its own successor, the
   destination, or its position in the path. This is the one relay in the system with
   no downstream knowledge — the property is structural, not a discipline we impose.
3. **Only one cause can produce it.** Which decides question 4 below more or less on
   its own.

**Current build, for reference** (`relay/relay_node.py:125`) — an implementation
default from Phase 1, not a protocol ruling:

```python
return 400, {"error": "layer_undecryptable", "reported_by": self.relay_id}
```

---

## 2. Options

### P1 — Status only, empty body

Non-2xx with no body at all.

**For:** cannot leak anything; nothing to specify.
**Against:** the predecessor must distinguish "my successor could not decrypt" from
"my successor is broken in some other way" in order to report accurately upstream, and
an empty body gives it nothing to distinguish on. It would have to infer meaning from
the status code, which §9.3 explicitly forbids as a discriminator. It also discards
`reported_by`, which SD-011 fixes as part of the error form.

### P2 — Uncoded body

A body with a human-readable reason but no value from any closed set, e.g.
`{"error": "relay_error", "reported_by": "relay-04"}`.

**For:** keeps §9.1's vocabulary strictly inside the sealed channel, so there is
visibly one authoritative code set and no second one to confuse it with.
**Against:** it is a code in all but name — `relay_error` is a fixed string the
predecessor will branch on — while being outside the closed set, so it is unvalidated
and undocumented. It buys the appearance of separation at the cost of a real one.

### P3 — Coded body, drawn from §9.1 *(recommended)*

```json
{ "error": "decryption_failure", "reported_by": "<own relay_id>" }
```

**For:** it is the form SD-011 already fixes — *"An error carries
`{"error": "<code>", "reported_by": "<own relay_id>"}` … this is the part SD-011 fixes,
and it holds whatever envelope the error ends up in."* It is what the current build
emits, modulo the code's spelling. And it is the reading SD-024 residual 1 itself
identifies as the natural one.
**Against, and it must be answered rather than waved past:** it puts a value from the
**sealed** protocol vocabulary into an **unsealed** channel, which looks like the
two-sources-of-truth problem §9.3 was written to remove. See §4.

### P4 — Coded body, separate fallback vocabulary

A distinct code set for the fallback, e.g. `cannot_seal`.

**For:** no vocabulary overlap between sealed and unsealed channels at all.
**Against:** it invents protocol surface for a channel with exactly one possible
cause, and creates a second closed set that must be specified, validated and kept in
sync for no behavioural gain. It also makes the predecessor's translation step
arbitrary rather than derived.

---

## 3. The ten questions, answered under P3

### 1. Exact HTTP status behaviour

**A single status: `400 Bad Request`.** No status-based sub-classification, no range
of statuses carrying meaning.

`400` is the accurate reading: from this relay's position the sender supplied a layer
it cannot open, which is a defect in the request as received. `502` belongs to
`next_hop_unreachable`, which cannot occur here.

**The status carries no protocol meaning.** §9.3 already states that the client must
not use HTTP status as the success/error discriminator; the same applies to a
predecessor relay reading this response. The status says only "this is not a sealed
envelope" — which is precisely the transport-level fact it is entitled to convey.

### 2. Exact plaintext response body shape

```json
{
  "error": "decryption_failure",
  "reported_by": "<the emitting relay's own relay_id>"
}
```

Two fields, both required, both strings. No other field is permitted. `Content-Type:
application/json`, matching every other relay response.

### 3. Does the body contain a protocol error code?

**Yes.** The alternative is that the predecessor must guess what happened in order to
report it, and a guess is what the sealed protocol was designed to eliminate.

### 4. Which error codes are permitted here?

**Exactly one: `decryption_failure`.** Not a subset chosen for tidiness — the other
two are unreachable:

| §9.1 code | Can it appear in the fallback? |
|---|---|
| `decryption_failure` | **Yes** — it is the only cause that leaves a relay without a key |
| `next_hop_unreachable` | **No** — the relay decrypted, holds `K`, and seals |
| `destination_unreachable` | **No** — same |

**This resolves the objection to P3.** The overlap between the sealed and unsealed
vocabularies is one value, and it is the same fact in both channels: a relay could not
decrypt. There is no case where a plaintext code and a sealed code could disagree,
because the plaintext code has a domain of size one. The two-sources-of-truth risk
§9.3 guards against does not arise.

Note this also aligns the spelling: the current build says `layer_undecryptable`, which
is not a §9.1 value. Adopting P3 makes it `decryption_failure`.

### 5. What must NOT be exposed

- **No decryption diagnostics.** No exception text, no `InvalidTag`, no indication of
  *how* decryption failed, no distinction between a bad RSA unwrap and a failed GCM
  tag. This is the decryption-oracle concern and it is the reason the body is a fixed
  string rather than a message.
- **No key material, nonces, ciphertext, or plaintext byte lengths.**
- **No `request_id`** — SD-003 keeps it relay-local and off the wire.
- **No downstream relay identity** — see question 6.
- **No destination host or port, no path information, no hop index.**

The current build is already compliant on every point: it logs the exception locally
(`relay_node.py:119`) and returns only the fixed code and its own id.

### 6. Can the fallback reveal downstream relay identity?

**No — and it is structurally incapable of doing so.** The emitting relay failed before
parsing `next_hop`, so it does not know its successor's identity. There is nothing to
withhold.

`reported_by` names the emitting relay itself, which SD-011 expressly permits: *"a
relay may identify itself as the reporter."* The recipient is that relay's immediate
predecessor, which already knows its identity because it just sent to it — or the
client, when the emitter is the entry relay, which the client selected. **No party
learns anything it did not already know.**

### 7. Interaction with SD-011, SD-024/E2 and SD-024/D2

**SD-011 — satisfied, and P3 is the option that keeps it intact.** SD-011's recorded
error form is `{"error": "<code>", "reported_by": "<own relay_id>"}` and its invariant
is about relay identity only. P3 is that form exactly. P1 discards it.

**SD-024 §A / E2 — consistent.** E2 requires sealing *when the relay possesses the
key*. This response exists only where it does not. The fallback is E2's stated
exception, not an erosion of it.

**SD-024 §B / D2 — untouched.** D2 governs the *sealed inner plaintext* and its three
types. The fallback is not a sealed response and carries no `type` field; it must not
be confused with a `{"type": "error"}` object. They are different objects in different
channels, and P3 does not blur them: the fallback has `error` and `reported_by`, the
sealed form has `type`, `code` and `reported_by`.

**What the predecessor does with it — the one point worth care.** On receiving the
fallback, the predecessor emits its own **sealed** error:

```json
{ "type": "error", "code": "decryption_failure", "reported_by": "<predecessor's id>" }
```

That looks at first like a misattribution — the predecessor decrypted fine. It is not,
under SD-024's own definition: §D says `reported_by` means *"the last relay that
successfully processed the request and is reporting the failure"*, which is exactly the
predecessor. `reported_by` names the **reporter**, never the **failer**. The `code`
describes the failure on the path; `reported_by` describes who is telling you. Read
that way the translation is exact and requires no change to SD-024.

This is also the single adjacency SD-024 §J narrows SD-011's rewriting rule to, so the
two decisions meet here and agree.

### 8. Client behaviour on receiving the fallback

The client sees the plaintext fallback **only when the entry relay cannot decrypt**.
At any deeper hop it receives the predecessor's sealed error instead and never sees
plaintext.

When it does see it:

- Classify as a **protocol error** — §9.2 row 2. It is relay-generated, not a
  client-side condition, and must not be collapsed into the malformed-response or
  transport-failure categories.
- Raise `OnionPathError` naming the entry relay as `reported_by`, matching the
  behaviour for a sealed error.
- **Do not retry, do not rebuild the circuit, do not try another path** — §9's "no
  automatic circuit rebuild" is unchanged.
- **Do not treat the `400` as authoritative.** The body's `error` field is what is
  read; the status only signalled that no envelope was coming.

`client/onion_client.py:264` already reads `exc.body.get("error", …)` and
`exc.body.get("reported_by", …)` in exactly this shape, so the client's existing
handling is compatible with P3 as written.

### 9. Test implications

**Survives unchanged:** `test_garbage_envelope_is_refused_with_400`
(`tests/test_phase1.py:488`) — the freeze review §7.3 already identified this as the
one failure test SD-024 preserves, because feeding a relay garbage is precisely the
fallback case. Its `assertEqual(status, 400)` holds under P3.

**Needs its expected string updated:** any assertion on `layer_undecryptable`, which
becomes `decryption_failure`.

**New tests, additional to OPEN-9's seven:**

1. The fallback body is exactly `{"error": "decryption_failure", "reported_by": <id>}`
   — two keys, no more.
2. The fallback body contains no decryption diagnostics: assert the exception text
   does not appear in it.
3. A predecessor receiving the fallback emits a **sealed** error with
   `reported_by` = its own id, and the client can open it.
4. That sealed error does **not** name the relay that failed to decrypt — the SD-011
   invariant, at the one adjacency where it still applies.
5. Entry-relay fallback reaches the client as `OnionPathError` naming the entry relay,
   classified as a protocol error rather than a client-side condition.

Log-hygiene coverage (OPEN-9 test 7) should extend over the fallback path, since it is
the branch that has real diagnostics to accidentally emit.

### 10. Does this change cryptographic or layered-response semantics?

**No, and it cannot.** The fallback is by definition the case where no sealing occurs.
Unchanged: AES-GCM parameters, RSA-OAEP key delivery, the fresh-nonce-per-encryption
rule (§7, §9.5), layer construction (§5.1–5.3), the return-path nesting, and the
visibility table (§6). `common/onion_crypto.py` needs no change under any option here.

The one thing P3 settles is what a relay writes when it has **no** key — which is the
complement of everything the crypto layer governs.

---

## 4. Comparison

| | P1 | P2 | **P3** | P4 |
|---|---|---|---|---|
| Predecessor can report accurately | **No** | Yes | **Yes** | Yes |
| Preserves SD-011's error form | **No** | Partly | **Yes** | Partly |
| Vocabulary overlap with sealed channel | None | None | **One value, one meaning** | None |
| Can the two channels disagree? | n/a | No | **No — domain of size one** | No |
| New protocol surface | None | Informal | **None** | **A second code set** |
| Matches the current build | No | No | **Yes, modulo spelling** | No |
| Client code changes needed | Yes | Yes | **No** | Yes |

---

## 5. Recommendation

**P3, with the permitted code set restricted to the single value `decryption_failure`.**

Stated as it would appear in an SD entry:

> The plaintext fallback carries `400 Bad Request` and a body of exactly
> `{"error": "decryption_failure", "reported_by": "<own relay_id>"}`. `decryption_failure`
> is the only permitted value, because it is the only cause that can leave a relay
> unable to seal. The status carries no protocol meaning. The body carries no
> diagnostics, no key material, no `request_id`, and no downstream identity — the
> emitting relay possesses none of these, having failed before parsing its layer. A
> predecessor receiving it emits its own sealed `{"type": "error", "code":
> "decryption_failure", "reported_by": "<its own id>"}`, which is exact under SD-024 §D:
> `reported_by` names the reporter, not the failer.

**Confidence: high**, for an unusual reason — this is close to a derivation rather than
a choice. Once §9.3 fixes *when* the fallback occurs, the cause is unique, the code set
collapses to one value, the leak surface is empty because the emitter knows nothing,
and SD-011 already fixes the field shape. P1 and P4 are the options that require
adding something; P3 requires only writing down what the surrounding decisions already
imply.

**The strongest argument against, recorded rather than dismissed.** P3 does place a
sealed-protocol code in an unsealed channel, and a reader coming to §9 fresh may take
that as licence to read plaintext codes as protocol truth generally. The mitigation is
wording, not design: the amendment should say that this is the sole plaintext code, in
the sole plaintext case, and that §9.3's prohibition on status-as-discriminator applies
to relays reading the fallback exactly as it applies to the client.

---

## 6. One adjacent gap, flagged and not decided

**`layer_malformed` has no home under SD-024.** The current build returns
`400 {"error": "layer_malformed"}` when a layer decrypts but its JSON is unusable
(`relay_node.py:137`). Under SD-024 that relay **holds `K`** and must therefore seal —
but §9.1's closed set has no code for a malformed layer, and §9.1 explicitly excludes
`malformed_response` as a *client-side* concern, which this is not: this is a relay
detecting malformation in its **own** layer, not in relayed content.

**This is outside B4** — it concerns the sealed channel, not the plaintext fallback —
and deciding it here would reopen SD-024's closed code set, which is out of scope. It
is raised because it sits one line away in the same function and **will surface the
moment OPEN-9 implementation begins**. It needs an answer before OPEN-9 can close.

---

**Nothing above has been done.** `RELAY_PROTOCOL.md`, `relay/`, `client/`,
`tests/` and `SPEC_DECISIONS.md` are unmodified. No SD entry created or amended.
OPEN-9 not started. Phase 5 not started. No commit.
