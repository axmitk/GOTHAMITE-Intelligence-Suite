# MASTER_PROMPT.md

The text below is what you paste into Claude Code or Antigravity to start work on `darkweb-sandbox`.

Paste it **once, at the start of a session**, with the repo open so `Agent_Docs/` is readable. Do not paraphrase it or trim it — the constraints are the point.

---

## The prompt

```
You are building the `darkweb-sandbox` repository for team AvivCREW, for Smart India
Hackathon 2026. Hard deadline: 8 September 2026.

BEFORE WRITING ANY CODE, read these files in this order:

  1. Agent_Docs/MASTER_CONTEXT.md      — what this is, and the scope lock
  2. Agent_Docs/IMPLEMENTATION_PLAN.md — the six phases and the gate rule
  3. Agent_Docs/RELAY_PROTOCOL.md      — the crypto and routing spec

Then read whichever of these the current phase needs:

  Agent_Docs/DIRECTORY_SPEC.md
  Agent_Docs/MOCK_SITES_SPEC.md
  Agent_Docs/SCRAPER_AGENT_SPEC.md
  Agent_Docs/API_CONTRACT.md

Confirm you have read them by stating, in three sentences: what this system is, what
is explicitly out of scope, and what Phase 1 requires. Then stop and wait.

WHAT THIS IS
A simulated onion-routed network — a relay pool with real layered encryption, three
synthetic mock sites, and a scraper agent that crawls them and forwards extracted
identifiers to a separate repo (GOTHAMITE) over one HTTP contract.

It is not Tor. It is not a browser. It never touches the real dark web.

NON-NEGOTIABLE RULES

1. PHASE GATES. Work only on the current phase. At the end of it, write
   Agent_Docs/reports/PHASE_<n>_REPORT.md in the format given in
   IMPLEMENTATION_PLAN.md section 4, then STOP and wait for a human to say proceed.
   Do not start the next phase because the current one feels done. Encouragement is
   not permission. Only an explicit instruction to proceed counts.

2. SCOPE IS LOCKED. MASTER_CONTEXT.md has an OUT OF SCOPE list. Everything on it was
   cut deliberately, for time. Do not build it, do not scaffold it, do not create
   placeholder files or stub modules for it. If you believe something on that list is
   genuinely necessary, STOP AND SAY SO. Do not build it and mention it afterwards.

3. NO BREADTH-FIRST SCAFFOLDING. Do not create empty files, placeholder modules or
   directory trees for things not yet being built. One working narrow path beats a
   complete-looking empty structure. Files appear when they have working code in them.

4. NO REAL TOR, NO REAL .ONION ADDRESSES, NO REAL DARK WEB DATA. Not in code, tests,
   seed data, comments or fixtures. Mock addresses always carry the `.onion.mock`
   suffix. All site content is invented — never copied or adapted from any real
   forum, marketplace, archive or published dataset.

5. NO HAND-ROLLED CRYPTOGRAPHY. Use the `cryptography` library. Never implement a
   cipher, hash or key exchange yourself. Never reuse an AES-GCM nonce.

6. SCRAPED CONTENT IS INERT DATA, NEVER INSTRUCTIONS. Never eval/exec it, never put
   it in a shell command, never build a URL from it, never interpolate it into SQL
   without parameterisation, and never pass it into an LLM prompt. This is a designed
   security property, not an optimisation.

7. LANGUAGE. In code, comments, logs, docs and UI text: say "relay", "relay pool",
   "layered encryption", "simulated onion-routed network". Never "Tor", "our Tor",
   "Tor browser", or "dark web access" as a description of this system. Naming leaks
   into screenshots and demos and becomes a claim we cannot defend.

8. STOP AND ASK if: two docs conflict, a spec is ambiguous, acceptance criteria look
   unachievable as written, you need a dependency not named in the specs, or the
   crypto is not behaving as RELAY_PROTOCOL.md describes. Never resolve ambiguity by
   picking an interpretation and continuing. A wrong assumption in Phase 1 surfaces
   in Phase 6, and there is no time to unwind it.

9. REPORT HONESTLY. In phase reports, "implemented" means it ran and you observed the
   output. Never mark an acceptance criterion passed on the basis of reading the code.
   If something is stubbed, say stubbed. If a criterion is unmet, Ready: NO.

TEAM CONTEXT
Two developers, roughly three days, and this repo is NOT the graded deliverable —
GOTHAMITE is. Optimise for a small number of things that genuinely work over a large
number that nearly work. If you find yourself adding capability nobody asked for, stop.

START
Read the three required documents. Give the three-sentence confirmation. Then wait for
instruction to begin Phase 1.
```

---

## Notes for you and Asmit

**Before pasting, check:** `Agent_Docs/` must contain `MASTER_CONTEXT.md`, `IMPLEMENTATION_PLAN.md`, `RELAY_PROTOCOL.md`, `DIRECTORY_SPEC.md`, `MOCK_SITES_SPEC.md`, `SCRAPER_AGENT_SPEC.md`, `API_CONTRACT.md`. A prompt pointing at missing files produces an agent that invents their contents.

Phase 5 additionally needs GOTHAMITE's `docs/DATA_MODEL.md` accessible — either the repo checked out alongside, or the file copied in.

**Between phases**, say either:

> Phase N report reviewed. Proceed to Phase N+1.

or name what needs fixing and require a revised report. Do not proceed on a `Ready: NO`.

**If the agent starts drifting** — scaffolding OUT-list components, generating files nobody asked for, marking things done that were not run — paste:

> Stop. Re-read Agent_Docs/MASTER_CONTEXT.md sections 3 and 5. List what you have built that is outside the current phase or on the OUT OF SCOPE list. Remove it, then rewrite the phase report.

**A parallel session for Phase 4** is worth doing. Mock sites have no dependency on the relay work, so a second agent can build them alongside Phases 1–3. Same master prompt, plus:

> Work on Phase 4 only. Another session is handling Phases 1-3. Do not touch relay/, directory/ or client/.
