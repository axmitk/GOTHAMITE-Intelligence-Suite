# GOTHAMITE

> **Cross-Source Dark Web Threat Actor De-Anonymization & Correlation Intelligence Platform**  
> *Deterministic Attribution · Auditable Evidence Provenance · Contradiction-Aware Scoring*

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026-orange.svg)](https://www.sih.gov.in/)
[![Problem Statement](https://img.shields.io/badge/PS-SIH26151%20(NTRO)-blue.svg)](#problem-statement)
[![Team](https://img.shields.io/badge/Team-AvivCREW-purple.svg)](#team--acknowledgements)
[![Python](https://img.shields.io/badge/Python-3.11-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20Research-lightgrey.svg)](#license)

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Core Principles & Architectural Philosophy](#core-principles--architectural-philosophy)
- [System Architecture](#system-architecture)
- [Correlation Engine & Scoring Model](#correlation-engine--scoring-model)
  - [Signal Weight Matrix](#signal-weight-matrix)
  - [Ground Truth Seed Benchmark](#ground-truth-seed-benchmark)
- [Application Security & Threat Model](#application-security--threat-model)
  - [Ingested Content as Inert Data](#ingested-content-as-inert-data)
  - [Attribution Safety & Language Rules](#attribution-safety--language-rules)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Installation](#local-installation)
  - [Running with Docker Compose](#running-with-docker-compose)
  - [Quickstart: Seed & Correlate](#quickstart-seed--correlate)
- [Analyst Workflow & Dashboard](#analyst-workflow--dashboard)
- [API Reference](#api-reference)
- [Documentation Index](#documentation-index)
- [Team & Acknowledgements](#team--acknowledgements)

---

## Overview

**GOTHAMITE** is an analyst-centric threat intelligence platform built to correlate threat-actor personas across disparate dark web sources (marketplaces, forums, leak sites) into a unified, confidence-scored relationship graph.

When threat actors operate across decentralized hidden services, they routinely rotate handles, migrate infrastructure, or cross-post between marketplaces. GOTHAMITE ingests observations, extracts cryptographic and digital identifiers (PGP keys, cryptocurrency wallets, temporal footprints), discovers linkages between distinct personas, and surfaces the explicit evidence justifying every relationship.

Crucially, GOTHAMITE provides **full cryptographic provenance**: every edge in the intelligence graph links directly to immutable, hashed source artifacts, allowing an investigator to inspect the exact verbatim page where an observation originated.

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Synthetic Dark  │       │ GOTHAMITE       │       │ Analyst         │
│ Web Crawlers    ├──────►│ Correlation     ├──────►│ Investigation   │
│ & Scrapers      │ Ingest│ Engine          │ Graph │ Workbench       │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                            │                       │
                            ▼                       ▼
                     [Artifact Locker]       [Evidence Provenance]
                     (Raw SHA-256 Hashes)    (Auditable Signals)
```

---

## Problem Statement

* **Code:** `SIH26151`
* **Title:** Dark Web Threat Actor De-anonymization
* **Organization:** National Technical Research Organisation (NTRO)
* **Theme:** Blockchain & Cybersecurity
* **Hackathon:** Smart India Hackathon 2026

### The Core Challenge
Threat actors purposefully fragment their identities:
1. Rebranding or migrating handles after forum busts or marketplace exits.
2. Generating noise and typosquatting handles (`nightjar` vs `nightjarr`) to confuse scrapers and investigators.
3. Transacting with other actors, creating deceptive co-occurrence signals that naive graph tools mistakenly flag as shared identity.

GOTHAMITE addresses this by moving beyond naive string matching, providing a deterministic, contradiction-aware correlation framework with full auditability.

---

## Core Principles & Architectural Philosophy

### 1. Deterministic & Reproducible Attribution
Attribution must withstand adversarial scrutiny and legal standards of evidence. GOTHAMITE does not rely on black-box neural networks, LLM attribution, or stochastic clustering. Every confidence score is computed via documented, arithmetic weights over verifiable digital artifacts. Re-running the pipeline over identical observations produces identical results.

### 2. Complete Evidence Provenance
A score without an audit trail is inadmissible conjecture. In GOTHAMITE:
* Every derived identifier carries an `artifact_id`.
* Every graph edge carries explicit `evidence` rows pointing to specific artifact IDs.
* Every artifact is stored verbatim with an immutable SHA-256 hash.
* Analysts can click any edge or score in the UI to inspect the exact raw post that established the link.

### 3. Contradiction-Aware Scoring
Naive OSINT tools focus solely on supporting signals, falling prey to confirmation bias. GOTHAMITE models **contradicting signals as first-class citizens**. For instance, two near-identical handles active concurrently on different platforms are penalized heavily with a negative weight (-0.30), reflecting the high probability of separate actors or typosquatting decoys.

### 4. Interaction is Not Identity
Transacting with an actor does not make you that actor. GOTHAMITE isolates interaction signals into a separate `transacted_with` edge type, which is **never** promoted to a `same_actor_suspected` link.

### 5. Ethical Research & Safety Boundary
* **No live dark web traffic:** The platform operates against a synthetic corpus of simulated Tor hidden services (`.onion.mock`).
* **Inert data pipeline:** Ingested content is treated as inherently hostile text authored by adversaries. It is never executed, evaluated, interpolated into shell commands, or injected into LLM prompts.
* **Pseudonym-to-pseudonym correlation:** GOTHAMITE maps relationships between pseudonymous online handles; it never claims real-world physical deanonymization.

---

## System Architecture

GOTHAMITE enforces a strict **unidirectional 4-layer architecture**. Ingest and Correlation are deliberately decoupled: **ingestion never creates relationships inline**. This guarantees that scoring is order-independent and deterministic.

```
                    External Scraper / Relay Crawler
                                   │
                                   ▼ POST /api/v1/ingest
┌────────────────────────────────────────────────────────────────────────────┐
│ 1. INGEST LAYER                                                            │
│    • Validate JSON schema & ISO-8601 timestamps                            │
│    • Recompute & verify SHA-256 hash of raw_content                        │
│    • Deduplicate on (source_id, content_hash)                              │
│    • Persist raw artifact → upsert persona → persist identifiers           │
│    • ZERO relationships created here. Pure storage.                        │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 2. STORAGE LAYER (SQLite / PostgreSQL-compatible)                          │
│    • artifacts · personas · identifiers · relationships · evidence         │
│    • Append-only observations; immutable artifact history                  │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼ Triggered via API / Dashboard Button
┌────────────────────────────────────────────────────────────────────────────┐
│ 3. CORRELATION ENGINE (Batch Evaluation)                                   │
│    • Evaluates all cross-source persona pairs (P.source_id != Q.source_id) │
│    • Matches exact normalized PGP fingerprints & cryptocurrency wallets    │
│    • Evaluates temporal succession windows (< 45 days)                     │
│    • Computes Levenshtein handle similarity                                │
│    • Evaluates contradicting activity overlap (-0.30)                      │
│    • Clamps scores to [0.00, 0.95]; emits relationship & evidence rows     │
│    • Idempotent: survives re-runs and respects analyst rejections          │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 4. PRESENTATION & WORKBENCH LAYER                                          │
│    • FastAPI Backend: RESTful endpoints (/graph, /entities, /artifacts)   │
│    • Streamlit UI: Interactive Graph, Persona Dossier, Activity Timeline   │
│    • Analyst Review: Confirm / Reject linkages with instant recomputation │
│    • Export Engine: CSV / JSON bundles with embedded artifact provenance   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Correlation Engine & Scoring Model

### Signal Weight Matrix

The correlation engine processes cross-source persona pairs and sums weighted signals. Relationships with a composite score $\ge 0.30$ are surfaced to the analyst. Scores are strictly clamped to a maximum of **0.95** (reflecting inherent operational uncertainty).

| Signal | Weight | Direction | Condition | Rationale |
|---|:---:|:---:|---|---|
| **Shared PGP Fingerprint** | `+0.70` | Supporting | Identical 40-character hex key fingerprint | Strongest cryptographic link available |
| **Shared Crypto Wallet** | `+0.45` | Supporting | Identical base58 BTC/XMR address | High confidence financial infrastructure overlap |
| **Temporal Succession** | `+0.15` | Supporting | Persona A last seen $< 45$ days before Persona B first seen | Suggests rebrand, migration, or exit handoff |
| **Handle Similarity** | `+0.05` | Supporting | Levenshtein edit distance $\le 2$ | Low-weight corroborating signal |
| **Activity Overlap Conflict** | `−0.30` | Contradicting | Active time windows overlap concurrently | Strong evidence against a single operator |

$$\text{Score} = \min\left(0.95, \max\left(0.0, \sum \text{Weights}\right)\right)$$

### Ground Truth Seed Benchmark

The engine is verified against standardized test vectors defined in the project specification:

| Persona Pair | Discovered Signals | Calculated Score | Result Status | Diagnostic Notes |
|---|---|:---:|:---:|---|
| `nightjar` ↔ `n1ghtjar_` | PGP (`+0.70`), Wallet (`+0.45`) | **0.95** *(capped)* | `same_actor_suspected` | High confidence cross-marketplace link |
| `quillfeather` → `quill_v2` | Wallet (`+0.45`), Succession (`+0.15`) | **0.60** | `same_actor_suspected` | Migration / rebrand caught without PGP match |
| `nightjar` ↔ `nightjarr` | Handle (`+0.05`), Overlap (`−0.30`) | **0.00** | **NO EDGE** | **Correctly rejected.** Conflicting active windows prevent typosquat link |
| `bellwether` → `n1ghtjar_` | Wallet reference in post content | *N/A* | `transacted_with` | Interaction link only; **never** promoted to identity |

> **Key Takeaway:** A correct rejection (`nightjar` vs `nightjarr`) is a stronger sign of algorithmic integrity than a simple match. Naive systems produce a false link; GOTHAMITE discards it.

---

## Application Security & Threat Model

### Ingested Content as Inert Data

In dark web investigations, **the input data is authored by the adversaries under investigation**. Post content, profile signatures, and usernames are potential attack vectors designed to subvert analysis pipelines.

GOTHAMITE treats all ingested content as untrusted, inert strings:

1. **No Code Execution:** Ingested strings are never passed to `eval()`, `exec()`, `os.system()`, or unsafe deserializers (`pickle`).
2. **SQL Injection Defense:** All database interactions use SQLAlchemy parameterized queries. Zero raw string concatenation in SQL.
3. **No Prompt Injection:** Ingested dark web text is never passed into LLM contexts or system prompts.
4. **XSS & Dashboard Sanitization:** All user handles, identifiers, and raw content are explicitly escaped before rendering in Streamlit. Raw HTML tags are treated as plain text (`unsafe_allow_html=False`).
5. **Boundary Validation:** Payloads must pass strict schema validation:
   - Known `source_id` enumeration
   - Hex-validated 40-character PGP fingerprints
   - Valid cryptocurrency address formats
   - Strict 1 MB maximum artifact payload ceiling

### Attribution Safety & Language Rules

To maintain high evidentiary standards, strict linguistic constraints are enforced across code, UI strings, documentation, and exports:

| Never Use | Use Instead |
|---|---|
| *Identified / Deanonymized / Unmasked* | **Suspected same actor / Likely linked** |
| *Confirmed identity* | **Analyst-confirmed link** |
| *95% probability / 95% match* | **Confidence score 0.95** |
| *Proof / Proves* | **Evidence / Supports** |
| *The actor is X* | **Personas P and Q are likely the same operator** |

---

## Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11 | High performance, rich ecosystem for data engineering |
| **API Framework** | FastAPI + Pydantic v2 | High-speed asynchronous REST endpoints with automatic OpenAPI documentation |
| **Database & ORM** | SQLite + SQLAlchemy | Zero-friction setup; portable, relational, fully PostgreSQL-compatible schema |
| **Graph Modeling** | NetworkX | In-memory graph algorithms, topology traversals, dynamic reconstruction |
| **Analyst UI** | Streamlit | Rapid interactive dashboard with multi-page navigation and live state binding |
| **Graph Visualization** | `streamlit-agraph` / `pyvis` | Interactive force-directed node-link layouts with edge-click inspection |
| **Containerization** | Docker & Docker Compose | Uniform runtime packaging for backend, frontend, and database |
| **Export Formats** | CSV & JSON (RFC 8259) | Standard machine-readable formats with mandatory provenance hashes |

---

## Repository Structure

```
GOTHAMITE/
├── .env.example                       # Environment template
├── docker-compose.yml                 # Multi-container orchestration (backend + UI)
├── requirements.txt                   # Production Python dependencies
├── README.md                          # Project documentation and guide
│
├── backend/                           # Core API and Engine
│   ├── main.py                        # FastAPI application entrypoint
│   ├── db.py                          # SQLAlchemy engine, session maker, DB initialization
│   ├── models/
│   │   └── entities.py                # Normalized schema (Artifacts, Personas, Identifiers, Relationships, Evidence)
│   ├── services/
│   │   ├── ingest_service.py          # Ingest validation, SHA-256 verification, raw persistence
│   │   ├── correlation_service.py     # Deterministic cross-source scoring engine
│   │   ├── graph_service.py           # NetworkX graph builder and queries
│   │   └── export_service.py          # CSV/JSON export with provenance tracking
│   └── api/
│       ├── ingest.py                  # POST /api/v1/ingest
│       ├── correlate.py               # POST /api/v1/correlate
│       ├── graph.py                   # GET /api/v1/graph, PATCH /api/v1/graph/edge/{id}
│       ├── entities.py                # GET /api/v1/entities/search, /entities/persona/{id}
│       ├── artifacts.py               # GET /api/v1/artifacts/{id} (provenance lookup)
│       └── export.py                  # GET /api/v1/export
│
├── frontend/                          # Streamlit Analyst Workbench
│   ├── app.py                         # Workbench Home & Intelligence Overview
│   └── pages/
│       ├── 1_graph.py                 # Interactive Relationship Graph & Edge Evidence Inspector
│       ├── 2_dossier.py               # Persona Dossiers, Digital Fingerprints & Correlated Links
│       └── 3_timeline.py              # Temporal Activity Timeline & Rebrand Migration Tracking
│
├── scripts/
│   ├── seed_demo.py                   # Offline loader for standardized test corpus
│   └── run_correlation.py             # CLI runner for the correlation pipeline
│
└── Docs/                              # Comprehensive Specifications & Architectural Blueprints
    ├── GOTHAMITE_MASTER_CONTEXT.md    # Core mission, system boundaries, and scope lock
    ├── GOTHAMITE_PROBLEM_STATEMENT.md # Official NTRO SIH26151 problem statement breakdown
    ├── GOTHAMITE_ARCHITECTURE.md      # Detailed multi-tier architectural blueprint
    ├── GOTHAMITE_INVESTIGATION_PIPELINE.md # 10-stage lifecycle of threat observations
    ├── GOTHAMITE_REQUIREMENTS.md      # Capability matrix (Built vs Partial vs Cut)
    ├── GOTHAMITE_SECURITY.md          # Threat modeling, untrusted data handling & safety rules
    ├── GOTHAMITE_AI_DESIGN.md         # Rationale for deterministic correlation over black-box AI
    ├── GOTHAMITE_IMPLEMENTATION_PLAN.md # 6-phase gated build roadmap
    ├── GOTHAMITE_AGENT_TASK_SPLIT.md  # Agent engineering responsibilities & file ownership
    ├── GOTHAMITE_MASTER_PROMPT.md     # Primary prompt instructions and guardrails
    └── ROBIN_ANALYSIS.md              # Comparative OSINT architectural reference
```

---

## Getting Started

### Prerequisites

* **Python:** `3.11+`
* **Docker & Docker Compose:** *(Optional, for containerized run)*
* **Git**

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Tanish18906/GOTHAMITE.git
   cd GOTHAMITE
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Initialize environment variables:**
   ```bash
   cp .env.example .env
   ```

### Quickstart: Seed & Correlate

To test and verify the intelligence pipeline without external crawlers:

1. **Seed the database with test personas & artifacts:**
   ```bash
   python scripts/seed_demo.py
   ```

2. **Run the correlation pass:**
   ```bash
   python scripts/run_correlation.py
   ```

3. **Start the FastAPI backend server:**
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **In a separate terminal, launch the Streamlit Analyst Dashboard:**
   ```bash
   streamlit run frontend/app.py --server.port 8501
   ```

5. Open your browser and navigate to:
   - **Analyst Workbench UI:** `http://localhost:8501`
   - **Interactive API Docs (Swagger):** `http://localhost:8000/docs`

### Running with Docker Compose

To launch the complete platform in isolated containers:

```bash
docker compose up --build
```

Services will become accessible at:
* **Streamlit UI:** `http://localhost:8501`
* **FastAPI Backend:** `http://localhost:8000`

---

## Analyst Workflow & Dashboard

The Streamlit workbench provides an end-to-end investigative workspace across four views:

### 1. Intelligence Overview (`app.py`)
* System metrics: count of stored raw artifacts, personas, extracted identifiers, and computed relationships.
* Source reliability ratings and scan health metrics.
* Single-click **"Run Correlation Pass"** button to execute batch correlation on demand.

### 2. Force-Directed Graph Explorer (`pages/1_graph.py`)
* Nodes represent distinct personas, color-coded by originating dark web source.
* Edge thickness reflects the calibrated confidence score.
* **Evidence Panel:** Clicking an edge expands every supporting and contradicting signal, showing weight contribution, signal type, and direct links to the raw artifact.
* **Analyst Review Actions:** Buttons to **Confirm** or **Reject** proposed relationships. Rejecting an edge immediately hides it and recalculates the graph topology.

### 3. Actor Dossier (`pages/2_dossier.py`)
* Deep profile lookup for any selected handle:
  - Cryptographic keys (PGP fingerprints)
  - Financial markers (cryptocurrency wallets)
  - Suspected correlated personas across other marketplaces
  - Direct provenance links to source post artifacts

### 4. Activity Timeline (`pages/3_timeline.py`)
* Chronological visualization of actor activity across all monitored sources.
* Visually highlights **rebranding handoffs** (e.g., observing `quillfeather` activity terminating immediately prior to `quill_v2` emerging with the same crypto wallet).

---

## API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/ingest` | Ingests a raw artifact, upserts persona, and extracts identifiers |
| `POST` | `/api/v1/correlate` | Triggers a deterministic batch correlation pass |
| `GET` | `/api/v1/graph` | Returns all active graph nodes, scored edges, and metadata |
| `GET` | `/api/v1/graph/edge/{id}` | Retrieves all supporting/contradicting evidence for an edge |
| `PATCH` | `/api/v1/graph/edge/{id}` | Updates link status (`confirmed` / `rejected`) and triggers graph refresh |
| `GET` | `/api/v1/entities/search?q={query}` | Searches entities by handle, PGP fingerprint, or crypto wallet |
| `GET` | `/api/v1/entities/persona/{id}` | Returns comprehensive dossier and timeline for a persona |
| `GET` | `/api/v1/artifacts/{id}` | **Provenance Endpoint:** Returns the exact verbatim raw artifact |
| `GET` | `/api/v1/export?format=csv\|json` | Exports the current intelligence graph with embedded provenance |

---

## Documentation Index

Comprehensive documentation is available in the [`Docs/`](Docs/) directory:

| Document | Focus & Highlights |
|---|---|
| [**MASTER_CONTEXT.md**](Docs/GOTHAMITE_MASTER_CONTEXT.md) | Ground-truth context, project boundaries, scope lock, and core rules |
| [**PROBLEM_STATEMENT.md**](Docs/GOTHAMITE_PROBLEM_STATEMENT.md) | Official SIH26151 NTRO requirements and objective breakdown |
| [**ARCHITECTURE.md**](Docs/GOTHAMITE_ARCHITECTURE.md) | Technical architecture, data flow, component decoupling, and API contracts |
| [**INVESTIGATION_PIPELINE.md**](Docs/GOTHAMITE_INVESTIGATION_PIPELINE.md) | The 10-stage lifecycle of an observation from scraper to dashboard |
| [**REQUIREMENTS.md**](Docs/GOTHAMITE_REQUIREMENTS.md) | Honest mapping of requested vs built capabilities (preventing overclaiming) |
| [**SECURITY.md**](Docs/GOTHAMITE_SECURITY.md) | Adversarial input defenses, XSS sanitization, and attribution language policy |
| [**AI_DESIGN.md**](Docs/GOTHAMITE_AI_DESIGN.md) | Rationale for deterministic scoring and why LLMs are excluded from attribution |
| [**IMPLEMENTATION_PLAN.md**](Docs/GOTHAMITE_IMPLEMENTATION_PLAN.md) | 6-phase gated development roadmap with strict verification gates |
| [**AGENT_TASK_SPLIT.md**](Docs/GOTHAMITE_AGENT_TASK_SPLIT.md) | Engineering ownership boundaries across backend and frontend |
| [**ROBIN_ANALYSIS.md**](Docs/ROBIN_ANALYSIS.md) | OSINT architectural benchmark comparing GOTHAMITE with open-source tools |

---

## Team & Acknowledgements

* **Team:** AvivCREW
* **Lead Developer & Maintainer:** [Tanish Mishra](https://github.com/Tanish18906) (`@Tanish18906`)
* **Event:** Smart India Hackathon (SIH 2026)
* **Organization:** National Technical Research Organisation (NTRO)

---

## License

This project is developed for educational and research purposes under the Smart India Hackathon 2026 framework. Strictly intended for authorized investigative workflows under lawful process.
