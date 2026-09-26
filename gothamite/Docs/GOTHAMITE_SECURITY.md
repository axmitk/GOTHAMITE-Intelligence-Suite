# SECURITY.md

**Repo:** `GOTHAMITE`
**Prerequisites:** `MASTER_CONTEXT.md`, `AI_DESIGN.md`

Two distinct concerns live here. **Application security** — this system ingests attacker-authored content by design. And **governance** — what the system is permitted to claim, and what it must never claim.

The second matters as much as the first. An attribution tool that overstates its confidence causes real harm.

---

## 1. Threat model

Unusual, and worth stating precisely: **the content this system ingests is written by the people it investigates.**

Every forum post, every listing, every profile is attacker-controlled input. Not "untrusted" in the abstract sense that all user input is untrusted — adversarial, authored by someone with motive to manipulate whatever processes it.

| Adversary | Capability | Mitigation |
|---|---|---|
| Actor authoring forum content | Full control of page text | §2 — content is inert data |
| Actor aware of the correlation logic | Plants shared identifiers to create false links | §4 — contradiction signals, analyst review, no auto-confirmation |
| Actor attempting to poison the graph | Floods sources with decoy identifiers | Analyst review; evidence is always inspectable |
| Analyst over-trusting output | Treats a score as proof | §5 — language rules, capped scores, mandatory evidence display |

Out of scope for this build: network attackers, multi-user privilege escalation (single-user demo), infrastructure compromise.

---

## 2. Ingested content is inert data

**The central rule. Everything else in this document follows from it.**

Content arriving via `/api/v1/ingest` is **never**:

- passed to `eval`, `exec`, `pickle.loads`, `yaml.load` (unsafe loader), or any deserialiser that can execute
- interpolated into a shell command or subprocess argument
- interpolated into a SQL string — **parameterised queries only, no exceptions**
- used to build a URL that the system then fetches
- written to a file path derived from its own content
- **passed into any LLM prompt** — see `AI_DESIGN.md` §5

Content is **only**:

- stored verbatim as an artifact
- read by rule-based extractors looking for known patterns
- sanitised, then rendered

### Rendering

Scraped HTML rendered unescaped in the dashboard is an injection into your own analyst UI, executed by content the adversary wrote.

- Escape all ingested strings before display. In Streamlit: never `unsafe_allow_html=True` on any ingested value
- Raw artifact viewing shows content **as escaped text**, never as rendered markup
- Handles, PGP fingerprints and wallet addresses are escaped before display like everything else

### Validation at the boundary

| Field | Constraint |
|---|---|
| `source_id` | Enum. One of three known values |
| `handle` | Length ≤ 128, no control characters |
| `pgp_fingerprint` | Exactly 40 hex chars after normalisation |
| `wallet` | Length 26–35, base58 alphabet only |
| `url` | Must match a known `.onion.mock` host |
| `raw_content` | Size cap (1 MB). Stored verbatim, but bounded |
| `relay_path` | List of known relay ids |

Reject at the boundary. A malformed field never reaches the database.

---

## 3. Data handling

**Artifacts are immutable.** Once written, never updated or deleted. Content hash verified on ingest. If a stored artifact's hash stops matching its content, that is corruption — fail loudly.

**Observations append.** A persona's `first_seen` / `last_seen` widen; nothing is overwritten. History is never collapsed.

**Provenance is mandatory.** Every identifier carries an `artifact_id`. Every evidence row carries an `artifact_id`. A derived claim that cannot name its source is a bug, not a degraded result.

**Analyst decisions persist.** A `rejected` relationship stays rejected across correlation re-runs. The system never overrides a human judgement.

### Not in this build
No auth, no RBAC, no encryption at rest, no audit log of analyst actions. Single-user demo, cut for time — listed in `MASTER_CONTEXT.md` §3.

Say this plainly if asked. All four are required for a real deployment and none are hard to add; they were cut because three days does not stretch. That is a better answer than pretending a login screen is a security model.

---

## 4. Attribution safety

The failure mode that matters most is not a crash. It is a **confident wrong link** that an analyst acts on.

### Enforced properties

**Scores cap at 0.95.** No output is ever 1.0. This system cannot establish certainty and must not render it.

**Contradicting evidence is displayed, never suppressed.** Negative signals reduce the score and appear in the evidence panel alongside supporting ones. A tool that only shows what supports its conclusion is a confirmation-bias engine.

**Nothing auto-confirms.** Correlation produces `proposed` relationships. Only an analyst sets `confirmed`.

**Interaction is not identity.** `transacted_with` edges are never promoted to `same_actor_suspected`. Two personas transacting are two personas. The seed data includes `bellwether` → `n1ghtjar_` specifically to demonstrate this line being held.

**Weak signals stay weak.** Handle similarity is 0.05. A one-character handle difference is close to meaningless — `nightjar` and `nightjarr` are in the seed data to prove the system knows that.

**Every score is inspectable.** Any number in the UI clicks through to its contributing signals and their source artifacts. No unexplained values anywhere.

### What the system does not do

It links **pseudonyms to pseudonyms**. It does not identify people.

A shared PGP key is evidence that two personas share control of a key. A shared wallet is evidence of a shared address. Neither is a name, a location, or a person. The gap between "these two handles are probably the same operator" and "this is a specific human being" is not one this system crosses, and no output should suggest otherwise.

---

## 5. Language rules

Enforced in code, logs, UI strings, exports and documentation.

| Never | Use instead |
|---|---|
| identified / deanonymised / unmasked | suspected same actor / likely linked |
| confirmed identity | analyst-confirmed link |
| 95% probability / 95% match | confidence score 0.95 |
| proof / proves | evidence / supports |
| the actor is X | personas P and Q are likely the same operator |

Strings ship into screenshots and demo recordings. A careless label in a UI component is a claim you will have to defend.

---

## 6. Ethical boundaries

Fixed, from the project design document. Not negotiable by any agent or under time pressure.

1. **No connection to real dark web infrastructure.** Not in code, tests, fixtures or comments
2. **No real scraped data.** Not from live sources, not from published dark web corpora, not from archives. All content is invented
3. **No real identifiers.** No real PGP key, wallet address, handle, or person appears anywhere. All seed values are synthetic and must not correspond to anything real
4. **No participation in illicit activity** of any kind, in any form, including simulated transactions that could function as instructions
5. **Built for authorised investigators under lawful process.** Framed that way in documentation and pitch, always

If an implementation choice would require crossing any of these: **stop.** It is not a trade-off to weigh against the deadline.

---

## 7. Agent rules

1. Parameterised queries only. Never build SQL by string concatenation
2. Never render ingested content with `unsafe_allow_html=True`
3. Never pass ingested content to `eval`, `exec`, a subprocess, or an LLM
4. Never create a relationship without evidence rows
5. Never emit a score above 0.95
6. Never auto-confirm a relationship
7. Never delete or mutate an artifact
8. Never use the forbidden vocabulary in §5, anywhere — including variable names, log lines and comments
9. If a task appears to require breaking any of the above: **stop and say so.** Do not implement it and note it in the report afterwards
