# SPEC_DECISIONS.md

**Repo:** `darkweb-sandbox`
**Status:** Phase 0 — specification blocker resolution
**Created:** 2026-09-07

---

## 0. What this document is

The audit of this repository found that the existing specifications leave several
engineering questions undefined or self-contradictory, and that Phase 1 could not be
implemented without answering them.

This file records those answers. It is **subordinate to the existing specifications**:
every decision below is derived from what `AgentsDocs/` already says, choosing the
smallest option compatible with all of it. Where a decision narrows a range the specs
left open, the rationale names the documents that constrained the choice.

Nothing here rewrites an existing document. Where a decision affects one, the
"Affected documents" field names it so a human can fold the decision back in later if
they want to.

**Reading order:** `MASTER_CONTEXT.md` -> `IMPLEMENTATION_PLAN.md` -> `RELAY_PROTOCOL.md`
-> this file.

---

## SD-000 — Phase 1 scope

**Question:**
`AgentsDocs/IMPLEMENTATION_PLAN.md` §3 defines Phase 1 as a *single hardcoded hop* and
explicitly says "Do not build: the directory, multiple relays, path selection". But
`AgentsDocs/RELAY_PROTOCOL.md` §11 criterion 1 — the acceptance test Phase 1 delegates
to — requires the relay to register its public key **with the directory**. Phase 1 as
written cannot both omit the directory and demonstrate registration with it.

**Chosen decision:**
Phase 1 is implemented as **relay pool + directory + multi-hop path**, covering what
`AgentsDocs/IMPLEMENTATION_PLAN.md` calls Phases 1, 2 and 3.

This is **a human product decision, not an inference.** It was given as an explicit
instruction by the repository owner, who defined Phase 1 as "RELAY + DIRECTORY" with
required capabilities including "directory", "relay discovery", "layered encrypted
request forwarding" and a path length of "2-5 hops". It is recorded here because it
changes what the phase gate means.

**Rationale:**
It is the only reading that lets `RELAY_PROTOCOL.md` §11 criterion 1 pass, and it
resolves the contradiction in the direction the acceptance criteria already point.

**Affected documents:**
- `AgentsDocs/IMPLEMENTATION_PLAN.md` §3 (Phase 1 "Do not build" list; Phases 2 and 3)
- `README.md` §7 (phase checklist)

**Implementation consequence:**
The Phase 1 deliverable set is `common/`, `directory/`, `relay/`, `client/`, a static
Phase-1 endpoint, `docker-compose.yml`, and tests. The acceptance criteria satisfied
are `RELAY_PROTOCOL.md` §11 (all six), `DIRECTORY_SPEC.md` §5 (all seven), and
`IMPLEMENTATION_PLAN.md` §3 Phase 3 (all six). Phases 4, 5 and 6 remain untouched.

---

## SD-001 — Relay transport

**Question:**
How do client -> relay and relay -> relay messages travel? `AgentsDocs/RELAY_PROTOCOL.md`
§6 calls `forward(layer.next_host, layer.next_port, ...)` and
`http_request(layer.next_host, layer.next_port, ...)` without defining either.

**Chosen decision:**
**HTTP/1.1 over TCP, one `POST /relay` per hop.** The request body is the wire layer
of `RELAY_PROTOCOL.md` §5.2 as `application/json`. The HTTP response body is the
sealed response envelope (SD-002). Each hop is a synchronous, blocking
request/response.

The exit relay is the exception: its `payload` is `base64(raw_http_request)` per
§5.1, so it opens a plain TCP socket to `next_host:next_port`, writes those bytes
verbatim, and reads the raw HTTP response bytes back. It does not parse or re-issue
the request.

**Rationale:**
HTTP is already the ambient transport of this system and is not a new choice: the
directory serves four HTTP endpoints (`DIRECTORY_SPEC.md` §3), `README.md` §8
demonstrates it with `curl`, and §6's exit branch is named `http_request`. Using the
same transport for relay hops adds nothing new to the architecture.

Synchronous request/response is what §7 already describes — "returns it to B", "returns
it to A", "returns to the client" is a return path that unwinds the forward path in
reverse, which is exactly the shape of nested blocking calls.

The exit relay treating `payload` as opaque bytes on a raw socket is the literal
reading of "`payload`: base64 ... of the raw request if exit" (§5.1) and keeps the
relay free of any knowledge of the request's structure.

**Affected documents:**
- `AgentsDocs/RELAY_PROTOCOL.md` §6 (defines `forward` and `http_request`)

**Implementation consequence:**
Every relay exposes `POST /relay`. `relay/relay_node.py` forwards with
`urllib.request` and exits with `socket`. The client sends only to the entry relay's
`POST /relay`, per §5.3. Hop timeouts are bounded (SD-011) so no hop can hang.

**Amended 2026-09-07 by SD-024 (narrowed, not reversed).** The transport is
unchanged: still HTTP/1.1, still one `POST /relay` per hop, still synchronous. What
is retired is this decision's use of **non-2xx as the client's protocol failure
signal**. Under `RELAY_PROTOCOL.md` §9.3 a relay answers **HTTP 200** whenever it can
seal a response envelope, whether the sealed content is a `success` or an `error`, and
non-2xx survives only where a relay cannot seal at all. The client reads the sealed
`type`, never the status code.

---

## SD-002 — Response wire envelope

**Question:**
`RELAY_PROTOCOL.md` §5.2 defines the forward wire format as
`{enc_key, nonce, ciphertext}`. The return leg reuses the retained `K`, so no
`enc_key` is needed — but §6's `encrypt_response(response, K, fresh_nonce)` never
defines what it produces, and the fresh nonce must still reach the client.

**Chosen decision:**
The response envelope is the forward envelope **minus `enc_key`**:

```json
{ "nonce": "<base64 of the fresh 96-bit nonce>",
  "ciphertext": "<base64 of AES-GCM(K, nonce, inner_bytes)>" }
```

It nests exactly like the forward direction: the exit relay seals the site's raw
response bytes; each upstream relay seals **the JSON bytes of the envelope it received**
with its own `K` and a fresh nonce. The client unseals with its keys in path order
A -> B -> C, and what falls out of the innermost envelope is the raw HTTP response.

> **Two sentences above became false on 2026-09-07 and are corrected by SD-024.** The
> **wire shape is unchanged** -- `{nonce, ciphertext}` still, in both directions -- so
> the decision itself stands. What changed is what gets sealed:
>
> 1. *"what falls out of the innermost envelope is the raw HTTP response"* -- it is now
>    a **typed object** carrying it: `{"type": "success", "body": "<b64>"}`, or an
>    `error`, per `RELAY_PROTOCOL.md` §7.
> 2. *"each upstream relay seals the JSON bytes of the envelope it received"* -- it now
>    seals a `relay` wrapper holding **base64 of** those bytes:
>    `{"type": "relay", "inner": "<b64>"}`.
>
> The base64 indirection exists so that no intermediate relay has to parse relayed
> content to know what to do with it. The property this decision's last line asserts --
> *"a relay never inspects what it is sealing"* -- is preserved, and is in fact the
> reason for the change.

**Rationale:**
Derived directly from §5.2 by removing the one field the return leg cannot use: `K`
is already held by both sides, so RSA key delivery does not repeat. Keeping the
remaining two fields identical in name, encoding and base64 treatment means one
envelope codec serves both directions.

The nesting order is fixed by §7: "the response travels back along the same path,
**gaining a layer at each hop**", and "Client decrypts in order A -> B -> C". Sealing
the received envelope's bytes is what "gaining a layer" means.

**Affected documents:**
- `AgentsDocs/RELAY_PROTOCOL.md` §6, §7

**Implementation consequence:**
`common/onion_crypto.py` provides `seal_response` / `open_response` alongside
`seal_layer` / `open_layer`. A relay never inspects what it is sealing — to an
intermediate relay the inner envelope is opaque bytes.

---

## SD-003 — `request_id`

**Question:**
`RELAY_PROTOCOL.md` §6 says `remember (request_id -> K, nonce)` and §8's mandatory log
format prints `request_id=a7f3`. But the plaintext layer (§5.1) has exactly four
fields and the wire layer (§5.2) exactly three. Neither carries a `request_id`.

**Chosen decision:**
`request_id` is **relay-local**. Each relay generates a fresh 4-hex-character id when
it receives a layer, uses it for that relay's own log lines, and discards it when the
response is returned. It is **not** carried on the wire and **not** shared between
hops. The same request therefore appears under a different `request_id` in each
relay's log.

**Rationale:**
Three constraints force this.

1. §5.1 states "Every layer, before encryption, **is this JSON object**" and lists
   four fields. Adding a fifth would change an authoritative wire format.
2. A client-generated id carried to every hop would be a single value visible to all
   relays, linking their views of one request. §1 states the isolation property is
   "the entire point" and that any choice serving it less is wrong. A shared
   correlator is exactly the kind of cross-hop linkage the design excludes.
3. With synchronous transport (SD-001), `K` lives on the handling call stack for the
   duration of the request. The `remember (request_id -> K)` map is not needed to
   route the response back; §7's requirement that keys be retained "for the duration
   of that request only" is satisfied more strictly by a local variable than by a map.

**Affected documents:**
- `AgentsDocs/RELAY_PROTOCOL.md` §6, §8
- `format/DEMO_SCRIPT.md` §3 — see consequence

**Implementation consequence:**
§8's log format is reproduced verbatim, including `request_id=`. `K` is held in a
local variable and explicitly deleted after the response is sealed.

**Known consequence for the demo:** a presenter cannot grep one `request_id` across
three relay logs to trace a single request. The demo beat in `format/DEMO_SCRIPT.md`
§3 does not actually require this — it points at the volume and ordering of log lines
("each relay logs one hop") rather than at a shared id — but anyone planning to trace
an id across panes should know it is deliberately not possible. `DIRECTORY_SPEC.md`
§3's `path_id` remains available for correlating a client run with a directory log
line.

---

## SD-004 — Directory ownership and implementation

**Question:**
Who builds the directory, where does it live, and what backs it?

**Chosen decision:**
`directory/directory_service.py`, owned by Claude Code, in-memory only, serving the
four endpoints of `DIRECTORY_SPEC.md` §3 exactly as specified. No database, no disk,
no persistence.

**Rationale:**
Not genuinely open — `format/AGENT_TASK_SPLIT.md` §1 assigns `directory/` to Claude
Code, `IMPLEMENTATION_PLAN.md` §3 Phase 2 names the file, and `DIRECTORY_SPEC.md` §2
fixes the state shape and forbids persistence. Recorded only because SD-000 moves it
into Phase 1.

**Affected documents:** none — this is the specification as written.

**Implementation consequence:**
State is a `dict` guarded by a lock. `POST /register` rejects any payload containing
`PRIVATE KEY` or a value that does not parse as a PEM public key. Directory logs
carry `path_id` and hop count only, never path composition, per §4.

---

## SD-005 — HTTP framework and dependencies

**Question:**
The relay and directory must both serve HTTP. `README.md` §8 lists only
`cryptography`, `requests` and `beautifulsoup4` — none of which is a server.
`AgentsDocs/MASTER_CONTEXT.md` §5 rule 5 forbids adding an unlisted dependency without
flagging it first.

**Chosen decision:**
**No web framework.** The directory, the relays and the Phase-1 endpoint are built on
the standard library's `http.server.ThreadingHTTPServer`. The client uses
`urllib.request` and `socket`. The only third-party dependency in Phase 1 is
**`cryptography`**.

**Rationale:**
Rule 5 exists to stop unlisted dependencies appearing silently. The way to honour it
is to need none: the standard library covers every Phase-1 requirement, so nothing has
to be flagged and nothing has to be justified.

`cryptography` is not a new dependency — `RELAY_PROTOCOL.md` §2 mandates it by name
("Use the Python `cryptography` library"), as do `MASTER_CONTEXT.md` §5 rule 2 and
`README.md` §8.

`requests` and `beautifulsoup4` are listed in `README.md` §8 but are Phase-5 scraper
needs. They are deliberately **not** installed in Phase 1.

Tests use `unittest` from the standard library rather than `pytest`, for the same
reason.

**Affected documents:**
- `README.md` §8 (prerequisites)

**Implementation consequence:**
`requirements.txt` pins `cryptography` alone. The `python:3.11-slim` base image plus
that one wheel is the whole runtime. `http.server` is single-purpose and unsuitable
for production traffic, which is correct here — this is a demonstration environment,
`MASTER_CONTEXT.md` §4 makes no availability or performance claim, and a framework
would add surface without adding a demonstrated property.

---

## SD-006 — Ports

**Question:**
`DIRECTORY_SPEC.md` never states what port the directory listens on, and the relay
port convention appears only inside an example.

**Chosen decision:**

| Component | Port | Host-published |
|---|---|---|
| directory | `8000` | yes, `8000` |
| `relay-NN` | `90NN` (relay-01 -> 9001 ... relay-07 -> 9007) | no |
| Phase-1 static endpoint | `80` | no |

**Rationale:**
Both values are already implied by the documents rather than free.
`README.md` §8's quickstart reads `curl http://localhost:8000/relays` and
`curl "http://localhost:8000/path?hops=3"`, which fixes the directory at 8000.
`DIRECTORY_SPEC.md` §3's registration example is
`{"relay_id": "relay-03", "host": "relay-03", "port": 9003, ...}`, which fixes the
`90NN` convention. Port 80 for the endpoint matches the site port that
`format/AGENT_TASK_SPLIT.md` §3 mandates for Phase-4 sites, so the exit relay's
behaviour does not change when the real sites arrive.

Only the directory is published to the host, because `README.md` §8 requires reaching
it with `curl`. Relays and the endpoint are unpublished, consistent with
`MOCK_SITES_SPEC.md` §3's "reachable only through the relay chain" property.

**Affected documents:**
- `AgentsDocs/DIRECTORY_SPEC.md` §3
- `README.md` §8

**Implementation consequence:**
Ports are read from environment variables with these values as defaults, so tests can
bind ephemeral ports on `127.0.0.1` without special-casing.

---

## SD-007 — `.onion.mock` address resolution

**Question:**
`SCRAPER_AGENT_SPEC.md` §2 has the caller pass `alpha7fq2mx9k.onion.mock` to
`onion_client`, but `RELAY_PROTOCOL.md` §5.3's innermost layer sets
`next_host: "forum-alpha"` — a container name. `MOCK_SITES_SPEC.md` §6 gives the
mapping table but never says who applies it.

**Chosen decision:**
**The client resolves the address, before building the innermost layer.** The
`.onion.mock` name never reaches any relay. The innermost layer carries the container
name in `next_host`, exactly as §5.3 shows. The client writes the `.onion.mock` name
into the raw HTTP request's `Host:` header, so the destination still sees the mock
address it is addressed by.

**Rationale:**
§5.3 is explicit that `next_host` is `"forum-alpha"`, so by the time the innermost
layer exists the translation has already happened, and the only component upstream of
it is the client. Putting the table in the client also keeps relays free of any
knowledge of what sites exist — a relay resolving `.onion.mock` would need the site
list, which is knowledge §6's visibility table does not grant it.

The mapping table itself is copied verbatim from `MOCK_SITES_SPEC.md` §6 and is data,
not new architecture. There is no descriptor lookup and no DHT, per the scope lock.

**Affected documents:**
- `AgentsDocs/RELAY_PROTOCOL.md` §5.3
- `AgentsDocs/MOCK_SITES_SPEC.md` §6
- `AgentsDocs/SCRAPER_AGENT_SPEC.md` §2

**Implementation consequence:**
`client/onion_client.py` holds `MOCK_ADDRESS_MAP`. It contains the three addresses
from `MOCK_SITES_SPEC.md` §6 plus the Phase-1 endpoint (SD-012). The three Phase-4
entries are inert until those containers exist; resolving one before then raises a
named error rather than failing obscurely. `OnionClient.get(path, host, resource)`
matches the call signature `SCRAPER_AGENT_SPEC.md` §2 already specifies, so Phase 5
needs no client change.

---

## SD-008 — Shared cryptographic module

**Question:**
The client seals layers and the relays open them. `format/AGENT_TASK_SPLIT.md` §1
lists `relay/`, `client/`, `directory/` and `scraper/` but no shared location.

**Chosen decision:**
One module, `common/onion_crypto.py`, imported by both. Plus `common/http_util.py`
for a small JSON-over-HTTP request/response helper.

**Rationale:**
`MASTER_CONTEXT.md` §5 rule 2 and `RELAY_PROTOCOL.md` §2 forbid hand-rolled
cryptography, and the deeper risk is not a bad primitive but two copies of the
envelope logic drifting apart — a client and a relay that disagree by one base64 layer
fail in a way that looks like a crypto bug. A single codec makes that class of bug
impossible.

`common/` sits entirely within Claude Code's ownership (all cryptographic code is
Claude Code's per `AGENT_TASK_SPLIT.md` §2) and is not a new architectural component:
it holds no state, serves no port, and makes no decisions.

**Affected documents:**
- `format/AGENT_TASK_SPLIT.md` §1 (ownership table gains `common/`, Claude Code)

**Implementation consequence:**
`common/onion_crypto.py` is the only file that calls the `cryptography` package.

---

## SD-009 — Relay pool size

**Question:**
`MASTER_CONTEXT.md` §3 and §7 say "5-7 relays". `README.md` §1's diagram says
"Relay Pool (7 Nodes)". `format/DEMO_SCRIPT.md` §3 scripts the presenter saying
"Seven relay nodes" and "seven nodes, all up".

**Chosen decision:**
**Seven**, `relay-01` ... `relay-07`.

**Rationale:**
Seven is the single value inside the specification's own 5-7 range that also makes
`format/DEMO_SCRIPT.md`'s spoken line literally true. `MASTER_CONTEXT.md` §4 exists to
prevent claims the system does not support; choosing the value that keeps the scripted
claim accurate serves that directly. It also leaves headroom above the `hops=5`
maximum of `RELAY_PROTOCOL.md` §4, so path selection is still a real choice at maximum
hop count rather than a forced permutation.

**Affected documents:**
- `AgentsDocs/MASTER_CONTEXT.md` §3, §7
- `README.md` §1, §3.1
- `format/DEMO_SCRIPT.md` §3

**Implementation consequence:**
`docker-compose.yml` declares seven relay services on ports 9001-9007.

---

## SD-010 — The `sandbox-net` network

**Question:**
`format/AGENT_TASK_SPLIT.md` §3 describes `sandbox-net` as
"(external, created by root compose)". In Docker Compose those are mutually exclusive:
a network marked `external: true` must already exist and is explicitly not created by
that file.

**Chosen decision:**
Root `docker-compose.yml` declares `sandbox-net` as an ordinary named network with an
explicit `name: sandbox-net`, so Compose creates it under that exact name. The
Phase-4 `mock-sites/docker-compose.sites.yml` — not written here — references it as
`external: true`.

**Rationale:**
This is the reading under which both halves of the sentence are true at once:
the network is created by root compose, and it is external *from the sites file's
point of view*. Every shared constraint in the §3 table is preserved — the name, the
container names, port 80, and no host port mapping. It also keeps the documented
invocation working unchanged:
`docker compose -f docker-compose.yml -f mock-sites/docker-compose.sites.yml up`.

**Affected documents:**
- `format/AGENT_TASK_SPLIT.md` §3

**Implementation consequence:**
Root compose sets `networks: sandbox-net: {name: sandbox-net}`. The explicit `name:`
prevents Compose from prefixing the project name, which would otherwise break the
sites file's external reference.

---

## SD-011 — Failure propagation and timeouts

**Question:**
`RELAY_PROTOCOL.md` §9 requires that an unreachable relay produce "a clear error
naming the failed hop", and `IMPLEMENTATION_PLAN.md` §3 Phase 3 criterion 6 requires
"a clear named error, no hang". But §6's visibility table forbids a relay learning
hops other than its own — and an error that names a downstream relay, propagated
upstream, would tell relay A about relay C.

**Chosen decision:**
An error is a protocol response that preserves the same relay-visibility invariant as
a successful one. Each relay **rewrites `reported_by` to its own `relay_id`** before
propagating an error upstream, and **never forwards a downstream relay's identity**.

The failed hop is named **in the detecting relay's own log**, where §8 already permits
naming the next hop. The client receives an error naming the last relay it
successfully reached as the point from which the path broke, and raises
`OnionPathError`.

The wire form of that response — sealed under the return-path layers, or a plaintext
status — is **not decided here**; see "Scope of this decision" below and OPEN-9.

Every hop is bounded by a timeout (default 10s, `HOP_TIMEOUT` env), so no failure can
hang.

**Rationale:**
The two requirements pull against each other and the visibility property wins, because
§1 says so explicitly: "That property is the entire point. Every design decision below
serves it." Naming the failed hop end-to-end would satisfy the wording of §9 while
breaking the invariant §1 calls the point of the system.

The requirement is still met in substance: the error is clear, it is named, it is
immediate, and the specific broken link is one `docker compose logs relay-NN` away —
in the same log pane the demo already has open.

**This is the one decision in this document that resolves a genuine tension rather
than an omission.** It is flagged for human review.

**Scope of this decision:**
SD-011 decides **what an error may say**, not **how it is carried**. The invariant is
about relay identity only:

- a relay never reveals a downstream relay's identity to its predecessor or to the client
- a relay may identify itself as the reporter
- the client may therefore learn the last relay it successfully reached, and never the
  identity of a failed relay further down the path

That invariant must hold under any transport form the error takes. Whether an error
travels sealed under the return-path layers or as a plaintext status is a **protocol
question that `RELAY_PROTOCOL.md` does not settle**, and it is deliberately not
settled here — see OPEN-9.

**Affected documents:**
- `AgentsDocs/RELAY_PROTOCOL.md` §9
- `AgentsDocs/IMPLEMENTATION_PLAN.md` §3 (Phase 3, criterion 6)

**Implementation consequence:**
An error carries `{"error": "<code>", "reported_by": "<own relay_id>"}`, where
`reported_by` is always the emitting relay's own id and never a downstream one. This
is the part SD-011 fixes, and it holds whatever envelope the error ends up in.

The **transport form is not decided by SD-011.** The current Phase-1 build returns
errors as plaintext JSON with a non-2xx HTTP status at every hop. That is an
implementation default adopted to get Phase 1 running, not a protocol ruling, and it
is a **known deviation** for one of the four cases in §9:

> "Mock site unreachable → exit relay returns an error response **through the normal
> return path**"

The normal return path is the layered, sealed one of §7, so that bullet implies a
sealed error for the destination-unreachable case specifically. The current build
returns plaintext there instead. The other three bullets in §9 say only "return an
error" and do not constrain the form.

This deviation is recorded, not resolved. Fixing it is a protocol decision for a
human, tracked as **OPEN-9**, and Phase 1's acceptance is unaffected either way —
`IMPLEMENTATION_PLAN.md` Phase 3 criterion 6 asks for "a clear named error, no hang",
which both forms satisfy.

---

## SD-012 — The Phase-1 static endpoint

**Question:**
`IMPLEMENTATION_PLAN.md` §3 Phase 1 requires "One trivial mock endpoint (a static page
is fine — the real sites come in Phase 4)" but gives it no path, port or address. It
cannot live in `mock-sites/`, which `format/AGENT_TASK_SPLIT.md` §2 forbids Claude
Code from touching.

**Chosen decision:**
`phase1_endpoint/static_endpoint.py`, serving one hardcoded page on port 80, addressed
as **`phase1sandbox.onion.mock`**.

It is **not a mock site.** It carries no persona, no handle, no PGP block and no
wallet address. It exists only to prove a request reached the far end of the chain and
came back.

**Rationale:**
A separate top-level directory keeps the ownership boundary in `AGENT_TASK_SPLIT.md`
§2 intact — nothing here is inside `mock-sites/`, so the Phase-4 agent's tree is
untouched.

The `.onion.mock` suffix is mandatory: `MOCK_SITES_SPEC.md` §6 states these addresses
"must never be presentable" as real onion addresses, and that applies to every mock
address in the repository, not only the three Phase-4 ones.

Keeping it free of seed data is deliberate. `DATA_MODEL.md` §4's values are the demo's
ground truth and `MOCK_SITES_SPEC.md` §2 rule 5 requires them character-exact in the
real sites; a second, throwaway copy in a Phase-1 fixture is exactly how a
character-level drift gets introduced.

**Affected documents:**
- `AgentsDocs/IMPLEMENTATION_PLAN.md` §3 (Phase 1 deliverables)
- `AgentsDocs/MOCK_SITES_SPEC.md` §6 (address table gains a Phase-1-only entry)

**Implementation consequence:**
Declared in root `docker-compose.yml` with no host port mapping. **It is deleted at
Phase 4**, when the three real sites replace it. Its compose service and its entry in
`MOCK_ADDRESS_MAP` are both marked with that removal note in-code.

---

## SD-013 — Phase report directory name

**Question:**
Eleven references across `MASTER_CONTEXT.md`, `IMPLEMENTATION_PLAN.md`,
`API_CONTRACT.md`, `format/MASTER_PROMPT.md` and `format/AGENT_TASK_SPLIT.md` point at
`Agent_Docs/`. The directory on disk is `AgentsDocs/`, which is also what
`README.md` §6 uses.

**Chosen decision:**
`AgentsDocs/` is correct. Phase reports go to **`AgentsDocs/reports/PHASE_<n>_REPORT.md`**.

**Rationale:**
The filesystem and `README.md` §6 agree; the `Agent_Docs/` references are a stale
name. No document is edited to match — the existing docs are left as they are, and
this entry records the mapping.

**Affected documents:**
- `AgentsDocs/MASTER_CONTEXT.md` §1, §2
- `AgentsDocs/IMPLEMENTATION_PLAN.md` §4
- `AgentsDocs/API_CONTRACT.md` (header)
- `format/MASTER_PROMPT.md` (throughout)
- `format/AGENT_TASK_SPLIT.md` §1, §2, §5, §7

**Implementation consequence:**
Anyone pasting `format/MASTER_PROMPT.md` verbatim will point an agent at a directory
that does not exist. That prompt is human-owned and is not edited here; flagged for
the owner.

---

## SD-014 — Data-model authority boundary

**Resolves:** OPEN-1. **Kind:** Human product decision, 2026-09-07.

**Question:** `AgentsDocs/DATA_MODEL.md` declares `Repo: GOTHAMITE` in its own
header while every other document cites "GOTHAMITE `docs/DATA_MODEL.md`" as a file
in a *different* repository. Is the local copy authoritative, a synchronised
mirror, or stale?

**Chosen decision:** Neither wholly. The two files govern **different things**, and
the header wording was the ambiguity, not the content:

| File | Authoritative for |
|---|---|
| `darkweb-sandbox/AgentsDocs/DATA_MODEL.md` | The sandbox's **simulated ground truth** — seed personas, seed identifiers, seed artifacts, and the sandbox data model |
| GOTHAMITE `docs/DATA_MODEL.md` | GOTHAMITE's **internal intelligence / ingestion representation** |

The two must remain compatible **at the API boundary**, which is
`AgentsDocs/API_CONTRACT.md`. Neither repository owns the other's model.

**Rationale:** The audit read `Repo: GOTHAMITE` as a claim of provenance — that
this file was a copy of a GOTHAMITE-owned document — which is what made its
authority unknowable from inside this repository. It is not that claim. The file
is a `darkweb-sandbox` document describing what this sandbox fabricates, and its
own authority line ("single source of truth for the schema and the seed data") is
correct **within that scope**. The conflict existed because one header line
conflated two different data models that happen to share a filename.

**Explicitly not decided:** this repository does **not** own, define, or restate
GOTHAMITE's internal data model. No GOTHAMITE model is to be invented or rewritten
here.

**Affected documents:** `AgentsDocs/DATA_MODEL.md` header clarified.
`AgentsDocs/API_CONTRACT.md:4` is unaffected — it already defers to the GOTHAMITE
file for the *ingestion representation*, which is exactly the scope SD-014 leaves
with GOTHAMITE.

**Implementation consequence:** Phase 4 seeds mock sites from
`AgentsDocs/DATA_MODEL.md` §4 with no external lookup required. Phase 5 emits in
`API_CONTRACT.md` shape. A future divergence in GOTHAMITE's model is an
API-boundary change, not a reseed.

---

## SD-015 — Canonical A1/A2 wallet

**Resolves:** OPEN-2. **Kind:** Human product decision, 2026-09-07.

**Question:** `README.md` §4 gave persona A1's wallet as a bech32 address while
`DATA_MODEL.md` §4, `API_CONTRACT.md` §3 and `MOCK_SITES_SPEC.md` §2 gave a base58
address for the same persona.

**Chosen decision:** The canonical A1/A2 wallet is

```
1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6
```

base58, 34 characters, leading `1`. **No bech32 support.** **No mixed-format
extractor.** The `SCRAPER_AGENT_SPEC.md` §4 regex
`[13][a-km-zA-HJ-NP-Z1-9]{25,34}` and its validation rules (length in range,
no `0`/`O`/`I`/`l`, not a substring of a longer alphanumeric run) remain
authoritative and unchanged.

The value must stay **character-for-character identical** across
`AgentsDocs/DATA_MODEL.md`, `AgentsDocs/API_CONTRACT.md`,
`AgentsDocs/MOCK_SITES_SPEC.md`, `README.md`, and the seeded mock content.

**Rationale — why the conflict existed, preserved:** the bech32 value appeared in
exactly one place, `README.md` §4's illustrative ingestion payload, against the
base58 value in three specification documents plus the regex that
`SCRAPER_AGENT_SPEC.md:74` describes as "the base58 pattern used in the seed data".
README §4 is illustrative and claims no authority over seed data; it was stale.
The conflict mattered because the regex is **structurally incapable** of matching
bech32 — `[13]` rejects `bc1q` at the first character, and 42 characters exceeds
the 25–34 bound — so a spec-conformant scraper crawling README-seeded sites would
have extracted zero wallets and emitted `identifiers: []`, which
`SCRAPER_AGENT_SPEC.md:114` classifies as "Normal". The failure would have been
silent, degrading the headline A1↔A2 link from 0.95 to 0.70 with no error raised.

**Affected documents:** `README.md` §4 corrected. `DATA_MODEL.md`,
`API_CONTRACT.md` and `MOCK_SITES_SPEC.md` already carried the canonical value and
are unchanged.

**Implementation consequence:** the Phase-5 wallet extractor is single-format.
`MOCK_SITES_SPEC.md:113`'s "character for character" rule now has an unambiguous
referent. All eight seed wallets (A1/A2, B1/B2, C1, D1) are base58 and match the
existing regex — verified by running it against each value.

---

## SD-016 - Number of decoy personas

**Resolves:** OPEN-3. **Kind:** Resolved from the existing specification.

**Question:** `IMPLEMENTATION_PLAN.md` §3 Phase 4 acceptance 4 requires "decoy
person**as**" (plural); `DATA_MODEL.md` §4 specifies exactly one, C1 `nightjarr`.

**Chosen decision:** Exactly one decoy persona, C1, as `DATA_MODEL.md` §4
specifies. No additional decoys invented.

**Rationale - resolvable without a product decision.** SD-014 makes
`DATA_MODEL.md` authoritative for seed data, and its own authority line says
documents that disagree with it lose. Three further rules point the same way:
`MOCK_SITES_SPEC.md` §2 rule 3 forbids generated content, rule 5 requires values
exactly as written in `DATA_MODEL.md` §4, and `DATA_MODEL.md` §4's expected-output
table enumerates four links with C1 as the single rejected one. Inventing a second
decoy would add a persona with no defined handle, window, key or wallet, and no
row in that table - the demo could not state what the correct result was. The
plural in the plan is loose phrasing about a category, not a count.

**Affected documents:** none rewritten. `IMPLEMENTATION_PLAN.md`'s wording is left
as it is; this entry records how it is read.

**Implementation consequence:** `mock_sites/seed_data.py` carries six personas,
one of them C1. The decoy's job is done by handle similarity plus overlapping
activity, both asserted in `tests/test_phase4.py`.

---

## SD-017 - Mock-site timestamp timezone

**Resolves:** OPEN-7. **Kind:** Resolved from the existing specification.

**Question:** `MOCK_SITES_SPEC.md` §4 says post timestamps are "ISO 8601" without
naming a timezone; `DATA_MODEL.md` §4 gives active windows as bare dates.

**Chosen decision:** All post timestamps are **ISO 8601, UTC, `Z` suffix** -
`2026-03-11T09:14:00Z`. Active-window dates stay bare dates, as written.

**Rationale - resolvable without a product decision.** `API_CONTRACT.md` §3 already
fixes the format for the field these timestamps become: `collected_at` is
specified as "ISO 8601, UTC, `Z` suffix", and `persona.observed_at` - which the
same table defines as "the post's own timestamp" - carries a `Z` suffix in every
example in that document and in `README.md` §4. A mock site emitting a local or
offset-bearing timestamp would force the scraper to convert, and `API_CONTRACT.md`
§4 warns that `observed_at` feeds GOTHAMITE's temporal succession scoring - the
signal that catches the B1 to B2 rebrand. Anything but UTC would put a conversion
step in front of the one field the demo depends on.

**Affected documents:** none rewritten.

**Implementation consequence:** every `observed_at` in `mock_sites/seed_data.py`
ends in `Z`; pages render the string verbatim so the scraper can pass it through.

---

## SD-018 - B1's last post and B2's first post

**Kind:** Reconciled a contradiction between two specifications.

**Question:** `MOCK_SITES_SPEC.md` §5 requires B1's last post "strictly before
`2026-04-02`" and B2's first "strictly after `2026-04-19`". `DATA_MODEL.md` §4
gives B1's active window as ending **`2026-04-02`** and B2's as starting
**`2026-04-19`**, and annotates the pair "(17-day gap)".

**Chosen decision:** B1's last post is `2026-04-02T11:26:00Z`; B2's first is
`2026-04-19T10:12:00Z`. The gap is 17 days, matching `DATA_MODEL.md`.

**Rationale.** The two cannot both be satisfied. Reading §5 strictly forces B1 to
`2026-04-01` or earlier and B2 to `2026-04-20` or later - a gap of at least 19
days, against a data model that states 17 and an acceptance criterion
(`MOCK_SITES_SPEC.md` §7 item 6) that asks for "roughly 17 days".
`DATA_MODEL.md`'s authority line names `MOCK_SITES_SPEC.md` explicitly and says
that where they disagree, the data model wins; SD-014 reaffirmed that for seed
data. The gap is also a scoring input rather than decoration: `DATA_MODEL.md` §4
derives B1 to B2's expected 0.60 from "wallet 0.45 + temporal succession 0.15
(17-day gap)", so moving the dates to satisfy §5 would change the number the demo
claims.

Read against the active windows, §5's intent still holds: B1 posts nowhere after
its window ends, and B2 nowhere before its window begins.

**Affected documents:** `MOCK_SITES_SPEC.md` §5's two bullets are inconsistent
with `DATA_MODEL.md` §4 as written. Not rewritten here - flagged for whoever next
edits that file.

**Implementation consequence:** `tests/test_phase4.py` asserts the gap is 17 days
plus or minus 1, and that the two windows do not overlap.

---

## SD-019 - Mock sites emit no `Date` header

**Kind:** Filled a documented gap, and closes a finding from the Phase-1 report.

**Question:** `MOCK_SITES_SPEC.md` §7 item 7 requires content "stable across
restarts - identical bytes every time". A stdlib HTTP server stamps a `Date`
header, so two responses a second apart differ even when the page is identical.
Does the criterion mean the page, or the whole response?

**Chosen decision:** the mock sites send no `Date` header, which makes the
criterion true of the **whole response**, not only the page body.

**Rationale.** The Phase-1 report already recorded this ambiguity as a finding -
it first surfaced as `phase1_demo` reporting two identical pages as different.
Rather than narrow the criterion to "the page", the sites are made genuinely
deterministic, which is the stronger reading and the one the words support. There
is no cost: every byte these sites serve is hardcoded, so there is nothing a
`Date` header could be right about, and nothing downstream caches on it. This also
settles what Phase 5's `content_hash` over `raw_content` covers - for these sites
the full response is stable, so either reading yields the same hash.

**Scope:** the mock sites only. Relays, directory and the Phase-1 endpoint are
unchanged; `RELAY_PROTOCOL.md` does not constrain destination response headers.

**Implementation consequence:** `mock_sites/site_server.py` overrides
`send_response` to emit the status line and `Server` header only.
`tests/test_phase4.py` asserts byte-identical responses across a full server
restart, and asserts no `Date:` is present.

---

## SD-020 - `mock_sites/` rather than `mock-sites/`

**Kind:** Corrected an unusable path.

**Question:** `IMPLEMENTATION_PLAN.md` §3 Phase 4 names the deliverables
`mock-sites/forum-alpha/`, `mock-sites/marketplace-beta/` and
`mock-sites/forum-gamma/`, and the root compose file pointed at
`mock-sites/docker-compose.sites.yml`.

**Chosen decision:** the directory is `mock_sites/` (underscore), holding one
package: `seed_data.py`, `site_server.py` and `docker-compose.sites.yml`. Site
identity comes from `SITE_ID` at runtime rather than from three directories.

**Rationale.** A hyphen cannot appear in a Python package name, so `mock-sites/`
cannot be imported and cannot be launched with `python -m`, which is how every
other service in this repository starts (SD-005, and every `command:` in
`docker-compose.yml`). Three per-site directories would also mean three copies of
an identical server differing only in content - three chances for the content to
drift apart, against a specification whose central rule is that the values match
`DATA_MODEL.md` character for character. Same class of decision as SD-013.

**Affected documents:** `README.md` repository layout, and the root
`docker-compose.yml` comment pointing at the sites file, which was updated to the
real path. `IMPLEMENTATION_PLAN.md`'s deliverable path is left as written.

---

## SD-021 - Artifact `page_type` discriminator -- **IN FORCE**

> **STATUS: IN FORCE.** Adopted at the contract freeze of 2026-09-07. The
> specification amendments this decision called for have been **applied** to the
> documents named below. This entry is now a record of a decision that governs, not a
> proposal awaiting one.
>
> **Adoption is not counterparty agreement.** No GOTHAMITE repository exists to have
> agreed to anything; the recorded architecture is to finalise the contract first and
> implement GOTHAMITE against it. Absence of objection is not assent, and this file
> makes no claim that implementation compatibility has been established.

**Relates to:** OPEN-4. **Kind:** Proposed human product decision, 2026-09-07.
**Blocks:** Phase 5.

### Project-state clarification (recorded 2026-09-07)

**There is currently no GOTHAMITE implementation available for compatibility
review.** A review was attempted and could not be performed: no GOTHAMITE
repository is present in this workspace, in any sibling directory, as a git remote
or submodule, or in the owning GitHub account. No ingestion endpoint, schema,
validator, persona upsert or ingest test suite was found, and none is assumed to
exist. Nothing about a GOTHAMITE implementation is inferred anywhere in SD-021.

**Consequence for what "GOTHAMITE agreement" means.** It cannot presently mean
*implementation compatibility approval*, because there is no implementation to be
compatible with. Until an ingestion layer exists, the only thing that can be given
is **contract approval** -- a decision to freeze the ingestion contract -- which is
a different act.

SD-021, SD-021.1 and SD-021.2 therefore remain **PROPOSED and NOT IN FORCE** until
the ingestion contract is **formally frozen**. The absence of a counterparty is not
agreement, and it is not a reason to promote the proposal.

**Three distinct things, deliberately kept apart:**

| | What it asserts | Current state |
|---|---|---|
| **Proposal correctness** | The sandbox-side reasoning is sound: the page types are exhaustive, the required/omitted matrix is internally consistent, and no synthetic identifier or surrogate timestamp is introduced | Argued in this entry. Reviewed sandbox-side only |
| **Contract approval** | `API_CONTRACT.md` is amended and frozen with `page_type` in it | **Not given.** `API_CONTRACT.md` is unchanged |
| **Implementation compatibility** | A GOTHAMITE ingestion layer accepts all three shapes | **Not assessable.** No implementation exists |

A proposal can be correct and still unapproved; a contract can be approved and
still unimplemented. Collapsing these would let "the reasoning looks right" pass
for "the contract is settled".

**Intended architecture if no pre-existing GOTHAMITE implementation is
introduced.** In that case the order is:

1. **Finalise** the sandbox/GOTHAMITE ingestion contract, `page_type` included.
2. **Then implement** the first GOTHAMITE ingestion layer against that frozen
   contract.
3. **No migration or compatibility rollout is required**, because there is no
   existing validator to migrate. The staged rollout in
   `AgentsDocs/reports/OPEN_4_CHANGE_LIST.md` §3.4 -- accept-and-ignore, then send,
   then enforce -- exists solely to protect a *deployed* validator from a required
   new field. With no deployed validator, that risk does not arise and the staging
   is unnecessary.

This is contingent, not settled: if a pre-existing GOTHAMITE implementation is
later introduced, §3.4's staged rollout becomes live again and the compatibility
review that could not be run must be run before the contract is frozen.

**What this clarification does not do.** It does not resolve OPEN-4, does not
promote SD-021, does not claim GOTHAMITE has agreed to anything, and does not
assume any property of a GOTHAMITE repository, schema, validator or test suite.

**Question.** `API_CONTRACT.md` §3 marks `persona.handle` and
`persona.observed_at` required on every artifact. The crawl structure in
`SCRAPER_AGENT_SPEC.md` §3 is index -> threads/listings -> profiles, and two of
those three page types cannot satisfy that:

- **index pages** have no single author -- against the Phase-4 sites as built they
  are persona-*plural*, each listing 16 threads by 2 distinct handles
- **profile pages** have an unambiguous persona but **no single post timestamp**,
  so `persona.observed_at` has no correct value

**Proposed decision -- Option D.** An explicit `page_type` discriminator at the
ingestion boundary, with three allowed values:

| `page_type` | Represents | `persona` | `persona.handle` | `persona.observed_at` |
|---|---|---|---|---|
| `index` | a listing / index / navigation page | **omitted** | n/a | n/a |
| `item` | a thread, listing or post with one author | required | required | required -- the item's own post timestamp |
| `profile` | a single persona's profile page | required | required | **omitted** |

For `profile`, the join date **must not** be substituted for `observed_at`, and
neither may the most-recent-post timestamp.

**Rationale as given.** The purpose of `page_type` is to make the absence of
persona information **explicit**, rather than forcing GOTHAMITE to infer semantics
from a missing field. An absent `persona` with no discriminator is ambiguous
between "this page has no author", "extraction failed" and "the scraper is
buggy" -- three cases that warrant different handling on the ingest side and are
indistinguishable without it.

Supporting points from the existing documents, none of which decide the question
on their own:

- `DATA_MODEL.md` §2's **Artifact entity has no persona field** -- its columns are
  `artifact_id`, `source_id`, `url`, `raw_content`, `content_hash`, `collected_at`,
  `relay_path`. Persona is a separate entity whose `first_seen`, `last_seen` and
  `post_count` are derived *across* artifacts. An artifact carrying no persona is
  therefore not structurally anomalous.
- `DATA_MODEL.md` §1 rule 2 -- "every derived claim traces to an artifact" -- rules
  out a synthetic handle, which would trace to nothing on the page.
- A synthetic handle would also materialise phantom `Persona` rows (unique on
  `handle` + `source_id`) and break `SCRAPER_AGENT_SPEC.md` §8 criterion 3, which
  requires exactly the six seed personas to be found.

**Why this is not recorded as resolved.** SD-014 fixed the authority boundary:
GOTHAMITE's ingestion representation is authoritative on its side, and the two
models meet at `API_CONTRACT.md`. `page_type` changes that boundary in both
directions -- a new required field the scraper sends and GOTHAMITE must accept --
so it cannot be settled unilaterally here. Recording it as resolved would make
this repository the author of a contract it does not own.

**Residual gaps -- now resolved at proposal level (2026-09-07).** Both were
recorded as open when SD-021 was first written; both have since been answered by
the same human decision that proposed `page_type`. They remain **proposed, not in
force**, on exactly the same footing as the rest of SD-021.

### SD-021.1 -- `page_type` is REQUIRED, with no default

`page_type` is a **required** field. Allowed values are exactly `index`, `item`
and `profile`.

- There is **no default value.** A validator must not infer `item` -- or anything
  else -- from an absent field.
- A **missing** `page_type` must eventually be rejected by the GOTHAMITE ingestion
  contract.
- An **unsupported** value must likewise be rejected. The enum is closed.

*Rationale.* A default would reintroduce exactly the ambiguity `page_type` exists
to remove: an artifact with no persona and no discriminator is indistinguishable
between "this page has no author", "extraction failed" and "the scraper is buggy".
Defaulting to `item` would be the worst case, because it would then demand a
persona the page cannot supply and turn a silent ambiguity into a spurious `400`.

*Rollout consequence, unchanged and still the highest-risk item here.* Because the
field is required rather than optional, a GOTHAMITE validator that rejects unknown
fields will `400` **every** artifact until it is updated, and
`SCRAPER_AGENT_SPEC.md` §6 tells the scraper to log a 400 and continue -- so a
whole run would be lost quietly, with a clean-looking summary. This makes the
staged rollout in `AgentsDocs/reports/OPEN_4_CHANGE_LIST.md` §3.4 a practical
requirement of adopting SD-021.1, not merely a suggestion.

### SD-021.2 -- `identifiers[].observed_at` stays REQUIRED, with no substitution

`observed_at` remains **required on every identifier object that exists**. It is
not relaxed, not made conditional on `page_type`, and not defaulted.

- If `identifiers` is `[]`, **no identifier timestamp is required.** An empty array
  is already normal per `API_CONTRACT.md` §3, and remains so on every page type.
- **No page-level timestamp substitution is introduced.** An identifier's
  `observed_at` must **not** be derived from the profile "Joined" date, the latest
  post shown on a profile, the collection time, or any other surrogate.

*Rationale.* `API_CONTRACT.md` §4 states that the `observed_at` / `collected_at`
distinction is load-bearing: `observed_at` is when the thing happened on the site,
and GOTHAMITE's temporal succession scoring -- the signal that catches the B1 to B2
rebrand -- reads it. Every listed surrogate is a `collected_at`-like or
page-scoped value wearing an `observed_at` label, which is precisely the
conflation §4 warns silently breaks that link. A surrogate would not fail loudly;
it would produce a plausible timeline that is wrong.

*Consequence -- an invariant this creates.* Taken together, SD-021 and SD-021.2
mean an identifier can only be emitted where a real per-observation timestamp
exists, which under the proposed page types is `item` pages alone. It follows that
**a `profile` or `index` page must not carry an extractable identifier**: if one
did, the artifact could not be emitted in conformance, because there would be no
permissible value for its `observed_at`.

The Phase-4 mock sites already satisfy this -- neither index nor profile pages
render a PGP block or a wallet, so both yield `identifiers: []` -- but they satisfy
it as a property of how they were written, not as an asserted invariant. Recorded
here so that a future edit to `mock_sites/` does not silently break conformance.
No test or site change is made now; `mock_sites/` and the test suites are untouched
by this entry.

**Affected documents if agreed:** `API_CONTRACT.md` §3 (field table and example),
`SCRAPER_AGENT_SPEC.md` §8, and GOTHAMITE's ingest validator and persona upsert.
See `AgentsDocs/reports/OPEN_4_CHANGE_LIST.md` for the itemised cross-repository
change list.

**Affected documents now:** none. This entry only.

---

## SD-022 - Handle and contact identifier semantics -- **IN FORCE**

> **STATUS: IN FORCE.** Adopted at the contract freeze of 2026-09-07. The
> specification amendments this decision called for have been **applied** to the
> documents named below. This entry is now a record of a decision that governs, not a
> proposal awaiting one.
>
> **Adoption is not counterparty agreement.** No GOTHAMITE repository exists to have
> agreed to anything; the recorded architecture is to finalise the contract first and
> implement GOTHAMITE against it. Absence of objection is not assent, and this file
> makes no claim that implementation compatibility has been established.

**Relates to:** OPEN-5. **Kind:** Human architectural decision, 2026-09-07.
**Blocks:** Phase 5.
**Analysis:** `AgentsDocs/reports/OPEN_5_DECISION_BRIEF.md` and
`AgentsDocs/reports/OPEN_5_HANDLE_SEMANTICS.md`.

**Question.** OPEN-5 asks whether `handle` and `contact` are ever emitted as
`identifiers[]` entries, and how `contact` is extracted and normalised.

### SD-022.1 -- Handle semantics: H1, never emitted

The scraper **MUST NOT** emit the persona's own handle as an entry in
`identifiers[]`. The persona's own handle is represented by **`persona.handle`**,
and by that field alone.

*Rationale, as decided:*

- `DATA_MODEL.md` §2 makes `Identifier.persona_id` a **required FK to Persona**.
- `SCRAPER_AGENT_SPEC.md` §4's handle rule -- "From the post's author field or the
  profile page path" -- yields the **persona's own** handle, never a mentioned one.
- Therefore `Identifier(type=handle, value=persona.handle, persona_id=<that same
  persona>)` is **tautological**: it restates the persona's own key back at the
  persona and adds no cross-persona information.
- Artifact provenance is already retained through the artifact and its persona
  association, so `DATA_MODEL.md` §1 rule 2 is satisfied without such a row.
- Handle similarity remains a future/analysis signal **between persona handles**
  (`DATA_MODEL.md` §3, Levenshtein <= 2, weight 0.05). It is computed over
  `Persona.handle` pairs and does not require handle identifiers to exist.

*Supporting structural point from the analysis.* `DATA_MODEL.md` §3 matches PGP and
wallets by **identity of a shared value** and handles by **similarity of two
different values**. The seed data depends on that difference: A1 `nightjar` and A2
`n1ghtjar_` are the headline link and their handles do **not** match, while C1
`nightjarr` is one character from A1 and must **not** link. A handle is a persona's
key, not an observation about it.

### SD-022.2 -- Contact semantics: C1, reserved and not extracted

`contact` is **not extracted and not emitted**. No contact extraction rule,
normalisation rule, seed data, scoring rule or acceptance criterion is to be
invented as part of OPEN-5.

*Rationale.* `contact` appears exactly once in the repository -- the enum on
`DATA_MODEL.md` §2. There is no extraction rule in `SCRAPER_AGENT_SPEC.md` §4, no
normalisation row in `API_CONTRACT.md` §3 (where `handle` has one), no seed value in
`DATA_MODEL.md` §4, no signal in §3's scoring table, and no acceptance criterion
anywhere. Emitting it would require inventing a definition, a rule, seed data and a
purpose -- and adding contact values to the deterministic corpus would reopen the
closed Phase 4.

### SD-022.3 -- The enum is not narrowed

`handle` and `contact` **stay** in `DATA_MODEL.md` §2's Identifier `type` enum as
**reserved-but-unused**. This decision does **not** narrow the enum. Their
semantics await a separate future decision.

### SD-022.4 -- Mentioned handles are out of scope

A handle **mentioned in another persona's content** is explicitly outside OPEN-5.
Such a handle is **not automatically that persona's identifier** and **must not** be
assigned to the author's `persona_id`.

*Why this needed saying.* Because `Identifier.persona_id` is a required FK,
emitting a mentioned handle would either mis-attribute it to the author or create a
**phantom persona** for a handle that may not exist on that site. Mentioned-handle
extraction is a separate future design question, not an interpretation of the
existing documents.

### Dependency on OPEN-4 -- explicitly not resolved

**This decision does not resolve OPEN-4.** The proposed `page_type` semantics
(SD-021) and identifier timestamp rules (SD-021.2) are unaltered by it.

SD-022.1 is, however, the option **least entangled** with OPEN-4: emitting no handle
identifiers on any page type means the question never has to be answered for this
field. That independence is a property of the decision, not a resolution of OPEN-4.

**If OPEN-4 later creates a conflict, reopen the relevant decision rather than
silently changing this one.**

### What this entry does not do

It does not amend any contract, does not resolve OPEN-5, does not resolve OPEN-4,
and does not narrow any enum. Contract adoption is pending.

**Affected documents if adopted:** `API_CONTRACT.md` §3 (a clarifying sentence that
the `handle` normalisation row governs `persona.handle`, and that `handle` is not
emitted in `identifiers[]`), `SCRAPER_AGENT_SPEC.md` §4 (same, plus a note that
`contact` is not extracted). `DATA_MODEL.md` unchanged -- the enum is not narrowed.

**Affected documents now:** this entry, and
`AgentsDocs/reports/OPEN_5_DECISION_BRIEF.md`.

---

## SD-023 - Ingest payload `url` form -- **IN FORCE**

> **STATUS: IN FORCE.** Adopted at the contract freeze of 2026-09-07. The
> specification amendments this decision called for have been **applied** to the
> documents named below. This entry is now a record of a decision that governs, not a
> proposal awaiting one.
>
> **Adoption is not counterparty agreement.** No GOTHAMITE repository exists to have
> agreed to anything; the recorded architecture is to finalise the contract first and
> implement GOTHAMITE against it. Absence of objection is not assent, and this file
> makes no claim that implementation compatibility has been established.

**Relates to:** OPEN-6. **Kind:** Human architectural decision, 2026-09-07.
**Blocks:** Phase 5.
**Analysis:** `AgentsDocs/reports/OPEN_6_DECISION_BRIEF.md`.

**Question.** OPEN-6 asks whether `url` in the ingest payload includes a scheme.

### Chosen decision -- U2: a canonical absolute HTTP URL

At the GOTHAMITE ingestion boundary, `url` is a **canonical absolute HTTP URL**.

**Required form:**

```
http://<mock-host>/<path>
```

For the worked example already in `API_CONTRACT.md` §3:

```
http://alpha7fq2mx9k.onion.mock/thread/14
```

**Rules, as proposed:**

1. The scheme is **required**.
2. The scheme is **`http`** for the current simulated sandbox.
3. The `.onion.mock` host is **required**.
4. A route path is **required**.
5. A bare `/path` value is **invalid**.
6. A host-and-path value **without** a scheme is **invalid**.
7. **Do not introduce HTTPS** unless the sandbox actually implements it.
8. `url` is an **ingestion-payload field** and is **not** part of the relay
   wire-layer format.
9. This decision defines **no** query-string or fragment semantics.
10. This decision defines **no** URL deduplication semantics. Duplicate detection
    remains `content_hash` + `source_id`, per `API_CONTRACT.md` §4.

**Rationale, as decided:**

- The field is named `url`.
- U2 is syntactically parseable as a URL by standard URL libraries.
- It gives GOTHAMITE a canonical absolute URL representation.
- U1 would require treating a non-absolute value as a special host-and-path string.
- U3 directly conflicts with `API_CONTRACT.md`'s explicit host requirement.
- **This decision does not rely on examples being normative.** The two existing
  examples in `API_CONTRACT.md` §3 and `README.md` §4 show the scheme-less form; the
  decision departs from them deliberately, on the reasoning above, and those
  examples will need updating on adoption.

*Note on how this decision was reached.* The decision brief recommended U1 at low
confidence and named its own strongest counter-argument: a scheme-less
host-and-path string **is not a URL** in a field called `url`, so a standard RFC
3986 parser returns an empty host and silently swallows the whole value as a path.
That counter-argument is what the human decision turned on. Recorded so the
reversal is legible rather than looking like drift.

### Rule 8, restated -- scope boundary

`url` is carried **only** in the `POST /api/v1/ingest` body defined by
`API_CONTRACT.md` §3. `RELAY_PROTOCOL.md` §5.1 fixes the wire layer at four fields
-- `next_hop`, `next_host`, `next_port`, `payload` -- and the relay chain never sees
this string. **SD-023 therefore has no effect on routing, layering, the visibility
table, or anything in Phases 1 to 4.**

### Preserved contradiction -- NOT resolved here

`DATA_MODEL.md` §2 describes `Artifact.url` as **"mock-site path"**, while
`API_CONTRACT.md` §3 requires the `.onion.mock` host in the ingest payload. Read
strictly, "path" means `/thread/14` with no host at all, which is incompatible with
both the contract's existing host rule and with SD-023.

**This contradiction is deliberately left standing.** `DATA_MODEL.md` has **not**
been edited, and must not be edited silently to make SD-023 look consistent.

SD-023 resolves the **ingest boundary representation** -- what the scraper sends.
It does **not** resolve the **ownership or wording of the stored `Artifact.url`
field**, which remains a contract/data-model wording question to be reconciled
**before contract freeze**.

That reconciliation is genuinely open, and the authority hierarchy does not settle
it: `API_CONTRACT.md:4` defers to *GOTHAMITE's* `docs/DATA_MODEL.md`, which per the
SD-021 project-state clarification **does not exist**, while SD-014 gives the local
`DATA_MODEL.md` authority over the sandbox data model but expressly not over
GOTHAMITE's ingestion representation -- and `Artifact` is an entity GOTHAMITE
stores. Which side `Artifact.url` falls on is not determined by SD-014's wording.

### Residual items

1. **The `Artifact.url` wording question above.** Must be reconciled before freeze.
2. **Index-page trailing slash.** Rule 4 requires a route path, which implies an
   index artifact is `http://alpha7fq2mx9k.onion.mock/` with the slash present. The
   decision does not state this explicitly, so it is **narrowed but not eliminated**.
3. **Query strings and fragments.** Undefined by rule 9. No mock-site page uses
   either today.
4. **Example updates.** `API_CONTRACT.md` §3 and `README.md` §4 both show the
   scheme-less form and would need updating on adoption.

### What this entry does not do

It does not amend any contract, does not resolve OPEN-6, does not edit
`DATA_MODEL.md`, does not define dedup or query-string semantics, and does not
touch OPEN-4, OPEN-5 or OPEN-9. Contract adoption is pending.

**Affected documents if adopted:** `API_CONTRACT.md` §3 (field rule and example),
`README.md` §4 (example), and `DATA_MODEL.md` §2 **only if** residual 1 is
reconciled in the contract's favour.

**Affected documents now:** this entry, and
`AgentsDocs/reports/OPEN_6_DECISION_BRIEF.md`.

---

## SD-024 - Relay error transport and response discriminator -- **SPEC AMENDED**

> **STATUS: SPECIFICATION AMENDED; IMPLEMENTED AND VERIFIED.**
> `RELAY_PROTOCOL.md` §§6, 7 and 9.1-9.5 were amended on 2026-09-07 to carry this
> decision, and the implementation landed on 2026-09-08: relays seal typed
> `relay` / `success` / `error` content, the client branches on the sealed `type`, and
> HTTP status is transport-only. Phase 1 **61/61**, Phase 4 **42/42**, combined
> **103/103**.
>
> **This entry keeps the status category SPEC AMENDED.** SD-024's own decision
> structure records specification state, not a separate adoption state, and none is
> invented here. What is recorded is that its specification, code and tests agree.
>
> **Amended by SD-029 and SD-030, both IN FORCE as of 2026-09-08.** SD-029 amends
> **§E** only, supplying the plaintext fallback body that §E left undefined, and
> **closes residual 1**. SD-030 amends **§C** only, widening the closed code set from
> three to four with `unusable_layer`. §§A, B, D, F, G, H, I and J are untouched by
> both, and **residual 3 stands unchanged and OPEN**.

**Relates to:** OPEN-9. **Kind:** Human architectural decision, 2026-09-07.
**Blocks:** Phase 6 hardening.
**Analysis:** `AgentsDocs/reports/OPEN_9_DECISION_BRIEF.md`,
`AgentsDocs/reports/OPEN_9_ERROR_ENVELOPE.md`,
`AgentsDocs/reports/OPEN_9_FINAL_DEFINITION.md`.

**Question.** `RELAY_PROTOCOL.md` §5.2 defines the forward wire layer and §7 the
return path, but neither defines what an **error** looks like on the wire. §9 says
only "return an error" for three of its four cases, while the fourth requires the
exit relay to return "through the normal return path". The client has no way to
distinguish a sealed error from a sealed success.

### A. Error transport = E2, uniform layered sealing

Relay-generated protocol errors travel by the **normal layered return mechanism**. A
relay seals the error response for its predecessor **when it still possesses the
required encryption key**.

A relay that cannot decrypt the incoming layer holds no key and therefore **cannot
seal an error itself**. It returns the failure to its **immediate predecessor** per
SD-011; that predecessor reports the failure under section D below.

### B. Response discriminator = D2, typed inner plaintext

The outer wire envelope remains **exactly** as SD-002 specifies:

```json
{ "nonce": "<b64>", "ciphertext": "<b64>" }
```

The discriminator lives **inside the decrypted plaintext**. Three types:

```json
{ "type": "relay",   "inner": "<base64 of successor response bytes>" }
{ "type": "success", "body":  "<base64 of destination raw HTTP response>" }
{ "type": "error",   "code": "<closed error code>", "reported_by": "<relay_id>" }
```

**Intermediate relays MUST NOT parse the inner response merely to determine its
type.** They forward the response bytes **opaquely**. This is why `inner` carries
base64 bytes rather than a nested JSON object: an object would force every hop to
parse, creating a detection point the design deliberately removes.

### C. Error codes -- closed set of three

```
next_hop_unreachable
decryption_failure
destination_unreachable
```

These map to `RELAY_PROTOCOL.md` §9 bullets 1, 2 and 4. Bullet 3 (directory
unreachable) is client-side and never appears on the wire.

**`hop_timeout` and `malformed_response` are NOT protocol error codes.**

- **Hop timeout** maps to the existing unreachable cause appropriate to the failing
  hop: waiting on the next relay -> `next_hop_unreachable`; waiting on the
  destination -> `destination_unreachable`. SD-011 introduced `HOP_TIMEOUT` as a
  bound, not as a new cause.
- **Malformed / unparseable successor response** is a **client-side protocol parsing
  failure**, not a relay-generated wire error. Under section B no relay parses
  relayed content, so no relay is in a position to detect it.

### D. `reported_by`

`reported_by` means **the last relay that successfully processed the request and is
reporting the failure**.

A relay **MUST NOT** expose the identity of a downstream relay it could not reach, or
whose response it could not decrypt.

**SD-011 is preserved and remains applicable.** See section J.

### E. HTTP status

- **HTTP 200** whenever a sealed protocol response envelope is successfully returned
  -- **regardless of whether the decrypted protocol type is `success` or `error`**.
- **HTTP non-2xx** is retained **only** for a failure where the responding relay
  **cannot produce a sealed protocol response** for its predecessor.
- **HTTP status MUST NOT be used by the client as the success/error
  discriminator.** The encrypted protocol `type` / `code` is authoritative for
  protocol-level success and error.

This leaves one protocol discriminator and one transport signal with
non-overlapping meanings, rather than two competing sources of truth. SD-001's
`POST /relay` transport is otherwise unchanged; its current use of non-2xx as the
client's failure signal is retired.

### F. Layer depth

The client **MUST NOT** classify success versus error using the response layer count.

Layer depth **may** structurally reveal the point at which processing failed, because
the client knows how many of its own return-path decryptions succeeded. This is not a
disclosure choice -- it is unavoidable, and SD-011 already permits the client to learn
the last relay it successfully reached. **No explicit hop index or failure-position
field is added.**

### G. Malformed responses

The protocol distinguishes four outcomes and they must not collapse into each other:

| Outcome | Category |
|---|---|
| Valid encrypted **success** | Application response -- includes the site's own 4xx/5xx, which are **not** protocol errors |
| Valid encrypted **error** | Protocol error |
| **Malformed / unparseable** protocol response | **Client-side** condition |
| **Transport timeout / unreachable** | **Client-side** condition |

Malformed response and transport timeout are client-side **unless** they map to one
of the explicitly defined relay error causes in section C.

### H. Cryptography

**No cryptographic construction change is authorized by this decision.** AES-GCM,
nonce handling, key distribution and layered encryption remain unchanged.
`RELAY_PROTOCOL.md` §7's rule -- a fresh nonce for every encryption, forward and
return, never reused with the same key -- applies unchanged to error layers.

### I. Scope

This decision affects the **simulated onion routing return protocol only**. It does
**not** modify the GOTHAMITE ingestion API or Phase-4 mock-site behaviour. The
forward path (§5.1, §5.2, §5.3) is unchanged.

### J. SD-011 -- preserved and still applicable

**SD-011 remains in force.** Specifically:

- `reported_by` is always the emitting relay's own `relay_id`, never a downstream
  one.
- The client may learn the last relay it successfully reached, and never the identity
  of a failed relay further down the path.
- Every hop is bounded by `HOP_TIMEOUT`, so no failure can hang.
- The failed hop is named in the detecting relay's **own log**, per §8.

**Narrowed in application, not repealed.** SD-011's rewriting rule was written for
plaintext propagation at every hop. Under SD-024 a relaying relay cannot read a
sealed error, so rewriting is neither possible nor needed there. It applies to
**exactly one adjacency**: the predecessor of a relay that returned plaintext because
it could not decrypt (section A).

**SD-011's recorded "known deviation"** -- plaintext errors at every hop, against §9
bullet 4 -- is **resolved in principle** by this decision and will be retired **on
adoption**, not now.

### Interaction with other recorded decisions

| Decision | Effect |
|---|---|
| **SD-001** | Transport unchanged; the non-2xx protocol signal is retired (section E) |
| **SD-002** | **Wire shape unchanged.** Its stated consequence -- "what falls out of the innermost envelope is the raw HTTP response" -- becomes false: what falls out is a typed object carrying it. **An amendment in substance, to be made on adoption** |
| **SD-003** | Unaffected. `request_id` remains relay-local and off the wire |
| **SD-011** | Preserved, narrowed in application (section J) |
| **SD-021 / SD-022 / SD-023** | **Unaffected.** All three are ingest-boundary decisions; relay errors never reach the ingestion seam |

### Implementation consequences -- none of them yet performed

- **`AgentsDocs/RELAY_PROTOCOL.md` is the authoritative specification and MUST be
  amended BEFORE implementation.** §6's pseudocode gains an error branch, §7 gains
  the typed-content definition, §9 gains the code set and the timeout mapping.
- `relay/relay_node.py` will need return-path error handling changes.
- `client/onion_client.py` will need typed-response parsing.
- `tests/test_phase1.py` will need corresponding updates -- the fixed-depth unwrap
  assumption and the plaintext-error assertions in `TestFailureHandling` become
  invalid, though every property they assert survives.
- `common/onion_crypto.py` needs **no** change: it takes and returns bytes, and this
  decision changes which bytes are sealed, not how.
- `API_CONTRACT.md`, `DATA_MODEL.md`, `SCRAPER_AGENT_SPEC.md`, `mock_sites/` and
  `tests/test_phase4.py` need **no** change.

**No implementation compatibility has been established.** Nothing above has been
built, run or tested.

### Residual items

1. ~~**Whether the plaintext non-2xx body of section E carries a `code`.**~~
   **CLOSED 2026-09-07 by SD-029 (P3, proposed):** it does. HTTP 400 with exactly
   `{"error": "decryption_failure", "reported_by": "<own relay_id>"}`, and
   `decryption_failure` is the only permitted value there -- the other two §C codes
   are unreachable in a channel that exists only when the relay holds no key. §C
   itself is unchanged: it governs `code`, and this body's field is `error`.
2. ~~**The exact amendment wording for `RELAY_PROTOCOL.md` §6, §7 and §9.**~~
   **CLOSED 2026-09-08.** §7's typed-content table and §§9.1-9.5 landed at the
   2026-09-07 freeze; §9.3's fallback body (SD-029) and §6's validation boundary plus
   §9.1's fourth code (SD-030) landed under OPEN-9. The implementation and tests match
   all of it.
3. **Malformed responses remain permanently uncodeable** under this design. If a
   future design gave relays reason to parse relayed content, malformation would
   become detectable at a hop and would need a code §9 does not supply.

Resolved by this decision, and previously open: whether `code` should be omitted
entirely (section C defines it), and the name of the continuation type (section B
fixes `relay`).

### What this entry does not do

It does not amend `RELAY_PROTOCOL.md`, does not resolve OPEN-9, does not touch
OPEN-4, OPEN-5 or OPEN-6, does not change any cryptography, and does not claim
anything has been implemented or verified.

---

## SD-025 - `API_CONTRACT.md` authority clause -- **IN FORCE**

> **STATUS: IN FORCE.** Adopted at the contract freeze of 2026-09-07. The
> specification amendments this decision called for have been **applied** to the
> documents named below. This entry is now a record of a decision that governs, not a
> proposal awaiting one.
>
> **Adoption is not counterparty agreement.** No GOTHAMITE repository exists to have
> agreed to anything; the recorded architecture is to finalise the contract first and
> implement GOTHAMITE against it. Absence of objection is not assent, and this file
> makes no claim that implementation compatibility has been established.

**Resolves:** freeze blocker **A2**. **Kind:** Human architectural decision,
2026-09-07. **Analysis:** `AgentsDocs/reports/CONSOLIDATED_FREEZE_REVIEW.md` §8.2.

**Question.** `API_CONTRACT.md` line 4 reads:

> *"**Conforms to:** GOTHAMITE `docs/DATA_MODEL.md` -- that file is authoritative. If
> this contract and the data model disagree, the data model wins and this file gets
> corrected."*

That file does not exist -- no GOTHAMITE repository is present in this workspace, in
any sibling directory, as a git remote or submodule, or in the owning GitHub account.
The contract's stated superior authority is missing, and blocker A1 (the
`Artifact.url` wording contradiction) cannot be decided without knowing whose model
governs.

**This was not a fresh ambiguity.** SD-014, which is **in force** (OPEN-1 is closed),
already says something different:

> *"The two must remain compatible **at the API boundary**, which is
> `AgentsDocs/API_CONTRACT.md`. Neither repository owns the other's model."*

SD-014 treats `API_CONTRACT.md` as **the boundary**; line 4 treats it as
**subordinate to one participant's internal model**. Those are incompatible, SD-014
is the later and in-force decision, and line 4 was simply never updated to match. The
missing GOTHAMITE file made the tension visible; it did not create it.

### Chosen decision -- O2: the contract is self-authoritative for the wire format

`API_CONTRACT.md` is **authoritative for the sandbox <-> GOTHAMITE wire format**.

- GOTHAMITE `docs/DATA_MODEL.md` remains authoritative for **GOTHAMITE's internal
  storage and ingestion representation** (SD-014, unchanged).
- `AgentsDocs/DATA_MODEL.md` remains authoritative for the **sandbox's simulated
  ground truth and sandbox data model** (SD-014, unchanged).
- Neither repository owns the other's internal model, and **neither internal model
  overrides the boundary**.
- A disagreement between this contract and either side's internal model is a
  **change request against the contract**, not an automatic override of it.
- **Amendment by agreement** once a GOTHAMITE counterparty exists.

**Proposed replacement wording for line 4**, to be applied at freeze:

> **Conforms to:** This file is authoritative for the sandbox <-> GOTHAMITE wire
> format. Per SD-014, neither repository owns the other's internal model; they must
> remain compatible at this boundary. A disagreement between this contract and either
> side's internal model is a change request against this file, not an automatic
> override of it. Amendment by agreement once a GOTHAMITE counterparty exists.

**Rationale.**

1. **It is the only option consistent with SD-014 as already adopted.** SD-014 names
   `API_CONTRACT.md` as the boundary at which two independently-owned models must
   agree. A boundary subordinate to one side's internal model is not a boundary -- it
   is that side's API specification.
2. **`API_CONTRACT.md` §1 already describes itself in boundary terms:** *"the only
   point of contact between the two repos."*
3. **It grants this repository no new authority.** GOTHAMITE's internal model is
   untouched. What changes is only that the contract stops being overridable by a
   document neither party can currently read.
4. **It unblocks A1** by separating the **transmitted** value (this contract's, fixed
   by SD-023) from the **stored** value (whoever owns `Artifact`). It does **not**
   decide A1 -- see below.
5. **It is reversible and does not pre-empt a counterparty.** When GOTHAMITE exists,
   an explicit two-key amendment rule can be added without re-litigating ownership.

**Strongest argument against, recorded rather than dismissed.** O2 lets
`darkweb-sandbox` fix the wire format unilaterally, and a future GOTHAMITE team may
find some part of it unworkable. Two things mitigate it: the contract is amendable by
agreement once a counterparty exists, and the recorded architecture (SD-021's
project-state clarification) already sequences the work as *finalise the contract,
then implement GOTHAMITE against it* -- which presupposes the contract leads.

**Rejected alternatives.** O1 (keep the deferral) blocks the freeze indefinitely on a
file nobody has. O3 (defer to the local `DATA_MODEL.md`) is the mirror-image
over-delegation, makes the sandbox's internal model govern a shared boundary, and
conflicts with SD-014's "neither repository owns the other's model" -- it would also
override SD-023 by making *"mock-site path"* win. O4 (two-key amendment) is correct
in principle for a live cross-organisation contract but, with no counterparty in
existence, behaves as O1.

### What this decision does NOT do

- It does **not** resolve **A1**, the `Artifact.url` wording contradiction. It
  narrows the question -- the contract now governs the transmitted value, so what
  remains is what the **stored** `Artifact.url` should say and which model owns that
  entity -- but the choice is still open and still blocks freeze.
- It does **not** resolve **A3**, counterparty identifier attribution.
- It does **not** constitute GOTHAMITE agreement. No counterparty exists to agree,
  and absence is not assent.
- It does **not** edit `API_CONTRACT.md`. That happens at freeze.

**Affected documents if adopted:** `API_CONTRACT.md` line 4 (replacement wording
above). Nothing else -- SD-014 is confirmed rather than amended.

**Affected documents now:** this entry, and
`AgentsDocs/reports/CONSOLIDATED_FREEZE_REVIEW.md` (A2 reclassified).

---

## SD-026 - Stored `Artifact.url` wording and `DATA_MODEL.md` §2/§3 scope -- **IN FORCE**

> **STATUS: IN FORCE.** Adopted at the contract freeze of 2026-09-07. The
> specification amendments this decision called for have been **applied** to the
> documents named below. This entry is now a record of a decision that governs, not a
> proposal awaiting one.
>
> **Adoption is not counterparty agreement.** No GOTHAMITE repository exists to have
> agreed to anything; the recorded architecture is to finalise the contract first and
> implement GOTHAMITE against it. Absence of objection is not assent, and this file
> makes no claim that implementation compatibility has been established.

**Resolves:** freeze blocker **A1**. **Kind:** Human architectural decision,
2026-09-07. **Analysis:** `AgentsDocs/reports/A1_DECISION_BRIEF.md`.

**Question.** `DATA_MODEL.md` §2 describes `Artifact.url` as *"mock-site path"*, which
read strictly means `/thread/14` -- no host, no scheme. That is incompatible with
`API_CONTRACT.md` §3's host requirement and with SD-023's `http://<mock-host>/<path>`.
SD-025 settled that the contract owns the **transmitted** value; what remained was
the **stored** value's wording, and whether this repository may describe it at all.

### The structural finding behind the question

`Artifact` is unambiguously a **GOTHAMITE-stored** entity -- its own description says
*"Raw scraped content, stored verbatim. The evidence locker"*, and it is keyed by
`artifact_id` with `content_hash` and `collected_at`. **The sandbox never stores an
artifact; it sends one.** Verified: no file in `common/`, `directory/`, `relay/`,
`client/`, `mock_sites/`, `scripts/` or `tests/` references `artifact_id`,
`raw_content` or `content_hash`.

`DATA_MODEL.md` §2 therefore mixes two kinds of content:

| Section | Describes | Owner under SD-014 |
|---|---|---|
| §2 `Source`, `Artifact`, `Persona`, `Identifier` | GOTHAMITE's **storage** representation | GOTHAMITE |
| §2 `Relationship`, `Evidence`, `Actor` | GOTHAMITE's **intelligence** structures | GOTHAMITE |
| §3 Scoring -- weights, thresholds, bands | GOTHAMITE's **correlation logic** | GOTHAMITE |
| §4 Seed data, §5 Content volume | The sandbox's **simulated ground truth** | **darkweb-sandbox** |

SD-014 is in force and says this repository is authoritative for *"the sandbox's
simulated ground truth and sandbox data model"* and expressly not for GOTHAMITE's
internal representation -- *"Do not invent or restate a GOTHAMITE data model in this
repository."* §2 carries **no scope sentence** saying which side of that line it
falls on.

`Artifact.url` surfaced the mismatch first only because it is the one §2 field that
also appears on the wire. It would not have been the last:
`Persona.first_seen` / `last_seen` / `post_count` are already touched by SD-021's
profile rules, and §3's weights are the numbers the demo quotes throughout.

### Chosen decision -- W2: scope-mark §2 and §3, and correct the note

**Two edits, both to `AgentsDocs/DATA_MODEL.md`, both at freeze:**

**1. A scope sentence at the head of §2:**

> These tables and the scoring in §3 describe the **expected** GOTHAMITE
> representation, for context. Per SD-014 they are **non-normative for GOTHAMITE**,
> which owns its own model. Where a field also appears on the wire,
> `AgentsDocs/API_CONTRACT.md` governs.

**2. The `Artifact.url` note corrected:**

```
| `url` | str | absolute mock-site URL, e.g. http://alpha7fq2mx9k.onion.mock/thread/14 |
```

**Rationale.**

1. **It resolves A1 and the category error in one edit.** W1 (correct the cell only)
   would have unblocked the freeze and left the scope question to resurface at the
   next diverging field.
2. **It is consistent with SD-014 and SD-025 as recorded.** SD-014 forbids restating
   a GOTHAMITE model here; SD-025 says neither internal model overrides the boundary.
   A scope sentence makes §2 and §3 *descriptive context* rather than a competing
   specification, which is what both decisions already imply.
3. **Stored value equals sent value.** That fits *"stored verbatim, the evidence
   locker"* and `API_CONTRACT.md` §5 rule 1, *"Store `raw_content` before parsing
   anything"*.
4. **It retains §2 and §3 rather than deleting them.** The scoring table is what
   makes the seed data checkable -- it is how anyone verifies that A1 to A2 should
   score 0.95 and C1 must not link. W4 (delete the note) would have solved the
   contradiction by silence.

**Strongest argument against, recorded rather than dismissed.** W2 is a larger edit
than A1 strictly required, and it changes the felt status of §3's weights from
specification to expectation. Nothing depends on that today -- no GOTHAMITE exists to
disagree -- but it is a real change in what the file claims, and a future GOTHAMITE
team could reasonably choose different weights, at which point the demo's quoted
numbers would need restating.

**Rejected alternatives.** **W1** fixes one cell and leaves the scope question open.
**W3** (scope-split, stored != sent) contradicts *"stored verbatim"*, invents an
ingest normalisation step no document requires, and leaves a stored `/thread/14`
unable to identify its own source without joining `source_id` -- it formalises the
divergence rather than removing it. **W4** removes the contradiction by deleting the
only pointer to what the field holds.

### Impact

**Documentation-only.** No code references `Artifact`. Phase-1 (38 tests) and
Phase-4 (41 tests) touch neither `DATA_MODEL.md` §2 nor payload shape. Phase 5's
construction is unaffected -- the scraper emits the contract's value under SD-023
regardless.

### What this decision does NOT do

- It does **not** resolve **A3**, counterparty identifier attribution -- the one
  remaining freeze blocker.
- It does **not** edit `DATA_MODEL.md`. That happens at freeze.
- It does **not** re-open SD-014, which is confirmed rather than amended.
- It does **not** decide whether §3's scoring weights should eventually **move** to
  GOTHAMITE, or whether `DATA_MODEL.md` should split into a sandbox-owned seed-data
  document and a descriptive GOTHAMITE appendix. W2 defuses those without answering
  them; see residuals.

### Residual items

1. **Whether §3's scoring weights belong in this repository at all** once GOTHAMITE
   exists. W2 marks them descriptive; it does not relocate them.
2. **Whether `DATA_MODEL.md` should eventually split** into a sandbox-owned seed-data
   document and a descriptive GOTHAMITE-model appendix. Larger than A1; not proposed.
3. **Other §2 fields that may diverge from the wire later** -- `Persona.first_seen`,
   `last_seen`, `post_count` under SD-021's profile rules. W2's scope sentence means
   any future divergence is resolved by the contract without another blocker.

**Affected documents if adopted:** `AgentsDocs/DATA_MODEL.md` §2 (scope sentence) and
its `Artifact.url` row. Nothing else.

**Affected documents now:** this entry,
`AgentsDocs/reports/A1_DECISION_BRIEF.md`, and
`AgentsDocs/reports/CONSOLIDATED_FREEZE_REVIEW.md` (A1 reclassified).

---

## SD-027 - Counterparty identifier attribution: remove the reference from the corpus -- **IN FORCE**

> **STATUS: IN FORCE.** Adopted at the contract freeze of 2026-09-07. The
> specification amendments this decision called for have been **applied** to the
> documents named below. This entry is now a record of a decision that governs, not a
> proposal awaiting one.
>
> **Adoption is not counterparty agreement.** No GOTHAMITE repository exists to have
> agreed to anything; the recorded architecture is to finalise the contract first and
> implement GOTHAMITE against it. Absence of objection is not assent, and this file
> makes no claim that implementation compatibility has been established.

**Resolves:** freeze blocker **A3** -- the last one.
**Kind:** Human architectural decision, 2026-09-07.
**Analysis:** `AgentsDocs/reports/A3_DECISION_BRIEF.md`.

**Question.** A spec-conformant scraper extracts A2's wallet from D1's listing 44,
`Identifier.persona_id` is a required FK so it attaches to D1, and *"Identical wallet
address | 0.45"* clears the 0.30 threshold -- producing a `same_actor_suspected` edge
between D1 and A2 that `DATA_MODEL.md` §4 forbids in bold.

### Chosen decision -- T5: remove A2's wallet from the corpus

Listing 44 on `marketplace-beta` no longer references A2's wallet. With no
cross-persona identifier anywhere in the corpus, the false edge cannot arise.

**Chosen over T2 (observational `persona_id` plus a corroboration rule), T1
(ownership-marked identifiers), and T4 (accept the edge and amend §4).** The
consequences below were presented and the decision was confirmed with them stated.

### Amendment tasks -- six files, none yet touched

| # | File | Change |
|---|---|---|
| 1 | `mock_sites/seed_data.py` | Listing 44's body rewritten to remove `WALLET_A` and the "theirs, not mine" disclaimer |
| 2 | `AgentsDocs/MOCK_SITES_SPEC.md` §5 | Delete the D1 requirement: *"at least one post referencing A2's wallet as a counterparty, phrased as a transaction, not as its own address"* |
| 3 | `AgentsDocs/DATA_MODEL.md` §4, Actor D | Remove *"Transacts with A2's wallet. Creates a `transacted_with` edge only."* and the accompanying rationale |
| 4 | `AgentsDocs/DATA_MODEL.md` §4, summary table | Remove the `D1 → A2 | transacted_with` row |
| 5 | `tests/test_phase4.py` | Delete `test_d1_names_a2_wallet_as_a_counterparty_not_its_own`; the suite goes **41 → 40** |
| 6 | `AgentsDocs/reports/PHASE_4_REPORT.md` | Re-run Phase 4 and re-report; the planted-links table loses its D1 row |

Tasks 3 and 4 are required, not optional: removing the wallet reference removes the
**only evidence** that D1 and A2 transacted, so §4's `transacted_with` claim becomes
unachievable and must be withdrawn with it.

### Recorded consequences

- **The demo drops from four seed scenarios to three.** A1 ↔ A2 (0.95), B1 → B2
  (0.60) and the C1 rejection are unaffected. `DATA_MODEL.md` §4's closing line --
  *"Four personas linked, one correctly rejected, one interaction edge. That is the
  demo."* -- will need restating.
- **Actor D is repurposed, not stranded.** §4 gave it as *"Shows the system
  distinguishing interaction from identity."* That scenario is withdrawn. **Amended
  2026-09-07 -- see the R2 addendum below**: D1 is retained as a **co-location
  negative control** rather than dropped from the demo.
- **A closed phase is reopened.** Phase 4 was accepted with 41/41 tests and Docker
  verification; task 5 deletes a passing test and task 1 changes verified content.
  Phase 4 must be re-verified after the edit.
- **The root ambiguity is not resolved -- it becomes dormant.**
  `DATA_MODEL.md` §2's `persona_id` remains undefined between *"belongs to"* and
  *"was observed on an artifact of"*. T5 removes the only corpus content that
  exercises it. **If any future page carries an identifier belonging to another
  persona, the same false edge returns**, with no rule in place to prevent it.

### Addendum, 2026-09-07 -- R2: D1 retained as a co-location negative control

**Human decision, recorded after T5 was chosen.** D1 is **not** dropped from the
demo. It is retained with a different purpose:

> **D1 (`bellwether`) is a co-location negative control.** It shares a site with A2
> (`marketplace-beta`) and its activity window (`2026-02-01` to `2026-08-19`)
> overlaps A2's (`2026-02-14` to `2026-08-22`), yet the two share **no identifier**.
> Same venue plus overlapping activity must produce **no `same_actor_suspected`
> edge**.

**Why this is a distinct scenario and not a duplicate of C1.** C1 (`nightjarr`)
tests that a *similar handle* is not the same actor -- and handle similarity is a
**scored** signal in §3, worth 0.05, on a different site from A1. D1 tests a case
§3 has **no signal for at all**: co-location and temporal overlap. Those are the
circumstances most likely to tempt an inference the model cannot support, and
nothing else in the corpus exercises them.

**Cost: none beyond T5's existing tasks.** Post-T5 D1 automatically shares nothing
with anyone. No new seed value, no new persona, no new post is required. D1 keeps
its eight posts, its own PGP fingerprint, and its own wallet on listings 43 and 45
-- the identifiers are what make the negative result meaningful, since a persona
with no identifiers would demonstrate nothing.

**Effect on the amendment tasks above:**

| Task | Revised |
|---|---|
| 2 | `MOCK_SITES_SPEC.md` §5: the D1 counterparty requirement is **replaced**, not merely deleted -- D1's requirement becomes co-location with A2, an overlapping window, and no shared identifier |
| 3 | `DATA_MODEL.md` §4, Actor D: the `transacted_with` text is **replaced** by the co-location negative control, not removed outright |
| 4 | Unchanged -- the `D1 -> A2 | transacted_with` summary row is still removed. D1 produces **no** edge |
| 5 | One test deleted (41 -> 40), one added: `test_d1_and_a2_are_co_located_and_share_no_identifier` (-> 41). Whether it partially overlaps the existing `test_no_unintended_identifier_sharing` is to be confirmed at implementation |
| 6 | `PHASE_4_REPORT.md`: the planted-links table gains a D1 **negative** row instead of losing its D1 row |

**What R2 does not restore.** `transacted_with` was the only *positive non-identity*
relationship the model could demonstrate. R2 is a negative scenario. After T5,
`Relationship.type` carries three values and **one** is exercised by any seed
scenario. That is residual 3 below, unchanged.

**Demo shape after T5 + R2:** A1 <-> A2 linked (0.95), B1 -> B2 linked (0.60), C1
correctly rejected on handle similarity, D1 correctly rejected on co-location.
**Two positive links and two distinct rejections** -- §4's closing line still needs
restating, but the demo is four scenarios, not three.

### Interaction with other decisions

| Decision | Effect |
|---|---|
| **SD-015** | Unaffected. The canonical A1/A2 wallet is unchanged; it simply stops appearing on D1's page. Its four other occurrences stand |
| **SD-018** | Unaffected -- B1/B2 timing untouched |
| **SD-021** | Unaffected. Listing 44 remains an `item` artifact with a persona and an `observed_at` |
| **SD-022.4** | **Left asymmetric.** SD-022.4 governs mentioned *handles* by rule -- they are not attributed to the author's persona. Mentioned *wallets* are now governed by absence: none exists in the corpus. Two different principles for the same class of problem |
| **SD-023 / SD-024 / SD-025 / SD-026** | Unaffected |

### What this decision does NOT do

- It does **not** edit any file. All six tasks are deferred to freeze.
- It does **not** define `Identifier.persona_id`, and does not establish any rule for
  counterparty identifiers.
- It does **not** address how a `transacted_with` edge is produced -- see residual 2.

### Residual items

1. **`Identifier.persona_id` remains undefined** between ownership and observation
   (`A3_DECISION_BRIEF.md` §2.1). Dormant, not resolved.
2. **No document defines how a `transacted_with` edge is produced.**
   `DATA_MODEL.md` §3 has no signal for it and `Evidence.signal_type`'s enum has no
   value for it (`A3_DECISION_BRIEF.md` §2.2). After task 4 the enum value
   `transacted_with` becomes unused, alongside `trusts`.
3. **`Evidence.signal_type` and `Relationship.type` now carry values nothing
   produces.** Comparable to the reserved `handle` and `contact` identifier types
   under SD-022.3; no narrowing is proposed.
4. **A future counterparty reference reintroduces the problem** (see consequences).
   No guard exists -- neither a rule nor a test -- to catch one being added.
5. **SD-022.4's handle rule is now the only stated attribution principle**, covering
   one identifier type out of four.

**Affected documents if adopted:** the six above.
**Affected documents now:** this entry, `AgentsDocs/reports/A3_DECISION_BRIEF.md`, and
`AgentsDocs/reports/CONSOLIDATED_FREEZE_REVIEW.md` (A3 reclassified).

---

## SD-028 - `Identifier.persona_id` means ownership; no page carries another persona's identifier -- **IN FORCE**

> **STATUS: IN FORCE.** Adopted at the contract freeze of 2026-09-07. The
> specification amendments this decision called for have been **applied** to the
> documents named below. This entry is now a record of a decision that governs, not a
> proposal awaiting one.
>
> **Adoption is not counterparty agreement.** No GOTHAMITE repository exists to have
> agreed to anything; the recorded architecture is to finalise the contract first and
> implement GOTHAMITE against it. Absence of objection is not assent, and this file
> makes no claim that implementation compatibility has been established.

**Kind:** Human architectural decision, 2026-09-07.
**Relationship to SD-027:** SD-028 is **separate**. SD-027 removed the one corpus
item that exercised the ambiguity; SD-028 defines the field and adds the guard that
keeps it removed. SD-027's residual 1 (`persona_id` undefined) and residual 4 (no
guard against reintroduction) are the items this entry addresses.

**Question.** `DATA_MODEL.md` §2 lists `Identifier.persona_id` as a required FK with
**no gloss**, while the adjacent `artifact_id` is glossed *"FR -> Artifact -- where it
was seen"*. The field is therefore undefined between two readings: *"this identifier
belongs to this persona"* and *"this identifier was observed on an artifact of this
persona"*. Under the second reading a counterparty address attaches to the wrong
persona and scores 0.45 as an identity signal -- which is how A3 arose.

### Chosen decision

**A. `persona_id` means attribution, i.e. ownership.**

`DATA_MODEL.md` §2, Identifier table -- the `persona_id` row's note becomes:

```
FK -> Persona -- the persona this identifier is **attributed to**: asserted to
belong to them. Not "seen on their page"
```

**B. A scope note immediately after the Identifier table:**

> **Attribution, not observation.** Every identifier is attributed to exactly one
> persona and asserts ownership. This model has no representation for an identifier
> merely *observed* on a persona's artifact without being theirs -- a counterparty
> address quoted in a transaction, say. Corpus content requiring that distinction is
> excluded (SD-027). An observational relationship -- a role marker on
> `identifiers[]`, or a separate observation entity -- is **future GOTHAMITE
> architecture** and is out of scope here.

**C. The corpus invariant, as a normative rule.**

`MOCK_SITES_SPEC.md` §2 gains hard content rule **6**:

> 6. **No page carries a PGP fingerprint or wallet address belonging to another
>    persona.** Every emitted PGP fingerprint and wallet address belongs to that
>    page's author. This is what makes attribution sound
>    (`DATA_MODEL.md` §2, Identifier).

**D. A guard test.**

`tests/test_phase4.py` gains `test_no_page_carries_another_personas_identifier`,
crawling every rendered page and asserting that each PGP fingerprint and wallet
address found belongs to that page's author. This is the assertion that would have
caught listing 44 when it was written.

### Why the guard is the load-bearing half

Defining `persona_id` as ownership **converts SD-027's one-off corpus edit into a
standing invariant**. Before SD-028, a counterparty identifier produced an ambiguous
row. After it, emitting one is a **false assertion of ownership** -- strictly worse.
The wording in A and B is only sound while C holds.

Note the asymmetry, which decides where the weight sits. Under **SD-026**,
`DATA_MODEL.md` §2 is **descriptive and non-normative for GOTHAMITE** -- so A and B
describe an expected representation that GOTHAMITE is not bound by.
`MOCK_SITES_SPEC.md` and the corpus are **sandbox-owned and normative**. The rule in
C and the test in D are the parts that actually hold, and they hold regardless of
what GOTHAMITE decides.

### Consistency with SD-022.4

SD-027's interaction table recorded that T5 left SD-022.4 **asymmetric**: mentioned
*handles* were governed by a rule, mentioned *wallets* only by absence. SD-028
removes that asymmetry -- rule 6 governs PGP fingerprints and wallets by rule, so no
identifier of any type appears off-owner. The two principles are now stated in two
places (`SD-022.4` for handles, rule 6 for PGP and wallets); unifying them into a
single attribution principle is possible but is not proposed here.

### Amendment tasks -- three files, none yet touched

| # | File | Change |
|---|---|---|
| 1 | `AgentsDocs/DATA_MODEL.md` §2 | `Identifier.persona_id` note (A) |
| 2 | `AgentsDocs/DATA_MODEL.md` §2 | Scope note after the Identifier table (B) |
| 3 | `AgentsDocs/MOCK_SITES_SPEC.md` §2 | New hard content rule 6 (C) |
| 4 | `tests/test_phase4.py` | New `test_no_page_carries_another_personas_identifier` (D) |

`SCRAPER_AGENT_SPEC.md` needs **no** change: the scraper's extraction behaviour is
unchanged, and the guarantee moves to the corpus. `API_CONTRACT.md` needs no change:
the ingest payload's `identifiers[]` carries only `type`, `value` and `observed_at` --
`persona_id` is assigned GOTHAMITE-side and never appears on the wire.

### Test-count arithmetic across SD-027 and SD-028

41 (accepted Phase 4) -> **40** (SD-027 deletes the counterparty test) -> **41**
(SD-027/R2 adds the co-location control test) -> **42** (SD-028 adds the guard).
Phase 4 must be re-verified after the combined edit.

### What this decision does NOT do

- It does **not** edit any file. All four tasks are deferred to freeze.
- It does **not** define an observational representation, or add a role marker to
  `identifiers[]`. That is explicitly deferred to GOTHAMITE.
- It does **not** narrow `Relationship.type` or `Evidence.signal_type`, and does not
  supply a production rule for `transacted_with` -- SD-027 residuals 2 and 3 stand.
- It does **not** claim GOTHAMITE has agreed to anything. Per SD-026, §2 is
  descriptive for GOTHAMITE; a future GOTHAMITE may model identifiers observationally
  provided it does not attribute a counterparty identifier as an identity signal.

### Residual items

1. **Two attribution principles, not one** -- SD-022.4 for handles, rule 6 for PGP
   and wallets. Consistent, but not unified.
2. **The guard covers PGP fingerprints and wallets only.** `handle` and `contact`
   remain reserved and unemitted under SD-022, so nothing is unguarded today; if
   either is ever emitted, rule 6 would need extending.
3. **An observational model is deferred, not designed.** If GOTHAMITE later needs
   counterparty evidence, the sandbox corpus cannot currently supply it -- adding it
   would require reopening SD-027 and rule 6 together.

**Affected documents if adopted:** the four above.
**Affected documents now:** this entry and the SD-027 R2 addendum.

---

## SD-029 - Plaintext fallback response body (B4/P3) -- **IN FORCE**

> **STATUS: IN FORCE. Adopted 2026-09-08.**
> `RELAY_PROTOCOL.md` §9.3 defines the fallback body, `relay/relay_node.py` returns
> exactly it, `client/onion_client.py` classifies it as a protocol error
> (`OnionRelayError`, `sealed=False`), and `tests/test_phase1.py` covers status,
> content type, field set, values, absence of diagnostics, the one-hop rule and the
> predecessor's conversion.
>
> Verified before adoption: Phase 1 **61/61**, Phase 4 **42/42**, combined **103/103**.
> The order was decision → specification → implementation → verification → adoption;
> adoption was a human act and was not inferred from the tests passing.
>
> The decision wording below is unchanged from the reviewed proposal.

**Kind:** Human architectural decision, 2026-09-07.
**Relates to:** OPEN-9. **Closes:** SD-024 residual 1, and freeze-review item **B4**.
**Analysis:** `AgentsDocs/reports/B4_DECISION_BRIEF.md`.

**Question.** SD-024 §E retains a plaintext non-2xx response for the one case where a
relay cannot seal, but defines only its **status**, not its **body**. §A defers to
SD-011, whose recorded form is `{"error": "<code>", "reported_by": ...}` -- so the
reading was that a code is carried, but SD-024 never said so.

### When this response occurs -- the one case

Only when a relay **could not decrypt its own layer**, holds no key, and therefore
cannot seal anything for its predecessor. Every other failure -- next hop unreachable,
destination unreachable, hop timeout -- leaves the relay holding `K`, and SD-024 §A
requires it to seal.

Three structural consequences follow, and they decide the rest:

1. **It travels exactly one hop.** It is read by the emitting relay's immediate
   predecessor, or by the client directly when the *entry* relay is the one that
   failed. **It is never forwarded as protocol content.** A predecessor receiving it
   emits its own sealed error; it does not relay the plaintext onward.
2. **The emitting relay has nothing to leak.** It failed before parsing `next_hop`, so
   it does not know its successor, the destination, or its position in the path.
3. **Only one cause can produce it**, which decides the permitted code set below.

### Chosen decision -- P3

**Transport: HTTP `400 Bad Request`.** A single status. From this relay's position the
sender supplied a layer it cannot open, which is a defect in the request as received.
`502` belongs to `next_hop_unreachable`, which cannot occur here. The status carries
**no protocol meaning** -- it signals only that no envelope is coming.

**Body, exactly two fields, both required, both strings, `Content-Type:
application/json`:**

```json
{ "error": "decryption_failure", "reported_by": "<own relay_id>" }
```

**`decryption_failure` is the only permitted plaintext-fallback value.** Not a subset
chosen for tidiness -- the other two §C codes are unreachable here, because a relay
experiencing either holds `K` and seals instead.

This is what dissolves the objection to carrying a code in an unsealed channel: **the
plaintext code has a domain of size one**, so there is no case in which a plaintext
code and a sealed code could disagree. The two-sources-of-truth risk §E guards against
does not arise.

Note the spelling change: the current build emits `layer_undecryptable`, which is not
a §C value. Adoption makes it `decryption_failure`.

### What must NOT be exposed

No downstream relay identity; no destination host or port; no path information or hop
index; no `request_id` (SD-003); no decryption diagnostics, exception text, or
distinction between a failed RSA unwrap and a failed GCM tag; no key material, nonces,
ciphertext, or plaintext byte lengths.

The current build already satisfies this -- it logs the exception locally
(`relay_node.py:119`) and returns only the fixed code and its own id. That behaviour
is kept.

### `reported_by` and the predecessor's translation

`reported_by` names the emitting relay itself, which SD-011 expressly permits: *"a
relay may identify itself as the reporter."* The recipient already knows that identity
-- it just sent to it.

A predecessor receiving the fallback emits its own **sealed** error,
`{"type": "error", "code": "decryption_failure", "reported_by": "<its own id>"}`. That
reads like misattribution until checked against SD-024 §D, which defines `reported_by`
as *"the last relay that successfully processed the request and is reporting the
failure"* -- the **reporter**, never the **failer**. The translation is exact and
requires no change to §D.

This is the single adjacency SD-024 §J narrows SD-011's rewriting rule to.

### What is unchanged

- **SD-024's sealed error semantics are untouched.** §A's sealing rule, §B/D2's typed
  inner plaintext, §D's `reported_by` definition, §F, §G, §H, §I and §J all stand as
  written.
- **SD-024 §C is not amended.** §C governs the field **`code`**; the plaintext body's
  field is **`error`**. The closed set of three is neither widened nor narrowed by
  this decision.
- **No cryptographic primitive and no transport mechanism changes.** The fallback is
  by definition the case where no sealing occurs; §5.1-5.3, §7's nonce rule and
  SD-001's `POST /relay` are all untouched.
- **SD-011 is satisfied, not narrowed further.**

### Implementation and test consequences -- none yet performed

- `relay/relay_node.py:125` -- the code string becomes `decryption_failure`.
- `client/onion_client.py:264` already reads `error` and `reported_by` in this exact
  shape. **No client change is required.**
- **Survives unchanged:** `test_garbage_envelope_is_refused_with_400`
  (`tests/test_phase1.py:488`) -- feeding a relay garbage *is* this case, and its
  `assertEqual(status, 400)` holds.
- **New tests:** the body has exactly two keys; it contains no exception text; a
  predecessor converts it into a sealed error naming itself; that sealed error does
  not name the relay that failed to decrypt; an entry-relay fallback reaches the
  client as `OnionPathError` classified as a **protocol error**, not a client-side
  condition. Log-hygiene coverage extends over this branch.

**Affected documents if adopted:** `AgentsDocs/RELAY_PROTOCOL.md` §9.3; this file's
SD-024 §E.

---

## SD-030 - `unusable_layer`: a fourth closed protocol error code -- **IN FORCE**

> **STATUS: IN FORCE. Adopted 2026-09-08.**
> `RELAY_PROTOCOL.md` §9.1 declares the closed set of four and §6 makes the validation
> boundary explicit; `relay/relay_node.py` seals `unusable_layer` with HTTP 200, keeps
> `K` rather than discarding it, and no longer emits `layer_malformed`;
> `tests/test_phase1.py` covers both triggers, the status, the exact field set, the
> absence of diagnostics, and that an intermediate relay cannot read the sealed error.
>
> **SD-024 §C's closed set is amended accordingly**, and §9.1 matches it.
>
> Verified before adoption: Phase 1 **61/61**, Phase 4 **42/42**, combined **103/103**.
> The decision wording below is unchanged from the reviewed proposal.

**Kind:** Human architectural decision, 2026-09-07.
**Relates to:** OPEN-9. **Amends:** SD-024 §C. **Builds on:** SD-029.
**Analysis:** `AgentsDocs/reports/LAYER_MALFORMED_DECISION_BRIEF.md`.

**Question.** A relay that successfully decrypts and authenticates its own layer, then
finds it structurally unusable, must seal under §A -- it holds `K`. §C's closed set has
no fitting value: it did not fail to decrypt, reached no next hop, contacted no
destination. The condition was undefined.

### The condition, exactly

`open_layer` (`common/onion_crypto.py:186`) already validates base64 fields, nonce
length, the RSA unwrap, **the AES-GCM tag**, the JSON parse, `isinstance(dict)`, and
the presence of all four required fields. Each raises `EnvelopeError` and is a
**decryption failure** -- SD-029's case, not this one.

This condition occurs **only** at the validation boundary immediately after:
**`next_port` cannot be coerced to an integer, or `payload` cannot be decoded as
base64.** Nothing else reaches it; the `KeyError` arm at `relay_node.py:131` is dead
code, field presence being already guaranteed.

**The layer is authenticated when this fires.** AES-GCM is an AEAD and the tag check
passed, so the plaintext came from whoever holds `K` -- the client. Tampering fails the
tag and takes SD-029's path. **This is a client construction fault, never
attacker-injected.**

### Chosen decision -- M1

**`unusable_layer` is added to SD-024 §C as a fourth closed error code.**

**The relay holds `K` and MUST seal**, per §A/E2 -- no exception, no discarding of the
key to avoid it.

**Transport: HTTP 200**, per §E's first bullet -- a sealed envelope is returned. This
is a change from the current build's `400`.

```json
{ "type": "error", "code": "unusable_layer", "reported_by": "<detecting relay>" }
```

**`reported_by`** is the relay detecting the condition -- exact under §D: it
successfully processed the request as far as decrypting and authenticating its own
layer, and is the party reporting. No downstream identity exists to leak; it never
resolved `next_hop` into a forwarding attempt.

**No diagnostics on the wire:** not the field name, its value, the exception text,
byte lengths, or `request_id` (SD-003). Diagnosis belongs in the relay's own log (§8).

### Naming -- `unusable_layer`, deliberately not `malformed_layer`

§C already states **`malformed_response` is NOT a protocol error code**, because no
relay parses relayed content. `malformed_layer` sits one word from that exclusion and
would be misread as contradicting it. The distinction is load-bearing: the exclusion
concerns **relayed content**, which a relay must never parse; this concerns a relay's
**own layer**, which the protocol obliges it to parse. `unusable_layer` keeps them
lexically apart.

### Rejected alternatives

- **Map to `decryption_failure`** -- inaccurate; decryption succeeded and the tag
  proved it. It would also give that code two meanings immediately after SD-029
  established it as the single value meaning "I could not decrypt", carried unsealed
  precisely because the relay holds no key.
- **Use `malformed_layer`** -- the naming collision above.
- **Treat as `malformed_response`** -- misreads §C's exclusion, and gives the relay no
  wire behaviour at all. The client cannot detect this: it built the layer and
  believes it correct.
- **Use SD-029's plaintext fallback** -- contradicts §A/E2. The relay holds `K`.
- **Tighten `open_layer` so the branch cannot exist** -- reaches the outcome by
  deliberately discarding a held key so E2 stops applying, and collapses "wrong key or
  tampering" into "right key, bad content" at the layer where the distinction is
  cheapest to keep.

### What is unchanged

- **No cryptographic primitive.** AES-GCM parameters, RSA-OAEP delivery, the
  fresh-nonce rule (§7, §H, §9.5). `common/onion_crypto.py` needs no change.
- **No transport mechanism.** SD-001's `POST /relay` per hop stands.
- **No existing error code changes meaning.** The three original values keep their
  definitions and their §9 bullet mappings exactly.
- **§B/D2 is untouched.** The sealed object keeps its existing
  `{type, code, reported_by}` shape -- no new field, no new type. Intermediate relays
  still forward opaquely and never parse.
- **§D, §E, §F, §G, §H, §I, §J untouched.** HTTP 200 and the `reported_by` definition
  both follow from §E and §D as already written.
- **SD-029 is untouched.** The unsealed fallback remains HTTP 400 carrying only
  `decryption_failure`, reachable only when the relay holds no key. SD-030 adds
  nothing to the plaintext channel, so SD-029's single-value property survives intact.
- **SD-024 residual 3 is not contradicted.** *"Malformed responses remain permanently
  uncodeable"* concerns a **successor's response** -- relayed content. This concerns a
  relay's **own layer**. Residual 3 stays open, unchanged.
- **SD-011 is satisfied.** `reported_by` is the emitting relay's own id, never a
  downstream one.

### Recorded consequences

- **The current build is wrong on two counts** at `relay_node.py:137`: plaintext where
  it must seal, `400` where it must return `200`. Both are pre-SD-024 defaults, not
  deviations from a decision that existed at the time.
- **`unusable_layer` maps to no §9 bullet.** Bullets 1, 2 and 4 map to the three
  original codes; §9 never contemplated this case. That absence is the gap.
- **Defensively reachable only.** Our own client builds the layers, so in practice
  this fires on a client bug or a compromised client. It is specified because
  `RELAY_PROTOCOL.md` governs any implementation, and "undefined" is the one answer a
  protocol document should not give.
- **Not a denial-of-service surface, and no decryption-oracle risk.** The branch is
  unreachable without `K`: reaching it already requires having succeeded at decryption.
- **This is the first widening of anything in the 2026-09-07 freeze.** Recorded as such
  rather than absorbed quietly.

### Implementation and test consequences -- none yet performed

- `relay/relay_node.py:136-137` -- stop discarding `session_key`; seal instead of
  returning plaintext; status `200`; code `unusable_layer`.
- `client/onion_client.py` -- no new handling beyond the typed-error parsing OPEN-9
  already requires.
- `common/onion_crypto.py` -- **no change.**
- **New tests:** non-integer `next_port` yields a sealed error the client can open, not
  a plaintext 400; non-base64 `payload` yields the same; status is **200**, asserted
  directly; `reported_by` is the detecting relay; an intermediate relay **cannot read**
  that sealed error; the body carries no field name, value or exception text; a
  **tampered** layer still yields `decryption_failure` via the plaintext fallback --
  the negative control proving the two paths stay separate.

### Residual items

1. **`int()` silently truncates a float `next_port`** (`8080.9` -> `8080`);
   `int(True)` yields `1`. Not protocol questions; to be resolved during OPEN-9
   implementation.
2. **The dead `KeyError` arm** at `relay_node.py:131` should be removed, or retained
   with `open_layer`'s field-presence check cited as the reason it cannot fire.

**Affected documents if adopted:** `AgentsDocs/RELAY_PROTOCOL.md` §6 and §9.1; this
file's SD-024 §C.

---

## 2. Blockers deliberately NOT resolved here

These were found by the audit, are **not** Phase-1 blockers, and are **not** decided
above. They must be answered by a human before the phase that needs them.

| ID | Issue | Blocks |
|---|---|---|
| ~~**OPEN-1**~~ **RESOLVED** | `AgentsDocs/DATA_MODEL.md` declares `Repo: GOTHAMITE` in its own header, while every other document refers to "GOTHAMITE `docs/DATA_MODEL.md`" as a file in a different repository. Whether the local copy is authoritative, synchronised, or stale is unknown. — **Closed 2026-09-07 by SD-014:** the two files govern different scopes; sandbox seed data is owned here, GOTHAMITE's ingestion representation is owned there, compatible at the `API_CONTRACT.md` boundary. | ~~Phase 4, Phase 5~~ |
| ~~**OPEN-2**~~ **RESOLVED** | `README.md` §4 gives persona A1's wallet as a bech32 address; `AgentsDocs/DATA_MODEL.md` §4 and `AgentsDocs/API_CONTRACT.md` §3 give a base58 address for the same persona. The two disagree, the scraper regex in `SCRAPER_AGENT_SPEC.md` §4 can only match the base58 form, and `MOCK_SITES_SPEC.md` §2 rule 5 requires the seed values character-exact. — **Closed 2026-09-07 by SD-015:** canonical value is the base58 `1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6`; README was stale and is corrected; no bech32, no mixed-format extractor. | ~~Phase 4, Phase 5~~ |
| ~~**OPEN-3**~~ **RESOLVED** | `IMPLEMENTATION_PLAN.md` Phase 4 acceptance 4 requires decoy person**as** (plural); `DATA_MODEL.md` §4 specifies exactly one (C1 `nightjarr`). Inventing more would violate the determinism rule. - **Closed 2026-09-07 by SD-016:** exactly one decoy, resolved from the existing specification; no product decision was needed. | ~~Phase 4~~ |
| ~~**OPEN-4**~~ **RESOLVED** | `API_CONTRACT.md` §3 marks `persona.handle` required, but the crawl structure in `SCRAPER_AGENT_SPEC.md` §3 includes index pages, which have no single author. **Scope correction 2026-09-07:** profile pages are a second, distinct case -- they have an unambiguous persona but no single post timestamp, so `persona.observed_at` is equally unsatisfiable there. **SD-021 proposes** a `page_type` discriminator, extended 2026-09-07 by **SD-021.1** (`page_type` required, closed enum, no default) and **SD-021.2** (`identifiers[].observed_at` required for every identifier that exists, no surrogate timestamps). **Closed 2026-09-07 at contract freeze:** `API_CONTRACT.md` §3 now carries `page_type` as a required, closed-enum, no-default field with the persona matrix, and `SCRAPER_AGENT_SPEC.md` §3 carries the structural page-type mapping. SD-021 is **IN FORCE**. Adoption is not GOTHAMITE agreement -- no counterparty exists; the contract was finalised first by design. | ~~Phase 5~~ |
| ~~**OPEN-5**~~ **RESOLVED** | Whether `handle` and `contact` are ever emitted as `identifiers[]` entries, and how `contact` is extracted and normalised. **SD-022 records the human decision** -- H1 (handle never emitted) and C1 (contact reserved, not extracted), enum not narrowed, mentioned handles out of scope. **Closed 2026-09-07 at contract freeze:** `API_CONTRACT.md` §3 states that Phase 5 emits `pgp_fingerprint` and `wallet` only, with `handle` and `contact` reserved, and `SCRAPER_AGENT_SPEC.md` §4 states the same rule where extraction is defined. SD-022 is **IN FORCE**. | ~~Phase 5~~ |
| ~~**OPEN-6**~~ **RESOLVED** | Whether `url` in the ingest payload includes a scheme. **SD-023 records the human decision** -- U2, a canonical absolute HTTP URL, `http://<mock-host>/<path>`. **Closed 2026-09-07 at contract freeze:** `API_CONTRACT.md` §3 carries the seven `url` rules including the required scheme and the index page's trailing slash. The `DATA_MODEL.md` contradiction is **resolved, not preserved**: SD-026 corrected `Artifact.url` to the absolute URL and scope-marked §2/§3 as descriptive. SD-023 is **IN FORCE**. | ~~Phase 5~~ |
| ~~**OPEN-7**~~ **RESOLVED** | Timezone handling for mock-site post timestamps. - **Closed 2026-09-07 by SD-017:** ISO 8601, UTC, `Z` suffix, following `API_CONTRACT.md` §3. | ~~Phase 4, Phase 5~~ |
| **OPEN-8** | `IMPLEMENTATION_PLAN.md` Phase 4's first acceptance criterion requires a full relay path, contradicting Phase 4's documented independence from the relay work. Resolved in practice by SD-000 — the relay chain now exists before Phase 4 — but the sequencing note in `format/AGENT_TASK_SPLIT.md` §4 is still inconsistent. | Phase 4 gate |
| ~~**OPEN-9**~~ **RESOLVED** | **The error envelope is unspecified.** `RELAY_PROTOCOL.md` §5.2 defines the forward wire layer and §7 defines the return path, but neither defines what an *error* looks like on the wire. §9 says only "return an error" for three of its four cases, while the fourth — mock site unreachable — says the exit relay "returns an error response **through the normal return path**", which implies a sealed envelope for that case alone. The current Phase-1 build returns plaintext JSON with a non-2xx status at every hop, which deviates from that fourth bullet. Needs a human protocol decision: does an error travel sealed under the return-path layers, as a plaintext status, or sealed in some cases and plaintext in others — and if sealed, how does the client distinguish an error from a successful response before decrypting? SD-011's relay-identity invariant holds under any of those answers. **SD-024 records the human decision** -- E2 uniform layered sealing plus D2 typed inner plaintext, a closed error-code set, and HTTP status demoted to transport-only. — **CLOSED 2026-09-08.** **SD-029** (plaintext fallback body) and **SD-030** (`unusable_layer`, the fourth closed code) are both **IN FORCE**. Specification, implementation and tests agree: `RELAY_PROTOCOL.md` §§6, 7 and 9.1-9.5 define the typed sealed protocol; `relay/relay_node.py` seals typed responses and errors; `client/onion_client.py` branches on the sealed `type` and classifies the four outcomes of §9.2. **All seven required test areas of `CONSOLIDATED_FREEZE_REVIEW.md` §11 are covered** -- sealed errors opened at hops 2 through 5, a relay unable to read its successor's sealed error, the detecting relay named and the failed one never named, malformed responses classified client-side, a destination 404 carried as an application success, nonce discipline across error layers, and log hygiene on the error path. Verified at Phase 1 **61/61**, Phase 4 **42/42**, combined **103/103**. | ~~Phase 2 onward; revisit before Phase 6 hardening~~ |

---

## 3. Decision log

| ID | Subject | Kind |
|---|---|---|
| SD-000 | Phase 1 scope | Human product decision |
| SD-001 | Relay transport | Inferred from specs |
| SD-002 | Response wire envelope | Inferred from specs |
| SD-003 | `request_id` | Inferred from specs |
| SD-004 | Directory ownership | Already specified |
| SD-005 | Framework and dependencies | Inferred from specs |
| SD-006 | Ports | Inferred from spec examples |
| SD-007 | `.onion.mock` resolution | Inferred from specs |
| SD-008 | Shared crypto module | Inferred from specs |
| SD-009 | Relay pool size | Narrowed a documented range |
| SD-010 | `sandbox-net` | Reconciled a contradiction |
| SD-011 | Failure propagation (relay identity only; envelope form deferred to OPEN-9) | **Resolved a real tension — approved in principle** |
| SD-012 | Phase-1 static endpoint | Filled a documented gap |
| SD-013 | Report directory name | Corrected a stale path |
| SD-014 | Data-model authority boundary (closes OPEN-1) | **Human product decision** |
| SD-015 | Canonical A1/A2 wallet, base58 (closes OPEN-2) | **Human product decision** |
| SD-016 | One decoy persona (closes OPEN-3) | Resolved from the specs |
| SD-017 | Timestamps are UTC with `Z` (closes OPEN-7) | Resolved from the specs |
| SD-018 | B1/B2 boundary dates, 17-day gap | Reconciled a contradiction |
| SD-019 | Mock sites emit no `Date` header | Filled a documented gap |
| SD-020 | `mock_sites/` directory name | Corrected an unusable path |
| SD-021 | Artifact `page_type` discriminator, incl. SD-021.1 (`page_type` required, no default) and SD-021.2 (`identifiers[].observed_at` required, no substitution) -- closes OPEN-4 | **IN FORCE** - adopted at the 2026-09-07 freeze; adoption is not GOTHAMITE agreement |
| SD-022 | Handle and contact identifier semantics -- H1 (handle never emitted), C1 (contact reserved), enum not narrowed, mentioned handles out of scope -- closes OPEN-5 | **IN FORCE** - adopted at the 2026-09-07 freeze |
| SD-023 | Ingest payload `url` is a canonical absolute HTTP URL (`http://<mock-host>/<path>`) -- closes OPEN-6; the `Artifact.url` contradiction is resolved by SD-026, not preserved | **IN FORCE** - adopted at the 2026-09-07 freeze |
| SD-024 | Relay error transport (E2, uniform layered sealing) and response discriminator (D2, typed inner plaintext); closed code set; HTTP status transport-only; SD-011 preserved -- relates to OPEN-9. §E amended by SD-029, §C by SD-030 | **SPEC AMENDED** - implemented and verified 2026-09-08; §E amended by SD-029 and §C by SD-030, both IN FORCE; residual 3 open; OPEN-9 closed |
| SD-025 | `API_CONTRACT.md` is self-authoritative for the wire format; neither internal model overrides the boundary (O2) -- resolves freeze blocker A2 | **IN FORCE** - adopted at the 2026-09-07 freeze |
| SD-026 | Stored `Artifact.url` corrected to the absolute URL; `DATA_MODEL.md` §2/§3 scope-marked descriptive and non-normative for GOTHAMITE (W2) -- resolves freeze blocker A1 | **IN FORCE** - adopted at the 2026-09-07 freeze |
| SD-027 | Counterparty identifier attribution resolved by removing A2's wallet from D1's listing 44 (T5); Actor D's transaction scenario withdrawn and D1 retained as a co-location negative control (R2, addendum 2026-09-07) -- resolves freeze blocker A3 | **IN FORCE** - adopted at the 2026-09-07 freeze; Phase 4 re-verified 42/42 |
| SD-028 | `Identifier.persona_id` means attribution/ownership; corpus invariant that no page carries another persona's PGP fingerprint or wallet, plus a guard test -- addresses SD-027 residuals 1 and 4 | **IN FORCE** - adopted at the 2026-09-07 freeze; guard test passing |
| SD-029 | Plaintext fallback response body (B4/P3): HTTP 400 with exactly `{"error": "decryption_failure", "reported_by": "<own relay_id>"}`, the only permitted plaintext code; travels one hop, never forwarded; no diagnostics or downstream identity -- amends SD-024 §E, closes its residual 1 and freeze item B4 | **IN FORCE** - adopted 2026-09-08; specification, implementation and tests verified at 103/103 |
| SD-030 | `unusable_layer` added as the fourth closed protocol error code (M1): authenticated decryption followed by an uncoercible `next_port` or undecodable `payload`; the relay holds `K` and MUST seal; HTTP 200 -- amends SD-024 §C only | **IN FORCE** - adopted 2026-09-08; specification, implementation and tests verified at 103/103 |
