# REQUIREMENTS.md

**Repo:** `GOTHAMITE`
**Prerequisites:** `PROBLEM_STATEMENT.md`, `MASTER_CONTEXT.md`

Every capability NTRO asks for, mapped to what is actually built. **This document exists to prevent overclaiming.** If a slide, a demo line, or a Q&A answer states a capability, it must be marked BUILT here.

| Status | Meaning |
|---|---|
| **BUILT** | Working, demonstrable, defensible under questioning |
| **PARTIAL** | Working in a narrowed form. The narrowing is stated below and must be stated on stage |
| **DESIGNED** | Architecture supports it; not implemented for this deadline |
| **NOT BUILT** | Deliberately cut. Reason stated |

---

## 1. Mapping

### 1. Continuously gather threat-actor footprints from marketplaces, forums, deep web and other sources
**PARTIAL**

Built: a collection pipeline that crawls three synthetic sources through a simulated onion-routed network, extracting handles, PGP fingerprints and wallet addresses, and ingesting them with full provenance.

Narrowed: sources are synthetic, and scrapes are manually triggered rather than scheduled. The orchestration layer for continuous scheduled collection is designed but not implemented.

**Say:** "Our collection layer crawls configured sources and ingests observations with provenance. For this build the sources are a synthetic corpus we created, and collection is analyst-triggered — the scheduler is designed, not built."

**Never say:** "continuously monitors the dark web."

---

### 2. Link footprints to identifying information available on those sources
**BUILT**

Rule-based extraction of PGP fingerprints, wallet addresses and handles from post content, each stored against the persona and the source artifact it came from.

---

### 3. Find Tor hidden-service misconfigurations — exposed server-status pages, SSL certificates tied to clearnet domains, default service banners, descriptor inconsistencies
**NOT BUILT**

Cut for time. Certificate Transparency correlation is legally clean and genuinely feasible — CT logs are public infrastructure — and is the first thing to build next. It is marked STRETCH in `MASTER_CONTEXT.md` §3.

Descriptor-inconsistency detection is cut for a second reason: the project design document itself states the method must be validated against Tor protocol documentation before being claimed. That validation has not been done, and claiming an unvalidated detector is worse than omitting it.

**Say:** "Not built. Certificate Transparency correlation is our next component and the approach is defined. We did not want to claim a descriptor-inconsistency detector we hadn't validated against the protocol documentation."

---

### 4. Match hidden-service indicators with clearnet infrastructure to point to likely origin servers
**NOT BUILT** — depends on #3.

---

### 5. Map actors across multiple marketplaces into a relationship graph of handles, PGP keys, wallets and trust links
**BUILT — this is the core of the system**

Cross-source correlation producing a scored relationship graph. Nodes are personas, edges carry confidence scores, every edge carries its evidence.

Handles, PGP fingerprints and wallets are all implemented. Trust/reputation links between marketplace personas are **DESIGNED** — the schema supports the edge type, the signal is not scored.

---

### 6. Use AI-based analysis including stylometric persona identification and behavioural profiling
**NOT BUILT — deliberately**

See `AI_DESIGN.md` in full. Summary: our personas have 8–15 short posts each. A stylometric model on that volume produces numbers that look like results and mean nothing. We chose a deterministic engine whose every score reconstructs from documented weights and named artifacts.

**Say:** "We scoped it out rather than ship a model we couldn't evaluate. Attribution here is deterministic and reproducible, which is what makes the audit trail meaningful. The stylometry approach is specified — character n-grams and function-word frequency, weighted below the PGP signal, reported with precision and recall or not reported at all."

This is a strength when answered this way. It is a serious weakness if you claim the capability and get one follow-up question.

---

### 7. Link rebranded or migrated personas to known threat actors
**BUILT**

Temporal succession scoring: where one persona's activity ends and another's begins within 45 days, and independent evidence (a shared wallet) supports the link, the system proposes a migration.

Demonstrated by `quillfeather` → `quill_v2` — **linked at 0.60 with no PGP match**, because the key was rotated. Catching a rebrand without a key match is the interesting case.

---

### 8. Provide an analytical front end that queries the intelligence database across a chosen timeline
**BUILT**

Streamlit dashboard: graph, search (handle / PGP / wallet), per-persona dossier, and a timeline view where the rebrand handoff is visible as one activity line ending and another starting.

---

### 9. Operate in an autonomous mode using sources of good quality and reliability
**DESIGNED**

Source registry with reliability ratings and scan status exists in the schema. Scheduled autonomous collection is not implemented — scrapes are triggered manually.

**Never claim autonomous operation.** Say the architecture supports it and the scheduler was cut for the deadline.

---

### 10. Provide actor profiles, identifiers, infrastructure indicators, persona linkages, attribution confidence, category, last scan date and source
**PARTIAL**

Built: actor profiles, identifiers, persona linkages, attribution confidence, last scan date, source.
Not built: infrastructure indicators (depends on #3). Category is a schema field, not analyst-driven classification.

---

### 11. Export result sets as CSV, JSON and reports
**PARTIAL**

CSV and JSON built, including `artifact_id` on every evidence row — an export without provenance defeats the purpose. Formatted PDF reporting is **DESIGNED**, not built.

---

## 2. Summary

| Status | Count | Items |
|---|---|---|
| BUILT | 4 | #2, #5, #7, #8 |
| PARTIAL | 3 | #1, #10, #11 |
| DESIGNED | 1 | #9 |
| NOT BUILT | 3 | #3, #4, #6 |

**Roughly half the stated capability, built properly, with the gaps named.**

That is the deliberate trade. Eleven half-working capabilities would demo worse and collapse under questioning faster than four solid ones plus an honest account of the rest.

---

## 3. Beyond the PS

Three properties NTRO did not ask for, which strengthen the case:

**Contradiction-aware scoring.** The system surfaces evidence that *weakens* a proposed link, not only evidence supporting it. `nightjar` vs `nightjarr` — one character apart, overlapping activity — produces **no edge**, because a near-identical handle is worth almost nothing and conflicting activity windows count against. A tool that only shows supporting evidence is a confirmation-bias engine.

**Full provenance.** Every score reconstructs from its evidence rows; every evidence row names the artifact it came from; every artifact is stored verbatim with a hash. Any number in the UI clicks through to the actual source page.

**Adversarial-input design.** The content this system ingests is written by the people it investigates. It is never executed, never interpolated into a query or URL, never rendered unescaped, never passed to a model. See `SECURITY.md` §1–2.

---

## 4. Rule

**Nothing may be claimed on a slide, in the demo, or in Q&A unless it is BUILT or PARTIAL here** — and PARTIAL items must be stated with their narrowing.

If a claim appears in the deck that this document does not support, the deck is wrong and gets corrected. Not this document.
