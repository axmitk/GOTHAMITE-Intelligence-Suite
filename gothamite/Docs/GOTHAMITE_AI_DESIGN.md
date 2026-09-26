# AI_DESIGN.md

**Repo:** `GOTHAMITE`
**Prerequisites:** `MASTER_CONTEXT.md`

---

## 1. The position

**No AI, no ML, and no LLM participates in attribution in this build.**

That is a design decision, not a gap. This document exists to state it plainly, explain why, and define the boundary that keeps it true — because "AI-powered" is the easiest claim to make and the easiest to lose marks on.

The problem statement asks for AI-based stylometric and behavioural analysis. We have not built it, and we say so. What we built instead is a deterministic correlation engine whose every output can be reconstructed by hand from documented weights.

---

## 2. Why deterministic

**1. Reproducibility is what makes the audit trail worth anything.**
Every relationship traces to specific artifacts and specific weights. Re-running produces identical scores. An analyst can reconstruct any number on the screen with a calculator. Introduce a model into that chain and the explanation becomes "the model said so," which is not evidence and would not survive scrutiny in an investigative context.

**2. Stylometry done badly is worse than stylometry not done.**
Real stylometric authorship attribution needs a substantial per-author corpus, careful feature extraction, and evaluation against labelled ground truth with reported precision and recall. Our synthetic personas have 8–15 short posts each. A model trained on that would produce numbers that look like results and mean nothing.

Judges reward working systems with honest metrics and penalise unfounded ML claims. A confident, correct "we cut it, here's why" beats a vague "our AI analyses writing patterns" that collapses under one follow-up question.

**3. Time.**
Three days, two developers. Every hour on a model was an hour not spent making the correlation engine and dashboard actually work.

---

## 3. What we would build, and how

For the pitch — this is what "future work" means concretely, not hand-waving.

### Stylometric persona linkage
- Character n-grams (2–4) and function-word frequency — the standard baseline for short informal text
- Cosine similarity between persona profiles, calibrated on labelled ground truth
- **Reported with precision, recall and error bars, or not reported at all**
- Weight capped **below** the PGP signal. Writing style corroborates; it never carries a link on its own

### Behavioural profiling
- Posting-hour distributions, activity cadence, category preferences
- Corroborating only. Shared timezone is not shared identity

### Infrastructure attribution
- Certificate Transparency log correlation — a hidden-service certificate fingerprint matched against public CT logs to surface candidate clearnet domains
- Genuinely legal and buildable — CT logs are public infrastructure. **Cut for time, not for feasibility.** Marked STRETCH in `MASTER_CONTEXT.md` §3

### The rule that would apply to all of them
Any model output enters as **one weighted signal among several**, feeding the same evidence table as every other signal, with the same requirement to name its source artifact. A model never produces a conclusion. It produces a number that gets weighed alongside the deterministic ones.

---

## 4. The LLM boundary — enforced, not aspirational

If an LLM is ever added to this system, these hold:

| Rule | |
|---|---|
| **Never in attribution** | No LLM creates, modifies, scores or deletes a relationship. Ever |
| **Never on raw scraped text without treating it as hostile** | See §5 |
| **Output is a signal, not a verdict** | Enters the evidence table with a weight, like everything else |
| **Fully logged** | Prompt, model, version, output, timestamp — stored with the resulting evidence |
| **Seeded and reproducible where possible** | An unreproducible input to a reproducible pipeline breaks the pipeline |
| **Never in the demo path** | The demo runs deterministic |

Report-drafting or natural-language querying over already-computed results is a defensible use — it touches presentation, not attribution. That is the only use permitted, and it is not built for this deadline.

---

## 5. Prompt injection — the real risk, stated properly

In production, the pages this system ingests are **written by the actors under investigation**.

A forum post can contain text crafted to read as an instruction to any AI system that processes it. That is a documented, active attack pattern, not a theoretical concern. A pipeline that feeds scraped content into a model without treating it as hostile input can be steered by the exact people it is investigating — which turns an intelligence tool into a liability.

**Enforced boundary, in this repo, today:**

Ingested content is never:
- passed to `eval`, `exec`, or any deserialiser that can execute
- interpolated into a shell command
- interpolated into SQL — parameterised queries only
- used to construct a URL to fetch
- **passed into any LLM prompt**

Ingested content is only ever:
- stored verbatim as an artifact
- parsed by rule-based extractors for known patterns
- **sanitised before rendering** in the dashboard

The last one is not optional. Scraped HTML rendered unescaped in a Streamlit dashboard is a straightforward injection into your own analyst UI.

**This is a good answer to have ready.** If a judge asks how the system resists manipulation by the actors it monitors: it never treats their content as instructions, and there is no model in the attribution path for them to manipulate. Having designed against an attack you were not asked about reads better than a stylometry claim you cannot defend.

---

## 6. How to talk about this

**Say:**
> Attribution is deterministic and reproducible by design — every score reconstructs from documented weights and named source artifacts. We scoped stylometry out rather than ship a model trained on a handful of short posts and present its output as evidence.

**Do not say:**
> AI-powered threat actor identification.
> Our model detects writing patterns.
> Machine learning correlates the personas.

None of those are true of this build. All of them invite a question that ends badly.

**If asked "where's the AI?"** — answer from §2 and §3. Knowing precisely what you left out, and why, and what you would build instead, demonstrates more understanding than having a model you cannot evaluate.

---

## 7. Rule for the coding agent

**Do not add an LLM provider, an ML library, an embedding model, or a vector store to this repo.**

Not `openai`, not `anthropic`, not `ollama`, not `transformers`, not `sentence-transformers`, not `scikit-learn`, not `spacy`, not FAISS or Chroma.

`python-Levenshtein` (or an equivalent edit-distance implementation) is permitted — string edit distance is arithmetic, not machine learning.

If a task appears to require any of the above: **stop and say so.** Do not add the dependency and mention it afterwards.
