# ROBIN_ANALYSIS.md

**Repo:** `GOTHAMITE` → `research/`
**Subject:** Robin — AI-Powered Dark Web OSINT Tool (open source, `apurvsinghgautam/robin`)
**Purpose:** structural reference, and honest differentiation for the pitch.

---

## 1. What Robin is

An open-source tool for dark web OSINT investigations. It uses LLMs to refine a query, filters results from dark web search engines, scrapes them, and produces an investigation summary. Modular separation between search, scrape and LLM workflows; supports OpenAI, Claude, Gemini and local Ollama models; CLI-first with a Streamlit web UI; Docker deployment. It requires a local Tor installation to perform its searches.

Its workflow:

```
analyst query  →  refine with LLM  →  search dark web search engines (via Tor)
               →  scrape results  →  LLM summary  →  report file
```

Created by a threat research analyst, actively maintained, and explicitly framed for lawful investigative use.

---

## 2. Why we looked at it

**As a structural reference.** Robin's separation of search / scrape / analysis into independent workflows informed our own split of ingest / correlation / presentation. Same principle: keep collection away from analysis so either can change without the other.

**No code is used.** Robin is not a dependency and nothing is imported from it. The architectural pattern was the useful part.

---

## 3. What Robin does not do

This is the differentiation, and it is a **capability** difference, not a quality judgement. Robin does its job well. Its job is a different job.

| | Robin | GOTHAMITE |
|---|---|---|
| Unit of work | One query, one investigation | Continuous observation of configured sources |
| Memory | None between runs — each investigation is standalone | Persistent store; observations accumulate over time |
| Cross-source identity | Not attempted | The core function |
| Confidence | Narrative LLM summary | Numeric scores from documented weights |
| Contradicting evidence | Not modelled | First-class — reduces score, always displayed |
| Provenance | Report cites sources | Every claim traces to a stored, hashed artifact |
| Temporal modelling | None | Activity windows; rebrand/migration detection |
| Determinism | LLM-generated, varies between runs | Fully deterministic and reproducible |
| Analyst feedback | None | Confirm/reject recomputes the graph |

**In one line:** Robin answers *"what is out there about X right now?"* GOTHAMITE answers *"which of these personas are the same operator, how confident are we, and what is the evidence?"*

Robin searches and summarises, then forgets. GOTHAMITE accumulates and correlates.

---

## 4. Where Robin is genuinely ahead

State this if asked. Pretending otherwise is the kind of thing that gets caught.

- **Robin operates on real sources.** It performs live searches over real Tor against real dark web search engines. We run on a synthetic corpus — deliberately, for legal and ethical reasons, but it means Robin is solving a real-world collection problem we have not solved
- **Robin is mature and maintained**, with real users and a real release history. Ours is a hackathon prototype
- **Robin's LLM summarisation** produces readable narrative intelligence quickly. We produce structured evidence, which is more auditable but less immediately readable

---

## 5. What not to claim

**Never say** GOTHAMITE is "Robin but better", or imply we also perform live real-world dark web collection. We do not, and the difference is checkable by anyone who has used Robin.

**Never say** Robin is a poor tool or that it fails at attribution. It does not attempt attribution — that is scope, not failure.

**The honest framing:**

> We studied Robin, an open-source dark web OSINT tool. It does live search-and-summarise over real Tor — one query at a time, with no memory between investigations. What NTRO's problem statement actually asks for is different: persistent, correlated, time-aware attribution across sources. Robin has no identity graph, no cross-source correlation, no confidence model and no temporal analysis, because that isn't what it's for. That gap is what we built into.

That is defensible against anyone who knows the tool, and it demonstrates you surveyed the space rather than assuming nothing existed.

---

## 6. Other tools reviewed

Briefly, for the same gap analysis:

- **Maltego** — strong graph visualisation; links are manually asserted and binary. No confidence weighting, no automated cross-source correlation
- **SpiderFoot** — broad automated OSINT collection, surface-web oriented. No crypto correlation, no persona linkage
- **Chainalysis Reactor** — excellent wallet tracing; cryptocurrency only, no forum/marketplace identity correlation, commercial and foreign-hosted

**The common gap:** none combine cross-source persona identifiers, wallet relationships and temporal migration into a single scored, evidence-backed correlation pass with contradicting evidence modelled.

That gap is the project.

---

## 7. Source

- Repository: `github.com/apurvsinghgautam/robin`
- Reviewed: September 2026
- Basis: public repository documentation and feature description. **We have not run it** — it requires live Tor connectivity to real dark web search engines, which is outside our ethical scope. Claims here describe documented capability, not observed behaviour, and should be stated that way if pressed.
