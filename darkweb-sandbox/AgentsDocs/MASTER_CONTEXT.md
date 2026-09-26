# MASTER_CONTEXT.md

**Repo:** `darkweb-sandbox`
**Team:** AvivCREW
**Event:** Smart India Hackathon 2026 — internal college round + SIH prototype
**Hard deadline:** 8 September 2026
**Read this file first. Every other doc in `Agent_Docs/` assumes you have read it.**

---

## 1. What this repo is

A **simulated onion-routed network** containing fake dark web forums and marketplaces, plus a scraper agent that crawls them through that network.

It exists for one reason: to demonstrate, visibly and honestly, how the GOTHAMITE intelligence platform's collection layer reaches hidden services and what it extracts from them — without ever touching the real dark web.

This is **not** Tor. It is **not** a browser. It is a working simulation of the onion routing mechanism, built so that every claim made about it on stage is literally true.

---

## 2. Relationship to GOTHAMITE

Two separate repos. One data pipeline.

```
darkweb-sandbox (this repo)          GOTHAMITE (separate repo)
─────────────────────────────        ──────────────────────────
mock forums / marketplaces
        ▲
        │ routed through
        │
  relay pool + directory
        ▲
        │ uses
        │
   onion_client
        ▲
        │ uses
        │
  scraper_agent  ──────────────►  backend API  ──► extraction
                  API_CONTRACT.md                  ──► graph engine
                  (the ONLY seam)                  ──► dashboard
```

**`API_CONTRACT.md` is the only place these two repos touch.** The scraper agent lives here. GOTHAMITE never imports anything from this repo, and this repo never imports anything from GOTHAMITE.

**`API_CONTRACT.md` is authoritative for the sandbox ↔ GOTHAMITE payload and wire contract.** GOTHAMITE's own `docs/DATA_MODEL.md` remains authoritative for GOTHAMITE's internal representation, and this repository's `AgentsDocs/DATA_MODEL.md` §4–§5 remains authoritative for the sandbox's simulated ground truth. Neither repository owns the other's internal model; they must remain compatible **at this boundary**.

If the contract and either side's internal model disagree at the boundary, that is a **change request against `API_CONTRACT.md`**, agreed between the two repositories — not an automatic override of it in either direction. Do not invent fields.

*(Corrected per SD-025, in force. This paragraph previously said GOTHAMITE's `docs/DATA_MODEL.md` wins on disagreement, which SD-025 superseded when `API_CONTRACT.md` line 4 was amended.)*

---

## 3. Scope lock — read carefully

The team has deliberately scoped this down. These are decisions, not oversights. **Do not "improve" the design by adding anything from the OUT list.**

### IN SCOPE — build these

| Component | Scope |
|---|---|
| **Relay pool** | 5–7 relay nodes, each a separate Docker container with its own keypair |
| **Layered encryption** | Real, per-hop. Each relay decrypts exactly one layer and learns only its immediate next hop |
| **Directory service** | In-memory registry of relays (id, address, public key, up/down). Client queries it for a path |
| **Path selection** | Client receives a randomly selected N-hop path from the pool. Path differs between sessions |
| **Mock sites** | 3 sites (2 forums, 1 marketplace) with seeded persona content, reachable only through the relay chain |
| **Scraper agent** | Crawls the mock sites via `onion_client`, extracts defined fields, POSTs to GOTHAMITE per `API_CONTRACT.md` |

### OUT OF SCOPE — do not build these

| Excluded | Why |
|---|---|
| Directory authorities / consensus voting | Real Tor uses 9 authorities voting on a consensus document. Out of time budget. A single in-memory registry replaces it |
| Onion service descriptor resolution (DHT) | Mock `.onion`-style addresses map directly to containers. No distributed lookup |
| Relay bandwidth/uptime weighting | Random selection from the pool is sufficient |
| Relay reputation, authentication, or admission control | Relays are pre-registered at startup |
| Circuit teardown / rebuild on mid-path relay failure | Out of scope. A failed path may simply error |
| Any real Tor connectivity | **Hard rule.** Nothing in this repo connects to the real Tor network or any real `.onion` address, ever |
| A browser / browser chrome / rendering engine | This is a routing layer and a scraper. There is no browser UI to build |
| Stylometry, ML, or any LLM inference | Not in this repo. Not in scope anywhere for this deadline |

---

## 4. What is real vs. what is simplified

Be precise about this. It is the difference between a defensible demo and an embarrassing one.

| Claim | Status |
|---|---|
| Per-hop layered encryption | **REAL.** Standard AES/RSA via the `cryptography` library |
| Relay isolation | **REAL.** Separate Docker containers, separate processes, separate keys |
| Each relay knows only its neighbours | **REAL.** A relay cannot see the full path or the payload beyond its own layer |
| Dynamic path selection per session | **REAL.** Client queries the directory and gets a fresh path |
| Relay pool size | **SIMPLIFIED.** Fixed pool of 5–7, not a global volunteer network |
| Directory / consensus | **SIMPLIFIED.** Single in-memory registry, no voting, no distributed trust |
| Onion address resolution | **SIMPLIFIED.** Direct mapping, no DHT |
| Anonymity guarantee | **NONE.** We operate every node. This demonstrates the mechanism, not real-world anonymity |
| The forums/marketplaces | **SYNTHETIC.** Entirely invented content. No real scraped data, ever |

**Language rule for all output, docs, comments and UI text:**
Say "simulated onion-routed network", "relay pool", "layered encryption".
Never say "Tor", "our Tor", "Tor browser", or "dark web access" as a description of what this repo does.

---

## 5. Hard rules

1. **No real Tor. No real `.onion` addresses. No real dark web data.** Not in code, not in tests, not in seed data, not in comments.
2. **No hand-rolled cryptography.** Use `cryptography` (or equivalent standard library) primitives only. Never implement a cipher, hash, or key exchange from scratch.
3. **Scraped content is untrusted data, never instructions.** The scraper parses mock site content as data. It must never execute, evaluate, or feed scraped text into anything that treats it as a command. (This mirrors a real prompt-injection risk in the production system and is a deliberate design property, not paranoia.)
4. **The scraper visits only sites in its configured source list.** No arbitrary link-following, no crawling outward from discovered URLs.
5. **Do not add dependencies** not listed in the specs without flagging it in the phase report first.
6. **Do not scaffold empty files, stub modules, or placeholder directories** for anything on the OUT OF SCOPE list. Breadth is not progress. A working narrow path beats a complete-looking empty tree.

---

## 6. How you must work — phase gates

Build is divided into phases in `IMPLEMENTATION_PLAN.md`.

**At the end of every phase you must STOP.** Do not begin the next phase.

Write a short phase report covering:
- What was built
- What was actually tested, and how
- What is stubbed, faked, or incomplete
- What is blocked, and on what
- Any deviation from these docs, and why

Then wait for explicit human confirmation before proceeding. "Proceed" means a human said proceed. Nothing else counts.

If a spec is ambiguous or you believe a doc is wrong: **stop and ask.** Do not resolve ambiguity by guessing and continuing. A wrong assumption compounds across phases and there is no time to unwind it.

---

## 7. Success criteria

This repo is done when, live and repeatably:

1. `docker compose up` brings up the directory, 5–7 relays and 3 mock sites
2. The client requests a path and receives a randomly selected route through the pool
3. A request travels the full path, each relay peeling exactly one layer, each container's log showing only its own hop
4. A mock site responds and the response returns to the client
5. The scraper extracts the defined fields from all 3 mock sites
6. The extracted data reaches GOTHAMITE in the exact format defined in `API_CONTRACT.md`
7. Re-running produces a different path through the pool

Nothing beyond this list is required. Anything beyond this list is a risk to the deadline.
