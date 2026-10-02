> **Legacy script.** This describes the original persona-correlation demo
> (Streamlit on 8501, `docker compose`, simulated relay network). The current demo
> is the React investigation workbench on http://127.0.0.1:8042: follow the
> "Five-minute demo" in the [root README](../README.md). Keep this file only for
> the persona subsystem.

# DEMO_SCRIPT.md

**System:** GOTHAMITE — Cross-Source Dark Web Threat Actor De-Anonymization Platform  
**Target Audience:** SIH / Hackathon Technical Evaluators & Intelligence Agency Observers  
**Presentation Duration:** 6–7 minutes  
**Target Phase:** Phase 6 — Integration & Demo Hardening  

---

## 1. Golden Rules of the Presentation

1. **Rehearse the exact sequence below at least twice cold-start before presenting.**
2. **Have the pre-recorded walkthrough video ready and cued.** Chained systems across live or simulated networks carry environmental risks. If an external service hangs for more than 10 seconds, immediately switch to the video and maintain verbal narration.
3. **Use precise, professional terminology:**
   - Say *simulated onion-routed network*, *multi-hop relay pool*, *layered encryption*, *synthetic scenario test suite*, *threat actor persona*, *evidence locker*.
   - Never say "Tor browser" or "we hacked the dark web". Every statement made must be literally and technically true.
4. **Adhere to the strict vocabulary contract:**
   - Use *"suspected same actor"*, *"likely linked"*, *"confidence score 0.95"*, *"evidence"*.
   - Never use *"identified"*, *"deanonymised"*, *"confirmed identity"*, *"proof"*, or percentage labels like *"95% probability"*.

---

## 2. Screen & Window Arrangement

Before stepping up, configure the display into clean, uncluttered windows:

| Window | Application | Role / Content |
|---|---|---|
| **Window 1** | Terminal (Split) | Left: `docker compose up` logs / backend output. Right: CLI trigger commands |
| **Window 2** | Web Browser Tab 1 | GOTHAMITE Dashboard Overview & Graph View (`http://localhost:8501`) |
| **Window 3** | Web Browser Tab 2 | Dossier & Investigation Timeline (`http://localhost:8501`) |
| **Window 4** | Web Browser Tab 3 / Swagger | FastAPI Interactive API Docs (`http://localhost:8000/docs`) |

---

## 3. Demo Walkthrough Script

### 0:00 — Problem Statement & Motivation (45 seconds)
*No screen interaction. Address the judges directly.*

> "An intelligence analyst tracking dark web threat actors faces a fundamental challenge: fragmentation. The exact same human adversary operates under completely different handles across disparate dark web forums, escrow markets, and leak boards.
>
> Today, correlating these personas is painstakingly manual—investigators manually cross-reference forum posts, maintain ad-hoc spreadsheets, and rely on human memory. This does not scale, introduces cognitive bias, and leaves no audit trail of why two handles were linked.
>
> GOTHAMITE solves this by automating deterministic, multi-vector actor correlation. Furthermore, because operating against live dark web networks is ethically and legally constrained, we built an end-to-end simulated onion-routed infrastructure with synthetic marketplaces and realistic actor activity to exercise each attribution rule on cases with known answers."

---

### 0:45 — The Onion-Routed Pipeline & Ingestion Architecture (75 seconds)
*Switch to Window 1 / Window 4.*

> "Threat intelligence begins with secure collection. Our crawler traverses a multi-hop relay pool where each node peels exactly one cryptographic layer, providing true onion routing semantics.
>
> When data reaches GOTHAMITE via our ingestion API (`POST /api/v1/ingest`), we enforce a strict architectural boundary: **Ingestion never creates relationships.**
>
> Ingest treats raw page content as an inert, immutable evidence locker. It computes SHA-256 hashes, preserves relay provenance, and stores raw HTML verbatim without executing or interpolating it into queries."

*Point to Swagger `/docs` or Terminal showing HTTP 202 Accepted and duplicate prevention.*

---

### 2:00 — Deterministic Correlation Engine (75 seconds)
*Switch to Window 2 (Streamlit Overview / Graph).*

> "Every attribution score must be rebuildable by hand from its evidence.
> 
> GOTHAMITE implements a deterministic correlation engine. It evaluates five scored signals, plus one that is switched off:
> 1. Cryptographic PGP Key Matching (+0.70)
> 2. Cryptocurrency Wallet Reuse (+0.25, needs a second signal to form a link)
> 3. Handle Similarity via Levenshtein Edit Distance (+0.05)
> 4. Temporal Succession for Migrations and Rebrands (+0.15)
> 5. Activity Overlap Conflict Penalties (-0.30)
> 6. Lexical similarity, term-frequency cosine (weight 0, off until real stylometry exists: on scraped pages it fired on 8 of 12 pairs because of shared page markup)
>
> Scores are strictly capped at 0.95. Let us trigger the correlation pass."

*Click "Trigger Cross-Source Correlation Pass" on the dashboard.*

---

### 3:15 — The Visual Graph & Headline Attribution (90 seconds)
*Switch to `1_graph` interactive canvas.*

> "The analyst workbench renders the unified threat graph. Nodes represent personas color-coded by source, and edges represent suspected actor links.
>
> Look at our headline attribution:
> - Persona `nightjar` on `forum-alpha` is linked to `n1ghtjar_` on `marketplace-beta`.
> - Click the edge: the Evidence Inspector reveals the exact breakdown—Shared Canonical PGP Fingerprint (+0.70) and Shared Bitcoin Settlement Wallet (+0.25), capped at 0.95.
> - Click the 'Artifact ID' link: the analyst immediately views the raw immutable HTML collected from the onion site, proving the exact origin and timestamp."

---

### 4:45 — Rebrands, Decoys, and Anti-False-Positive Filtering (90 seconds)
*Zoom into the remaining graph nodes.*

> "Real threat actors rotate credentials and set decoys. GOTHAMITE is specifically hardened against naive matching:
>
> **1. The Rebrand (`quillfeather` → `quill_v2`):**
> Notice this link has a confidence score of 0.40. `quillfeather` announced departure from `forum-alpha` in early April. 17 days later, `quill_v2` surfaced on `forum-gamma`. The actor rotated their PGP key, but reused their treasury wallet. GOTHAMITE detected the wallet reuse (+0.25) and temporal succession (+0.15) to uncover the rebrand despite key rotation.
>
> **2. The Decoy Defense (`nightjarr` with two R's):**
> Notice persona `nightjarr`. Naive edit-distance tools link `nightjar` and `nightjarr` immediately because their handles differ by one character. But GOTHAMITE evaluates the activity window: both posted concurrently on competing platforms without shared cryptographic proof. The temporal overlap penalty (-0.30) completely wiped out the handle similarity (+0.05), dropping the score below our 0.30 threshold. **No false positive edge was created.**
>
> **3. Financial Transactions (`bellwether` → `n1ghtjar_`):**
> Look at `bellwether`. They transacted with `n1ghtjar_` via escrow. GOTHAMITE created a `transacted_with` relationship, but strictly isolated it from identity clustering. A customer is never accused of being the vendor."

---

### 6:15 — Audit Dossier, Export & Conclusion (30 seconds)
*Switch to `2_dossier`. CSV/JSON export is the API endpoint `GET /api/v1/export?format=csv|json` (whole correlation set; no UI button).*

> "Finally, the dossier and the export keep provenance: every evidence row in the CSV/JSON export carries its source artifact ID, and each artifact keeps its SHA-256 hash.
>
> In summary, GOTHAMITE transforms fragmented dark web noise into auditable, deterministic intelligence."

---

## 4. Frequently Asked Questions & Defensive Responses

| Question | Defensible Answer |
|---|---|
| **Why not use LLMs or AI for attribution?** | An attribution lead has to be checkable. GOTHAMITE uses deterministic, rule-based scoring where every score reconstructs exactly to its underlying signals and raw artifacts. The weights are hand-set priors, not yet calibrated (docs/scoring_rationale.md). |
| **Why synthetic data instead of live Dark Web data?** | Scraping live dark web networks during development is ethically irresponsible and legally prohibited for student teams. Synthetic cases have known answers, so each rule can be exercised; because we wrote them, they do not measure real-world accuracy. When authorized, GOTHAMITE points directly to lawful feeds without altering the core engine. |
| **How does the system prevent scraper poisoning attacks?** | All ingested payloads are treated as inert data. Raw HTML and usernames are never evaluated as code, never interpolated dynamically into SQL statements (SQLAlchemy parameterized queries only), and rendered strictly escaped in the UI (`unsafe_allow_html=False`). |
| **Why are confidence scores capped at 0.95?** | In forensic intelligence, 1.0 implies absolute mathematical certainty. Because adversaries can theoretically compromise private keys or share wallets, the system strictly reserves 1.0 and labels 0.95 as 'Very Strong Link'. |

---

## 5. Failure Playbook & Fast Emergency Recovery

| Failure Mode | Immediate Remediation |
|---|---|
| **Simulated relay chain or scraper hangs** | Do not pause or troubleshoot live. Immediately execute the autonomous fallback:<br>`python scripts/seed_demo.py && python scripts/run_correlation.py`<br>Takes less than 2 seconds, populates the scenario test suite, and dashboard is instantly live. |
| **Docker container restart required** | Run `docker compose restart backend` or fall back to local virtualenv execution: `./venv/bin/streamlit run frontend/app.py`. |
| **Dashboard UI cache out of sync** | Click the browser reload button or click "Trigger Cross-Source Correlation Pass" on the overview page. |
| **Host network / projector connection drops** | Cut to the cued MP4 video recording and continue vocal narration following the timing cues above. |
