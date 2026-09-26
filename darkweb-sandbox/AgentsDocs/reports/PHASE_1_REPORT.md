# Phase 1 Report

**Date:** 2026-09-07
**Scope note:** Phase 1 here means relay pool + directory + multi-hop path, per
`AgentsDocs/SPEC_DECISIONS.md` SD-000. That covers what
`AgentsDocs/IMPLEMENTATION_PLAN.md` calls Phases 1, 2 and 3. The scope change was a
human instruction, not an inference, and it is what makes
`RELAY_PROTOCOL.md` §11 criterion 1 satisfiable at all.

---

## Built

- `AgentsDocs/SPEC_DECISIONS.md` — Phase-0 decision record, 14 decisions, 8 open items deferred
- `common/onion_crypto.py` — RSA-OAEP + AES-GCM envelope; the only file that calls `cryptography`
- `common/http_util.py` — JSON-over-HTTP helpers and a base handler that suppresses the stdlib's request logging
- `directory/directory_service.py` — in-memory registry, `POST /register`, `GET /path?hops=N`, `GET /relays`, `POST /relays/{id}/status`
- `relay/relay_node.py` — in-memory RSA-2048 keypair, registration with retry, one-layer decryption, forwarding, exit fetch, response re-encryption
- `client/onion_client.py` — path request, innermost-first layer construction, send-to-entry-only, ordered response unwrap, `.onion.mock` resolution
- `phase1_endpoint/static_endpoint.py` — static connectivity target, no persona content (SD-012)
- `scripts/phase1_demo.py` — Docker-free end-to-end demo
- `tests/harness.py`, `tests/test_phase1.py` — 38 tests
- `Dockerfile`, `docker-compose.yml`, `requirements.txt`
- `.gitignore` — appended `.venv/`, `__pycache__/`, `*.pyc`

---

## Tested — how, not just whether

`python -m unittest discover -s tests -t .` against the real directory, relays,
client and endpoint on loopback sockets. Nothing stubbed, nothing mocked, no
network access. **38 tests, 38 passed, 0 failed**, 66s.

Observed directly:

- **Layering.** A 3-hop request's outer layer was decrypted with the entry relay's
  private key and asserted to name only relay B; the inner blob was decrypted with
  B's key and asserted to name only relay C; C's layer holds `DESTINATION` and the
  verbatim request. Each relay's key was also tried against the other relays'
  layers and rejected.
- **Visibility table (`RELAY_PROTOCOL.md` §6).** Asserted on real bytes: the
  destination hostname and the request-body marker appear in the exit relay's
  decrypted layer and in neither of the two upstream ones. The endpoint is
  addressed as `localhost` while relays advertise `127.0.0.1`, so the assertion
  distinguishes "a relay" from "the destination" rather than matching loopback
  generally.
- **Nonces.** All 5 forward-layer nonces distinct at `hops=5`; all 3 response
  nonces distinct; forward and return nonce sets disjoint; no nonce repeated
  across 5 consecutive runs. This is the rule §7 says has real consequences.
- **Log hygiene.** Logs captured during a live run and asserted to contain no
  `PRIVATE KEY`, no relay public PEM, no session key, no nonce from either leg,
  no ciphertext, not the destination host, and not the page content. Separately,
  each relay was asserted to emit exactly one `decrypted layer ->` line naming
  only its own successor.
- **End to end.** Works at `hops=2,3,4,5`. 10 consecutive runs returned the page
  and used more than one distinct path.
- **Directory.** 7 relays registered; `hops=1` and `hops=6` rejected 400; a downed
  relay excluded across 25 draws at `hops=5`; with 2 up, `hops=3` returned 503
  naming the shortfall; a registration carrying a private key rejected 400.
- **Failure.** Unreachable entry relay, unreachable middle relay and unreachable
  destination each raised a named `OnionPathError` within the timeout, no hang. A
  relay fed garbage returned 400 and served the next real request correctly.

`python -m scripts.phase1_demo` run twice; both runs returned the page through
different paths, printed the per-hop visibility breakdown, and confirmed the page
bytes identical across both paths.

---

## Stubbed / faked / incomplete

- **`docker-compose.yml` and `Dockerfile` are now verified** — see "Docker
  verification" below. Nothing in this report is unbuilt scaffolding.
- The Phase-1 endpoint is a connectivity target, not a mock site. No persona, PGP
  block or wallet — deliberately, per SD-012.
- `MOCK_ADDRESS_MAP` carries the three Phase-4 addresses from
  `MOCK_SITES_SPEC.md` §6. They are inert data until those containers exist and
  raise a named `AddressError` if used before then.
- No scraper, no mock sites, no GOTHAMITE ingestion. Phases 4–6 untouched.

---

## Deviations from the docs

All recorded in `AgentsDocs/SPEC_DECISIONS.md` with rationale. The ones that
change observable behaviour:

- **SD-003** — `request_id` is relay-local, not carried on the wire, because
  §5.1 fixes the layer at four fields and a shared id would link every relay's
  view of one request. Consequence: a single request cannot be traced by id
  across three relay logs.
- **SD-011** — a relay reports itself in a propagated error and never names a
  downstream relay, because doing so would tell the entry relay about hops it is
  not entitled to know. §9's "naming the failed hop" is therefore satisfied in
  the detecting relay's own log rather than end-to-end. **Approved in principle.**
  Its scope is relay identity only; the error *envelope* is not decided by it and
  is tracked as OPEN-9.
- **Errors are currently plaintext JSON with a non-2xx status at every hop.** For
  three of the four cases in `RELAY_PROTOCOL.md` §9 that is unconstrained, but the
  fourth — "mock site unreachable → exit relay returns an error response through
  the normal return path" — implies a sealed envelope, so the current build
  deviates there. Recorded as OPEN-9, not resolved. Phase 1 acceptance is
  unaffected: Phase 3 criterion 6 asks for "a clear named error, no hang", which
  the current form satisfies.
- **SD-009** — pool size fixed at 7 within the documented 5–7 range, so
  `format/DEMO_SCRIPT.md`'s spoken "seven nodes" is literally true.
- **SD-005** — no web framework; standard library only. `cryptography` is the
  sole third-party dependency, and it is mandated by name in `RELAY_PROTOCOL.md`
  §2, so nothing needed flagging under `MASTER_CONTEXT.md` §5 rule 5.

---

## Blocked

Nothing blocks Phase 1. Blocking later phases, listed as OPEN-1..8 in
`SPEC_DECISIONS.md` §2 and not resolved here:

- **OPEN-1** — whether `AgentsDocs/DATA_MODEL.md` or a GOTHAMITE-side copy is
  authoritative. Blocks Phases 4 and 5.
- **OPEN-2** — `README.md` §4 and `DATA_MODEL.md` §4 give persona A1 two different
  wallet addresses, and the scraper regex can only match one of them. Blocks
  Phases 4 and 5.
- OPEN-3..8 — decoy count, index-page persona, identifier types, URL scheme,
  timestamp timezone, Phase-4 gate sequencing.
- **OPEN-9 (new)** — the error envelope is unspecified in `RELAY_PROTOCOL.md`.
  Needs a human protocol decision before Phase 6 hardening; see above.

**New, found during implementation:** `http.server` stamps a `Date:` header, so a
raw HTTP response is not byte-identical between runs even when the page is. This
does not affect Phase 1, but Phase 4 acceptance 7 ("identical bytes every time")
and Phase 5's `content_hash` over `raw_content` both need to say whether they mean
the page or the whole response. Not resolved here.

---

## Acceptance criteria

**`RELAY_PROTOCOL.md` §11 — Phase 1**

- [x] 1. Relay generates a keypair at startup and registers its public key with the directory
- [x] 2. Client encrypts one layer to that relay's public key
- [x] 3. Relay decrypts it, reads `next_hop = DESTINATION`, fetches from the endpoint
- [x] 4. Relay encrypts the response with the same `K` and a fresh nonce
- [x] 5. Client decrypts the response successfully
- [x] 6. Relay logs show the hop in the §8 format, with no payload contents

**`DIRECTORY_SPEC.md` §5 — Phase 2**

- [x] 1. 5–7 relays start and register (7)
- [x] 2. Ten consecutive `/path?hops=3` calls return visibly different orderings
- [x] 3. No path contains a duplicate relay
- [x] 4. A relay set to `down` never appears in a returned path
- [x] 5. `hops=1` and `hops=6` both rejected with 400
- [x] 6. With only 2 relays up, `hops=3` returns 503 naming the shortfall
- [x] 7. Directory logs contain no private keys and no full path compositions

**`IMPLEMENTATION_PLAN.md` §3 — Phase 3**

- [x] 1. 3-hop request completes end to end, response decrypted correctly
- [x] 2. The visibility table in `RELAY_PROTOCOL.md` §6 holds, verified by inspecting what each relay actually decrypts
- [x] 3. Each relay logs exactly one hop, no payload contents
- [x] 4. Two consecutive runs use different paths
- [x] 5. Works at `hops=2` and `hops=5`
- [x] 6. A downed relay produces a clear named error, no hang
- [x] `docker-compose.yml` bringing up directory + 5–7 relays — **executed and verified**, including a 3-hop carry over `sandbox-net`

---

## Docker verification

Run against the live compose stack. Docker Desktop is installed per-user at
`%LOCALAPPDATA%\Programs\DockerDesktop
esourcesin`, which is not on PATH —
earlier reports in this file said "no Docker on this machine", which was wrong;
the CLI was simply not where the shell looks.

**Topology and registration.** `docker compose up --build -d`, then
`curl http://localhost:8000/relays` → `count=7`, `relay-01`..`relay-07`, all
`status="up"`. Registration is the end of a chain that fails if any link is wrong:
the image builds, seven services start from the YAML anchor matrix with distinct
`RELAY_ID`/`RELAY_PORT`, the healthcheck-gated `depends_on` releases them,
`sandbox-net` resolves relay hostnames, and every container reaches
`http://directory:8000/register`.

**Path selection in containers.** Two consecutive `GET /path?hops=3` calls
returned `p_22a1c4` = relay-01 → relay-06 → relay-03 and `p_e6ff76` =
relay-07 → relay-03 → relay-04: different orderings, no duplicate within a path.

**3-hop carry over the bridge network.**

```
docker compose run --rm --entrypoint python directory -m client.onion_client   --directory http://directory:8000 --hops 3   --host phase1sandbox.onion.mock --resource /
```

Path `p_0944c4` = relay-02 → relay-01 → relay-03. Returned 550 bytes, `200 OK`
from `phase1-endpoint`, marker `phase1-endpoint-ok` present, decrypted through
three layers. This is the item the previous revision of this report left open:
relay→relay and relay→endpoint traffic over `sandbox-net` rather than loopback.

**Visibility table holds in containers**, verified from the three relays' own
logs rather than asserted:

```
relay-02  decrypted layer -> next_hop=relay-01     forwarding 1857 bytes (opaque)
relay-01  decrypted layer -> next_hop=relay-03     forwarding  749 bytes (opaque)
relay-03  decrypted layer -> next_hop=DESTINATION  forwarding  120 bytes (opaque)
```

Each relay names only its own successor. The monotonically shrinking payload —
1857 → 749 → 120 bytes — is the layers being peeled one per hop. The exit relay
logs `DESTINATION`, not the destination hostname.

**Log hygiene under Docker.** All 40 lines of `docker compose logs` scanned: zero
occurrences of `PRIVATE KEY`, `BEGIN PUBLIC KEY`, `session_key`, `nonce`,
`ciphertext`, `phase1sandbox`, `onion.mock`, or the page marker. The containerized
run leaks nothing the loopback tests already forbade.

---

## Ready for next phase: YES

Every criterion in `RELAY_PROTOCOL.md` §11, `DIRECTORY_SPEC.md` §5 and
`IMPLEMENTATION_PLAN.md` §3 passes under observation, on loopback and in
containers. Nothing in Phase 1 is unverified.

Two things still want a human decision, neither blocking this gate:

- **OPEN-9** — the error envelope. SD-011 is approved in principle; the wire form
  of an error is undecided, and the current build deviates from
  `RELAY_PROTOCOL.md` §9's fourth bullet. Needs a ruling before Phase 6 hardening.
- **OPEN-1 / OPEN-2** — the seed-data conflicts, which will stall Phase 4 the
  moment it starts.
