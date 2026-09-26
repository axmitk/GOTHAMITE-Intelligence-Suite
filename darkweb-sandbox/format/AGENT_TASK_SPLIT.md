# AGENT_TASK_SPLIT.md

**Repo:** `darkweb-sandbox`
**Owner:** Asmit
**Purpose:** who builds what, and what neither agent is allowed to touch.

Two coding agents work this repo in parallel. Complex engineering goes to **Claude Code**. Content and site-building goes to **Antigravity / Codex**.

The split is by **directory ownership**, and it is absolute. An agent that edits a file it does not own creates a merge conflict Asmit has to resolve by hand, at night, near a deadline.

---

## 1. Ownership

| Path | Owner | Contents |
|---|---|---|
| `relay/` | **Claude Code** | Relay node, layered decryption, forwarding |
| `client/` | **Claude Code** | `onion_client`, nested encryption, path handling |
| `directory/` | **Claude Code** | Registry, path selection |
| `scraper/` | **Claude Code** | Crawl logic, extraction, API submission |
| `docker-compose.yml` | **Claude Code** | Root compose — **see §3, this is the one collision point** |
| `mock-sites/` | **Antigravity** | All three sites, all content |
| `Agent_Docs/` | **Neither** | Specs are human-owned. Read-only to both agents |
| `Agent_Docs/reports/` | Both | Each writes its own phase reports only |

### Why this split

Claude Code takes the cryptography, the multi-hop routing, and the scraper's safety properties — layer isolation, nonce handling, untrusted-input rules, false-positive-free extraction. These are the parts where a subtle mistake is invisible until it breaks the demo, and where "looks right" and "is right" diverge.

Antigravity takes the mock sites: three small Flask apps and a body of hand-specified content. Low algorithmic complexity, high volume, exacting detail — the identifiers must match `DATA_MODEL.md` character for character.

---

## 2. What each agent must never touch

### Claude Code — do not touch
- `mock-sites/` — not to "fix" a site, not to add a test fixture, not to adjust markup. If a site is broken, **report it, do not edit it**
- Any content, persona, PGP fingerprint or wallet value
- Antigravity's phase reports

### Antigravity — do not touch
- `relay/`, `client/`, `directory/`, `scraper/` — ever, for any reason
- Root `docker-compose.yml`
- Any cryptographic code
- Claude Code's phase reports

**If either agent believes it needs to change the other's files: stop and tell Asmit.** Do not edit and mention it afterwards.

---

## 3. The `docker-compose.yml` collision

Both agents need services declared. This is the only genuine conflict point in the repo, and it will bite if left implicit.

**Resolution: two files.**

- **Claude Code** owns root `docker-compose.yml` — directory, relays, scraper, and the internal network definition
- **Antigravity** owns `mock-sites/docker-compose.sites.yml` — the three site services only
- Asmit runs both together:
  ```bash
  docker compose -f docker-compose.yml -f mock-sites/docker-compose.sites.yml up
  ```

Shared constraints both must honour, or the sites will not be reachable:

| | Value |
|---|---|
| Network name | `sandbox-net` (external, created by root compose) |
| Site containers | Join `sandbox-net`, **no `ports:` mapping to host** |
| Site container names | `forum-alpha`, `marketplace-beta`, `forum-gamma` |
| Site internal port | `80` |

The absent host port mapping is deliberate: it is what makes "reachable only through the relay chain" true and testable rather than asserted.

---

## 4. Sequencing

```
Antigravity ──► Phase 4 (mock sites) ─────────────────┐
                start NOW, no dependencies            │
                                                      ▼
Claude Code ──► Phase 1 ─► Phase 2 ─► Phase 3 ─► Phase 5 ─► Phase 6
                relay      directory  multi-hop   scraper   integration
```

- **Antigravity starts immediately.** Phase 4 has zero dependency on the relay work. Every hour it waits is an hour lost
- **Claude Code's Phase 5 is blocked on Antigravity finishing Phase 4** — the scraper needs real sites to crawl
- **Phase 6 belongs to Claude Code.** Antigravity is done after Phase 4, unless site fixes come back from integration

If Antigravity finishes early: it stops. It does not "help" with the relay work.

---

## 5. Reporting

Both agents follow the phase-gate rule in `IMPLEMENTATION_PLAN.md` §1: build the phase, write the report, **stop**, wait for Asmit.

- Claude Code → `Agent_Docs/reports/PHASE_1_REPORT.md`, `PHASE_2_...`, `PHASE_3_`, `PHASE_5_`, `PHASE_6_`
- Antigravity → `Agent_Docs/reports/PHASE_4_REPORT.md`

Distinct filenames, no collision.

---

## 6. The handoff at Phase 4 → 5

Before Claude Code starts Phase 5, Asmit verifies Antigravity's output himself. Do not take the phase report's word for it.

- [ ] All three sites come up on `sandbox-net`
- [ ] `curl http://forum-alpha/` **from the host fails** — no port mapping
- [ ] All six personas present with correct handles
- [ ] **PGP fingerprints and wallet addresses match `DATA_MODEL.md` §4 character for character** — diff them, do not eyeball them
- [ ] A1/A2 share PGP **and** wallet; B1/B2 share wallet only; C1 shares nothing with anyone
- [ ] B1's last post precedes B2's first by ~17 days
- [ ] Content identical across a restart

The fingerprint check is the one that matters most. A single wrong character produces a demo where the headline link silently does not appear, and it will look like the correlation engine is broken when the data is what is wrong.

---

## 7. Session prompts

Both agents get `MASTER_PROMPT.md` in full, plus one of these appended:

### Claude Code
```
You own: relay/, client/, directory/, scraper/, and root docker-compose.yml.

You do NOT own and must never edit: mock-sites/ (another agent is building it),
mock-sites/docker-compose.sites.yml, or Agent_Docs/ (human-owned specs, read-only).

Your phases are 1, 2, 3, 5, 6 — in that order. Phase 4 belongs to the other agent.
Phase 5 is blocked until their mock sites exist; if you reach it before then, stop
and say so rather than building stub sites to test against.

Root docker-compose.yml defines an external network `sandbox-net`. Mock site
containers join it as forum-alpha, marketplace-beta, forum-gamma on port 80, with
no host port mapping. Do not declare those services yourself.

If a mock site appears broken, report it. Do not fix it.
```

### Antigravity / Codex
```
You own: mock-sites/ and mock-sites/docker-compose.sites.yml. Nothing else.

You do NOT own and must never edit: relay/, client/, directory/, scraper/, root
docker-compose.yml, or Agent_Docs/ (human-owned specs, read-only). Another agent is
building the routing layer. Do not touch cryptographic code for any reason.

Your only phase is Phase 4. When it is done, write the report and stop. Do not
continue to other phases.

Build to Agent_Docs/MOCK_SITES_SPEC.md and the seed data in GOTHAMITE's
docs/DATA_MODEL.md section 4.

The seed values are exact. Copy every PGP fingerprint and wallet address character
for character. Do not regenerate, reformat, abbreviate or "tidy" them. Do not use
faker or any random generation — content must be hardcoded and byte-identical
across restarts.

Your three services join the external network `sandbox-net` as forum-alpha,
marketplace-beta and forum-gamma, listening on port 80, with NO ports: mapping to
the host. The absence of that mapping is a required property, not an oversight.
```

---

## 8. Notes for Asmit

**Run these in separate sessions**, not one agent with two tasks. The ownership boundary is enforced by the prompt, and a single session will drift across it.

**Review before proceeding, every time.** The gate only works if someone actually reads the report and checks a claim or two against the running system. An unread gate is not a gate.

**If an agent crosses its boundary:**
> Stop. You have edited files outside your ownership per AGENT_TASK_SPLIT.md section 1. List every file you touched outside your scope, revert them, and rewrite your phase report.

**Antigravity's work is the higher-risk half, despite being simpler.** The relay crypto fails loudly — it either decrypts or it does not. Wrong seed data fails silently, on stage, and looks like the correlation engine is broken. Budget real time for the §6 checklist.
