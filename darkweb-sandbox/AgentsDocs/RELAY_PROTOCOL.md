# RELAY_PROTOCOL.md

**Repo:** `darkweb-sandbox`
**Prerequisite:** read `MASTER_CONTEXT.md` first.
**Covers:** key handling, layer construction, per-hop processing, return path, path selection.

This document is the authoritative spec for the routing layer. If code and this document disagree, this document is correct.

---

## 1. What this layer must prove

A request travels through N relays. **No single relay knows both where the request came from and where it is ultimately going.** Each relay decrypts exactly one layer, learns only its immediate next hop, and forwards an opaque blob it cannot read.

That property is the entire point. Every design decision below serves it. If an implementation choice would let a middle relay see the final destination or the request body, the implementation is wrong.

---

## 2. Cryptographic primitives

**Use the Python `cryptography` library. Do not implement any cryptographic primitive by hand.**

| Purpose | Algorithm | Parameters |
|---|---|---|
| Per-hop key delivery | RSA-OAEP | 2048-bit keys, SHA-256 |
| Layer payload encryption | AES-GCM | 256-bit key, 96-bit nonce |
| Serialization | JSON → UTF-8 bytes → base64 where transport requires text | — |

**Why hybrid (RSA + AES) and not RSA alone:** RSA-OAEP with a 2048-bit key can only encrypt ~190 bytes. Layers are larger than that. Real Tor solves this the same way — asymmetric crypto to establish a symmetric key, symmetric crypto for the payload. Do not try to RSA-encrypt a whole layer; it will fail on size and the fix is not "bigger keys."

---

## 3. Relay identity and key distribution

At container startup, each relay:

1. Generates an RSA-2048 keypair **in memory** (no keys on disk, no keys in the repo, no keys in git)
2. Registers with the directory service: `relay_id`, `host`, `port`, `public_key` (PEM), `status: up`
3. Holds its private key for the lifetime of the container

The directory **never** sees or stores any private key. Only public keys.

Relay IDs are stable and human-readable for demo legibility: `relay-01` … `relay-07`.

---

## 4. Path selection

1. Client calls the directory: `GET /path?hops=3`
2. Directory picks `hops` distinct relays **at random, without replacement**, from all relays currently `up`
3. Directory returns them **in order**, each with `relay_id`, `host`, `port`, `public_key`

Rules:
- Default `hops = 3`. Must be configurable. Pool is 5–7 relays, so `hops` may range 2–5
- No relay appears twice in one path
- Selection is uniform random. **No** bandwidth weighting, uptime weighting, or reputation — see `MASTER_CONTEXT.md` scope lock
- A new path is selected per scrape session, so consecutive runs visibly differ. This is a demo requirement, not an optimisation

---

## 5. Layer construction (client side)

Given path `[A, B, C]` and a request destined for mock site `forum-alpha`:

Build **innermost first, working outward.**

### 5.1 Plaintext layer structure

Every layer, before encryption, is this JSON object:

```json
{
  "next_hop": "<relay_id | DESTINATION>",
  "next_host": "<host>",
  "next_port": <port>,
  "payload": "<base64 of the next encrypted layer, or of the raw request if exit>"
}
```

### 5.2 Encrypting one layer for one relay

```
K      = random 256-bit AES key
nonce  = random 96-bit nonce
ct     = AES-GCM-encrypt(K, nonce, json_bytes(layer))
enc_K  = RSA-OAEP-encrypt(relay_public_key, K)

wire_layer = {
  "enc_key": base64(enc_K),
  "nonce":   base64(nonce),
  "ciphertext": base64(ct)
}
```

### 5.3 Full construction for path [A, B, C]

```
L3 = { next_hop: "DESTINATION", next_host: "forum-alpha", next_port: 80,
       payload: base64(raw_http_request) }
W3 = encrypt_layer(L3, C.public_key)

L2 = { next_hop: "relay-C", next_host: C.host, next_port: C.port,
       payload: base64(W3) }
W2 = encrypt_layer(L2, B.public_key)

L1 = { next_hop: "relay-B", next_host: B.host, next_port: B.port,
       payload: base64(W2) }
W1 = encrypt_layer(L1, A.public_key)

send W1 → relay A
```

The client sends **only** `W1` to relay A. It sends nothing to B or C directly.

---

## 6. Per-hop processing (relay side)

Every relay runs identical logic. A relay does not know whether it is entry, middle, or exit until it decrypts its layer.

```
on receive(wire_layer):
    K     = RSA-OAEP-decrypt(my_private_key, wire_layer.enc_key)
    layer = json(AES-GCM-decrypt(K, wire_layer.nonce, wire_layer.ciphertext))

    remember (request_id → K, nonce)   # needed for the return path, Section 7

    # K is held from here on, so every failure below is SEALED, never plaintext.
    validate layer:
        next_port must be an integer port value, not a float and not a boolean
        payload   must decode as base64
      on failure -> seal {"type":"error","code":"unusable_layer",...}, HTTP 200

    if layer.next_hop == "DESTINATION":
        response = http_request(layer.next_host, layer.next_port, decode(layer.payload))
        content  = {"type": "success", "body": b64(response)}          # Section 7
    else:
        response = forward(layer.next_host, layer.next_port, decode(layer.payload))
        content  = {"type": "relay", "inner": b64(response)}           # opaque bytes

    return encrypt_response(json(content), K, fresh_nonce)
```

**On failure, a relay that still holds `K` seals an error for its predecessor**
rather than answering in plaintext:

```
    on failure(cause):
        if K is known:
            content = {"type": "error", "code": cause, "reported_by": my_relay_id}
            return HTTP 200, encrypt_response(json(content), K, fresh_nonce)
        else:
            return HTTP non-2xx, plaintext        # cannot seal -- see Section 9
```

A relay reaches the `else` branch only when it could not decrypt its own layer, and
therefore holds no key. That is the **only** case in which a relay answers in
plaintext.

**The validation step above is deliberately after the decrypt.** A layer that reaches
it has already passed the AES-GCM tag check, so its contents came from whoever holds
`K` — the client. A tampered or corrupted layer fails the tag and takes the plaintext
branch instead. A relay that decrypted successfully **holds `K` and must seal**, even
when what it decrypted is unusable; it must not discard the key in order to answer in
plaintext. See §9.1's `unusable_layer`.

**A relay MUST NOT parse the response it is forwarding.** `inner` carries base64
bytes, not a nested object, precisely so that no hop needs to look inside to decide
what to do with it. A relay that parses relayed content creates a detection point
this design removes deliberately.

**What each relay can see — verify your implementation against this table:**

| | Sees client identity | Sees next hop | Sees final destination | Sees request body |
|---|---|---|---|---|
| Relay A (entry) | Yes | Yes (B) | **No** | **No** |
| Relay B (middle) | **No** (sees A) | Yes (C) | **No** | **No** |
| Relay C (exit) | **No** (sees B) | n/a | Yes | Yes |

If your implementation lets B see the destination, the layering is broken. This table is the acceptance test for Phase 1 and Phase 3.

**Note for the demo, state this openly if asked:** the exit relay sees the request body in cleartext. That is true of real Tor as well and is a genuine, well-documented property of onion routing, not a flaw in this implementation.

---

## 7. Return path

The response travels back along the same path, gaining a layer at each hop.

- Each relay retains the AES key `K` it derived on the forward pass, keyed by `request_id`, for the duration of that request only
- Exit relay C encrypts the site's response with its `K` and a **fresh nonce**, returns it to B
- B encrypts what it received with its own `K` and a fresh nonce, returns it to A
- A does the same, returns to the client
- Client decrypts in order A → B → C, using the keys it originally generated

**What falls out of each decryption is a typed object, not raw bytes.** The outer
wire envelope is unchanged — `{ "nonce": "<b64>", "ciphertext": "<b64>" }` — and the
discriminator lives inside the decrypted plaintext:

| `type` | Carries | Meaning |
|---|---|---|
| `relay` | `inner` — base64 of the successor's response bytes | Keep unwrapping |
| `success` | `body` — base64 of the destination's raw HTTP response | Terminal. Application response |
| `error` | `code`, `reported_by` | Terminal. Protocol error |

The client unwraps until it reaches a **terminal** type. It **must not** decide
success from error by counting layers, and it **must not** use the HTTP status of any
hop as the discriminator — the sealed `type` is authoritative. A relay error travels
sealed under exactly the same layers as a success, so no intermediate relay can tell
one from the other.

A destination's own `404` or `500` is a **`success`** at this layer: the request was
carried and answered. It is an application response, not a protocol error.

**Never reuse a nonce with the same key.** Generate a fresh nonce for every encryption operation, forward and return. AES-GCM's security fails catastrophically on nonce reuse — this is the one crypto rule in this document that has real consequences if ignored.

Per-request keys are discarded once the response is returned. No session persistence.

---

## 8. Logging — a demo requirement, not an afterthought

The visual payoff of this system is watching each container peel exactly one layer. Each relay must log, per request:

```
[relay-03] recv request_id=a7f3 from 172.20.0.4
[relay-03] decrypted layer -> next_hop=relay-06
[relay-03] forwarding 1184 bytes (opaque)
[relay-03] recv response, re-encrypting, returning to 172.20.0.4
```

Rules:
- Log the **next hop only**. Never log the full path, the destination, or decrypted payload content — a relay that logs those does not actually have the isolation property you are claiming
- Log payload **sizes**, never payload **contents**
- Never log keys, nonces, or ciphertext

---

## 9. Failure behaviour

Deliberately minimal — see scope lock.

- Relay unreachable → the request fails with a clear error naming the failed hop. **No** automatic circuit rebuild
- Decryption failure → log and drop, return an error. Do not retry with a different key
- Directory unreachable → client fails with a clear error. No cached fallback path
- Mock site unreachable → exit relay returns an error response through the normal return path

### 9.1 Error codes — a closed set of four

```
next_hop_unreachable
decryption_failure
destination_unreachable
unusable_layer
```

These are the only values `code` may take. The first three map to bullets 1, 2 and 4
above. Bullet 3, directory unreachable, is client-side and never appears on the wire.
**`unusable_layer` maps to no bullet** — §9's four bullets never contemplated the case.

**`unusable_layer` — a decrypted layer the relay cannot act on.** It applies only
after the relay has **successfully decrypted and authenticated its own layer**, and
therefore holds the correct key, but cannot use what it decoded:

- `next_port` is not a usable integer port value, or
- `payload` cannot be decoded as base64.

Everything that fails earlier — a bad base64 wire field, a wrong nonce length, a failed
RSA unwrap, a failed AES-GCM tag, unparseable JSON, a missing required field — is a
**`decryption_failure`**, not this.

The relay **holds `K` and MUST seal** the error, returning **HTTP 200** with:

```json
{ "type": "error", "code": "unusable_layer", "reported_by": "<detecting relay>" }
```

`reported_by` is the detecting relay itself. No downstream identity is available to
leak — the relay never resolved `next_hop` into a forwarding attempt — and no
diagnostic goes on the wire: not the offending field, its value, or any exception text.
Those belong in the relay's own log (§8).

**`unusable_layer` is not `malformed_response`.** The exclusion below concerns
**relayed content**, which no relay parses. `unusable_layer` concerns a relay's **own
layer**, which the protocol requires it to parse and which it is therefore the only
party able to detect.

**`hop_timeout` and `malformed_response` are not error codes.**

- A **hop timeout** maps to whichever unreachable cause fits the hop that timed out:
  waiting on the next relay → `next_hop_unreachable`; waiting on the destination →
  `destination_unreachable`. `HOP_TIMEOUT` is a bound, not a cause.
- A **malformed or unparseable response** is a **client-side** parsing failure. No
  relay parses relayed content (§6), so no relay is in a position to detect one.

### 9.2 Four outcomes that must not collapse into each other

| Outcome | Category |
|---|---|
| Sealed `success` — including the site's own 4xx/5xx | Application response |
| Sealed `error` | Protocol error |
| Malformed or unparseable protocol response | **Client-side** condition |
| Transport timeout or unreachable | **Client-side** condition |

### 9.3 HTTP status is transport, not protocol

- **HTTP 200** whenever a sealed response envelope is returned — **regardless of
  whether the sealed type is `success` or `error`**.
- **HTTP non-2xx** survives in exactly one case: a relay that could not decrypt its
  own layer, holds no key, and therefore cannot seal anything for its predecessor.
- **The client MUST NOT use HTTP status as the success/error discriminator.**

#### The plaintext fallback response

**HTTP 400**, `Content-Type: application/json`, and a body of **exactly two required
string fields**:

```json
{ "error": "decryption_failure", "reported_by": "<own relay_id>" }
```

- **`decryption_failure` is the only permitted value** of `error` here. The other §9.1
  codes are unreachable in this channel: a relay that experiences any of them holds
  `K` and seals instead.
- **This response occurs only** when a relay cannot decrypt its own layer, holds no
  usable key, and therefore cannot seal a response for its predecessor.
- **It travels exactly one hop and is never forwarded as a protocol response.** A
  predecessor that receives it emits **its own sealed** error,
  `{"type": "error", "code": "decryption_failure", "reported_by": "<its own id>"}`,
  naming itself. It does not pass the plaintext on, and it does not name its
  successor.
- **If the entry relay itself cannot decrypt**, the client receives this plaintext
  response directly and classifies it as a **protocol error** (§9.2), not a
  client-side condition.
- **Nothing else may appear in it.** No downstream relay identity, destination, path,
  hop index, `request_id`, diagnostic message, exception text, key material, nonce,
  ciphertext, or any other protocol metadata.

The field is named `error`, not `code`: the sealed protocol object of §7 carries
`code`, and the two are deliberately distinct so that no reader mistakes an unsealed
transport-level body for the authoritative sealed one.

### 9.4 Who is named

`reported_by` is **the last relay that successfully processed the request and is
reporting the failure**. A relay **MUST NOT** name a downstream relay it could not
reach or whose response it could not decrypt.

Because a sealed error is opaque to every relay above the one that produced it, the
client now learns the relay that **actually detected** the failure — for a middle-hop
failure, `path[1]` rather than `path[0]`. That is closer to the intent than the
plaintext behaviour it replaces, and the invariant is unchanged: the failed
downstream relay is still never named.

### 9.5 Cryptography is unchanged

Error layers are sealed with the same AES-GCM construction, the same key `K`, and the
**same fresh-nonce-per-encryption rule** as any other return layer. §7's nonce rule
applies to error layers without exception. No new primitive is introduced.

> **Status.** §§9.1–9.5 record `SPEC_DECISIONS.md` SD-024, as amended by **SD-029**
> (the plaintext fallback body, §9.3) and **SD-030** (`unusable_layer`, §6 and §9.1).
> **Both are IN FORCE as of 2026-09-08**, and their amendments are implemented and
> verified: `relay/relay_node.py` seals typed responses and errors,
> `client/onion_client.py` branches on the sealed `type`, and `tests/test_phase1.py`
> covers both. **OPEN-9 is closed.**

---

## 10. Explicitly out of scope

Do not build any of these. They are on the `MASTER_CONTEXT.md` OUT list:

- Directory authorities, consensus documents, voting
- Telescoping circuit construction / incremental hop-by-hop key negotiation (real Tor's `CREATE`/`EXTEND` cells). We use direct RSA-to-each-relay key delivery, which is simpler and sufficient here
- Perfect forward secrecy / ephemeral Diffie-Hellman handshakes
- Onion service descriptors, DHT lookup, introduction points, rendezvous points
- Guard node persistence, path bias defences
- Traffic padding, timing-attack mitigation, fixed-size cells

**If asked on stage why these are absent:** they are the parts of Tor that provide real-world anonymity against a global adversary. This system demonstrates the routing and layered-encryption mechanism, not anonymity. Say that plainly.

---

## 11. Phase 1 acceptance criteria

Phase 1 is complete when, with a **single hardcoded hop**:

1. A relay generates a keypair at startup and registers its public key with the directory
2. The client encrypts one layer to that relay's public key
3. The relay decrypts it, reads `next_hop = DESTINATION`, fetches from a mock site
4. The relay encrypts the response with the same `K` and a fresh nonce
5. The client decrypts the response successfully
6. Relay logs show the hop, in the format above, with no payload contents

Do not proceed to Phase 2 until every item above is demonstrated and a human has confirmed. Write the phase report per `MASTER_CONTEXT.md` Section 6.
