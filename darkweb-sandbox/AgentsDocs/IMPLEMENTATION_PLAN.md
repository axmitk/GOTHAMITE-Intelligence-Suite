# IMPLEMENTATION_PLAN.md

**Repo:** `darkweb-sandbox`
**Prerequisites:** `MASTER_CONTEXT.md`, `RELAY_PROTOCOL.md`
**Deadline:** 8 September 2026

---

## 1. The rule

Build proceeds in six phases. **At the end of each phase you stop, write a report, and wait.**

You do not start the next phase because the current one felt finished. You start it when a human replies with an explicit instruction to proceed. Silence is not permission. An encouraging comment is not permission.

**Why this exists:** coding agents given a large scope tend to build broad and shallow — many files, few working paths. By the time that is visible it is usually too late to unwind. Each gate below forces one narrow thing to actually work before the next thing starts.

---

## 2. Time budget

Roughly 3.5 working days remain. This repo is not the graded SIH deliverable — GOTHAMITE is. Budget accordingly.

| Phase | Target | Notes |
|---|---|---|
| 1 | Fri night / Sat AM | Riskiest phase. Crypto correctness |
| 2 | Sat AM | Small |
| 3 | Sat PM | Second riskiest. Multi-hop integration |
| 4 | Sat PM / Sun AM | Parallelisable with 1–3 by a second person |
| 5 | Sun AM | Blocked on GOTHAMITE `DATA_MODEL.md` |
| 6 | Sun PM | Leave real time here. Integration always overruns |

Mock sites (Phase 4) have **no dependency** on the relay work. If two people are building, one starts Phase 4 immediately in parallel rather than waiting for Phase 3.

If a phase runs materially over its target, say so in the report rather than absorbing it silently. Slipping quietly is how the dashboard does not get built.

---

## 3. Phases

### Phase 1 — Single hop, proven crypto

**Build:** one relay node, one mock endpoint, client encrypting a single layer.

**Deliverables**
- `relay/relay_node.py` — keypair at startup, decrypt one layer, act on `next_hop`, encrypt response
- `client/onion_client.py` — build one layer, send, decrypt response
- One trivial mock endpoint (a static page is fine — the real sites come in Phase 4)

**Acceptance** — per `RELAY_PROTOCOL.md` §11, all six items demonstrated.

**Do not build:** the directory, multiple relays, path selection, real mock sites.

---

### Phase 2 — Directory service

**Build:** `directory/directory_service.py` — relay registry and path selection.

**Deliverables**
- Relays self-register at startup: `relay_id`, `host`, `port`, `public_key`, `status`
- `GET /path?hops=N` returns N distinct `up` relays in order, uniform random, no repeats
- `GET /relays` for demo visibility

**Acceptance**
1. 5–7 relays start and register
2. Repeated `/path?hops=3` calls return visibly different paths
3. No relay appears twice in one path
4. A relay marked down is never selected
5. Directory holds **no** private keys

**Do not build:** consensus, voting, weighting, reputation, persistence.

---

### Phase 3 — Full multi-hop path

**Build:** client-side layered encryption across N hops; relays forwarding to each other.

**Deliverables**
- Client requests a path from the directory, builds N nested layers innermost-first
- Relays forward opaque payloads to the next hop
- Return path re-encrypts layer by layer per `RELAY_PROTOCOL.md` §7
- `docker-compose.yml` bringing up directory + 5–7 relays

**Acceptance**
1. 3-hop request completes end to end, response decrypted correctly by the client
2. **The visibility table in `RELAY_PROTOCOL.md` §6 holds** — verify by inspecting what each relay actually decrypts. The middle relay must not be able to see the destination
3. Each relay logs exactly one hop, no payload contents
4. Two consecutive runs use different paths
5. Works at `hops=2` and `hops=5`
6. A downed relay produces a clear named error, no hang

**This is the highest-risk phase.** If the visibility table does not hold, the layering is wrong and no amount of downstream work fixes it. Do not proceed on a partial pass.

---

### Phase 4 — Mock sites

**Build:** three sites reachable only through the relay chain.

**Deliverables**
- `mock-sites/forum-alpha/`, `mock-sites/marketplace-beta/`, `mock-sites/forum-gamma/`
- Content per `MOCK_SITES_SPEC.md`, seeded personas per GOTHAMITE `DATA_MODEL.md`
- Each containerised, on the internal Docker network only

**Acceptance**
1. All three reachable through a full relay path
2. Seeded personas, PGP fingerprints and wallet addresses present and consistent with the data model
3. The planted cross-site links exist as specified (shared PGP, shared wallet, the rebrand storyline)
4. Decoy personas present — similar-looking but genuinely unlinked
5. Content is stable and deterministic. **No randomly generated personas** — the demo depends on known-correct links

**Note:** planted links are the entire point. If GOTHAMITE finds nothing, there is nothing to show. This phase is content design as much as code.

---

### Phase 5 — Scraper agent

**Blocked on:** GOTHAMITE `docs/DATA_MODEL.md` and this repo's `API_CONTRACT.md`.

**Build:** `scraper/scraper_agent.py`.

**Deliverables**
- Crawls the three mock sites **through `onion_client`**, never directly
- Extracts fields per `SCRAPER_AGENT_SPEC.md`
- POSTs to GOTHAMITE in exactly the `API_CONTRACT.md` format

**Acceptance**
1. All routing goes through the relay chain — verifiable in relay logs
2. Visits only configured sources. No link-following outward
3. Scraped content handled as inert data — never executed, evaluated, or passed anywhere that treats text as instruction
4. Extracted fields validate against the contract schema
5. A site being down does not kill the run — that source fails, others continue

---

### Phase 6 — Integration and demo hardening

**Build:** nothing new. Make the existing path reliable.

**Deliverables**
- Full flow: `docker compose up` → scraper runs → data lands in GOTHAMITE → visible in its dashboard
- Startup ordering handled (relays register before the client asks for a path)
- Demo run repeatable from cold start
- `DEMO_SCRIPT.md` walked end to end at least twice
- **A recorded video of the full working flow**

**Acceptance**
1. Cold-start `docker compose up` to visible data in GOTHAMITE, no manual intervention
2. Run three times consecutively without failure
3. Different relay path each run
4. Recording exists and is watchable

**The recording is not optional.** Live demos of four chained subsystems fail on unfamiliar networks and projectors. The video is what stops a hiccup from costing the round.

---

## 4. Phase report format

At each gate, write `Agent_Docs/reports/PHASE_<n>_REPORT.md`:

```markdown
# Phase <n> Report

## Built
- <files created/modified, one line each>

## Tested — how, not just whether
- <what was run, what the observed output was>

## Stubbed / faked / incomplete
- <anything not actually working. Be exact. "None" is a valid answer only if true>

## Deviations from the docs
- <anything built differently from the specs, and why>

## Blocked
- <what is blocked, on what or whom>

## Acceptance criteria
- [ ] <each criterion from this plan, checked or not>

## Ready for next phase: YES / NO
```

Rules for the report:
- It is a status report, not a summary of intentions. "Implemented X" means X runs
- If a criterion is unmet, `Ready: NO`. Do not round up
- Never mark a criterion passed on the basis of code reading. Passed means executed and observed

---

## 5. Stop conditions

Stop and ask a human, mid-phase, if any of these occur:

- A spec is ambiguous or two docs conflict
- A phase's acceptance criteria appear unachievable as specified
- You need a dependency not named in the specs
- You believe something on the OUT OF SCOPE list is actually necessary
- Crypto is not behaving as `RELAY_PROTOCOL.md` describes

Do not resolve any of these by choosing an interpretation and continuing. A wrong assumption at Phase 1 is discovered at Phase 6, and there is no time to unwind it.
