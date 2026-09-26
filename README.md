# GOTHAMITE | Cyber Intelligence Suite

GOTHAMITE is an end-to-end cyber-intelligence and investigation platform engineered for deep-web source monitoring, multi-factor entity resolution, and explainable intelligence correlation. Designed for analysts, GOTHAMITE transforms fragmented, multi-source digital observations into a unified, actionable intelligence dossier.

## 🎯 Core Value Proposition

* **What GOTHAMITE collects:** Multi-source cyber intelligence (Dark Web Forums, Marketplaces, Open Web, Browser Intel).
* **What it does with the data:** Extracts, normalizes, correlates, and enriches identifiers into unified identities.
* **What makes it different:** Transparent cross-source entity resolution, explainable confidence scoring, and dynamic 3D graph analysis.
* **What the analyst gets:** A unified intelligence picture, risk context, evidence provenance, an investigation timeline, and a comprehensive entity dossier.
* **How it aligns with operations:** The entire workflow is meticulously mapped to the **NIST Cybersecurity Framework (CSF)**.

---

## 🏗️ Intelligence Pipeline Architecture

The GOTHAMITE platform operates on a robust data-fusion pipeline designed to minimize analyst fatigue and maximize actionable intelligence:

SOURCE → COLLECTION → NORMALIZATION → EXTRACTION → ENRICHMENT → CORRELATION → ANALYSIS → RISK → INVESTIGATION → REPORT

### 1. Data Collection & Browser Intelligence
GOTHAMITE ingests intelligence through modular collectors:
- **Dark Web Scrapers:** Headless autonomous collectors probing .onion forums and marketplaces.
- **Browser Intelligence Layer:** Analyst-driven manual captures from the open web seamlessly fed into the pipeline (Parse DOM → Extract NER → Normalize → Store Evidence).

### 2. Entity Resolution & Correlation Engine
The core technical differentiator of GOTHAMITE. It performs explainable identity resolution:
1. **Extraction:** Identifies handles, aliases, emails, domains, PGP fingerprints, and cryptocurrency wallets.
2. **Normalization:** Standardizes artifacts (e.g., stripping spaces from PGP keys).
3. **Correlation:** Connects entities using temporal proximity, shared infrastructure, and deterministic identifiers.
4. **Scoring:** Calculates confidence (HIGH/MED/LOW) and maintains transparent provenance for every linkage.

### 3. Analytical Risk Engine
Risk is dynamically calculated as a combination of multiple intelligence signals:
Risk = Exposure + Threat Indicators + Correlation Strength + Activity + Confidence
This analytical model directly influences entity prioritization, alert queues, and visual highlighting in the analyst workstation.

---

## 🛡️ NIST-Aligned Analyst Workflow

The GOTHAMITE UI is designed as a professional cyber-intelligence workstation, not a generic SaaS dashboard. The investigation journey is operationally aligned with the **NIST CSF**:

* **[IDENTIFY] 01 — DISCOVER:** Asset and entity discovery, threat surface mapping, and digital identity resolution queues.
* **[DETECT] 02 — COLLECT:** Continuous intelligence collection, source health monitoring, and intelligence-driven alerts (e.g., infrastructure changes, new credential exposures).
* **[RESPOND] 03 — CORRELATE (Entity Graph):** 3D visual analysis of resolved identities, infrastructure sharing, and interactive relationship investigation.
* **[RESPOND] 04 — ANALYZE (Timeline):** Chronological timeline construction bridging events across multiple disparate sources.
* **[PROTECT] 05 — ASSESS (Risk Engine):** Risk prioritization, exposure assessment, and high-value entity identification.
* **[RECOVER] 06 — INVESTIGATE (Dossier):** Generation of comprehensive intelligence dossiers preserving evidence provenance and investigation history for incident reporting.

---

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Deployment
GOTHAMITE utilizes a containerized microservice architecture.

1. **Start the Backend API & Frontend Workstation:**
   `ash
   cd gothamite
   docker compose up --build -d
   `
   The analyst workstation will be available at http://localhost:8501.

2. **Start the Dark Web Sandbox (Synthetic Intelligence Sources):**
   `ash
   cd darkweb-sandbox/mock_sites
   docker compose -f docker-compose.sites.yml up -d
   `

3. **Run the Autonomous Intelligence Collector:**
   `ash
   cd darkweb-sandbox
   python bridge_collector.py
   `
   *This script simulates the intelligence pipeline by scraping the mock .onion sites, extracting entities, and pushing them to the GOTHAMITE ingest API.*

---

## 🔬 Demonstration Scenario

The included synthetic dataset provides a highly deterministic investigation narrative for demonstrations:

1. **Discover:** Search for the entity 
ightjar.
2. **Collect:** Observe that 
ightjar operates on orum-gamma.
3. **Correlate:** The engine identifies a shared PGP fingerprint, linking 
ightjar to the known threat actor en0m.
4. **Graph:** The 3D entity graph visually maps this connection, highlighting the "HIGH" confidence score due to the deterministic key match.
5. **Timeline:** The chronological view reveals en0m was previously active on marketplace-beta, exposing a cryptocurrency wallet.
6. **Risk Assessment:** The entity's risk automatically elevates to **CRITICAL** due to cross-source confirmation and marketplace activity.
7. **Report:** Generate the final Intelligence Dossier for the unified 
ightjar / en0m identity.

---
*GOTHAMITE was built for the SIH 2026 Hackathon.*
