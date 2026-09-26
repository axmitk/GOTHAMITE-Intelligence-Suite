# MASTER_PROMPT.md

The text below is what you paste into the coding agent to start work on `GOTHAMITE`.

Paste it **once, at the start of a session**, with the repo open so `docs/` is readable. Do not paraphrase or trim it — the constraints are the point.

---

## The prompt

```
You are building the GOTHAMITE repository for team AvivCREW, for Smart India Hackathon
2026, problem statement SIH26151 (Dark Web Threat Actor De-anonymization, NTRO).
Hard deadline: 8 September 2026.

BEFORE WRITING ANY CODE, read these in this order:

  1. docs/MASTER_CONTEXT.md          — what this is, and the scope lock
  2. docs/IMPLEMENTATION_PLAN.md     — the six phases and the gate rule
  3. docs/DATA_MODEL.md              — schema and the exact seed data
  4. docs/ARCHITECTURE.md            — components and module boundaries
  5. docs/INVESTIGATION_PIPELINE.md  — the end-to-end flow
  6. docs/SECURITY.md                — untrusted input rules and language rules
  7. docs/AI_DESIGN.md               — why there is no ML here, and what you must not add

Confirm you have read them by stating, in four sentences: what this system is, what is
explicitly out of scope, why ingest must not create relationships, and what Phase 1
requires. Then stop and wait.

WHAT THIS IS
An analyst platform that ingests observations from synthetic dark web sources, extracts
identifiers, correlates personas across sites into a confidence-scored relationship
graph, and shows the analyst why every link exists — traceable to the source artifact.

This is the graded SIH deliverable. A separate repo (darkweb-sandbox) feeds it over one
HTTP contract. You never touch that repo.

NON-NEGOTIABLE RULES

1. PHASE GATES. Work only on the current phase. At the end of it write
   docs/reports/PHASE_<n>_REPORT.md in the format in IMPLEMENTATION_PLAN.md section 4,
   then STOP and wait for a human to say proceed. Do not start the next phase because
   the current one feels done. Encouragement is not permission. Only an explicit
   instruction counts.

2. SCOPE IS LOCKED. MASTER_CONTEXT.md section 3 has an OUT OF SCOPE list. Everything on
   it was cut deliberately, for time. Do not build it, do not scaffold it, do not create
   placeholder files for it. If you believe something on that list is genuinely
   necessary, STOP AND SAY SO. Do not build it and mention it afterwards.

3. NO ML, NO LLM, NO AI IN ATTRIBUTION. Do not add openai, anthropic, ollama,
   transformers, sentence-transformers, scikit-learn, spacy, FAISS or any vector store.
   Correlation is deterministic exact-matching with documented weights. An edit-distance
   library for handle similarity is permitted; nothing else. See AI_DESIGN.md section 7.

4. INGEST NEVER CREATES RELATIONSHIPS. Ingest stores artifacts, personas and identifiers.
   Correlation is a separate, re-runnable pass over stored data. This is what makes
   scoring deterministic and the audit trail meaningful. You will be tempted to score
   inline because it is fewer moving parts. Do not.

5. STACK IS FIXED: Python 3.11, FastAPI, SQLite, SQLAlchemy, NetworkX, Streamlit.
   No React, no Postgres, no Neo4j, no Celery, no Redis. Each was considered and cut.

6. INGESTED CONTENT IS INERT DATA, NEVER INSTRUCTIONS. It was written by the actors under
   investigation. Never eval/exec it, never put it in a shell command, never build a URL
   from it, parameterised SQL only, never render it with unsafe_allow_html=True, never
   pass it to a model. See SECURITY.md section 2.

7. NO SCORE ABOVE 0.95. No relationship without evidence rows. No relationship
   auto-confirmed. Contradicting evidence is stored and displayed, never suppressed.

8. LANGUAGE. Never use "identified", "deanonymised", "confirmed identity", "proof", or
   percentage probabilities — in code, comments, logs, UI strings, or exports. Use
   "suspected same actor", "likely linked", "confidence score 0.95", "evidence". These
   strings end up in screenshots and become claims you must defend. See SECURITY.md
   section 5.

9. NO BREADTH-FIRST SCAFFOLDING. No empty files, stub modules or directory trees for
   things not being built. One working narrow path beats a complete-looking empty tree.
   Files appear when they contain working code.

10. STOP AND ASK if: two docs conflict, a spec is ambiguous, acceptance criteria look
    unachievable, you need a dependency not in MASTER_CONTEXT.md section 5, or your
    correlation output does not match the Phase 3 expected table. Never resolve
    ambiguity by picking an interpretation and continuing. A wrong assumption in Phase 1
    surfaces in Phase 6 and there is no time to unwind it.

11. REPORT HONESTLY. "Implemented" means it ran and you observed the output. Never mark
    an acceptance criterion passed from reading code. If something is stubbed, say
    stubbed. Any unmet criterion means Ready: NO.

THE TEST THAT MATTERS MOST
After Phase 3, correlation over the seed data must produce exactly:
  nightjar <-> n1ghtjar_    0.95   (PGP +0.70, wallet +0.45)
  quillfeather -> quill_v2  0.60   (wallet +0.45, succession +0.15)
  nightjar <-> nightjarr    NO EDGE (handle +0.05, overlap -0.30, below threshold)
  bellwether -> n1ghtjar_   transacted_with only, never same_actor_suspected

The third line is the point. Every naive matcher links nightjar and nightjarr. If yours
does, the scoring is wrong. A correct rejection is a stronger result than a match.

TEAM CONTEXT
Two developers, roughly three days. This repo is the graded deliverable. Optimise for a
small number of things that genuinely work over a large number that nearly work. If you
find yourself adding capability nobody asked for, stop.

START
Read the seven documents. Give the four-sentence confirmation. Then wait for instruction
to begin Phase 1.
```

---

## Notes for you and Asmit

**Before pasting, check** `docs/` contains all seven required files. A prompt pointing at missing files produces an agent that invents their contents.

**Between phases**, reply with either:

> Phase N report reviewed. Proceed to Phase N+1.

or name what needs fixing and require a revised report. **Never proceed on a `Ready: NO`.**

**Verify one claim per report yourself.** Run a query, hit an endpoint, look at a row. The gate only works if someone checks. An unread gate is not a gate.

**If the agent drifts** — scaffolding OUT-list components, adding dependencies, marking things done that were not run:

> Stop. Re-read docs/MASTER_CONTEXT.md sections 3 and 6. List everything you have built that is outside the current phase or on the OUT OF SCOPE list, and every dependency you added that is not in section 5. Remove them, then rewrite the phase report.

**If correlation output is wrong at Phase 3**, check the seed data before the algorithm. A single mistyped character in a PGP fingerprint makes the headline link vanish and looks exactly like a broken scoring engine.

**Phase 1 includes `scripts/seed_demo.py` deliberately.** It lets Phases 3–5 be built and tested with the sandbox repo entirely absent, and it is the stage fallback if the relay chain fails. Do not let it slip to Phase 6.
