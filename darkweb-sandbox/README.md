# darkweb-sandbox

> **Simulated Onion-Routed Network & Hidden Service Collection Layer**  
> **Team Shankh_AvivCREW** | **Smart India Hackathon 2026**  
> *Authoritative Companion Repository to the GOTHAMITE Threat Intelligence Platform*

---

## 1. Overview

`darkweb-sandbox` is an isolated, simulated onion-routed network containing synthetic dark web forums and marketplaces, coupled with an automated scraper agent. It serves as the upstream collection environment for the **GOTHAMITE** threat actor intelligence platform.

Its primary purpose is to demonstrate—visibly, deterministically, and ethically—how GOTHAMITE's collection pipeline traverses multi-hop hidden routing infrastructure to discover threat actor handles, PGP keys, and cryptocurrency wallets, **without ever connecting to the real Tor network or touching real illicit services**.

```
┌─────────────────────────────────────────────────────────────┐
│                 darkweb-sandbox (This Repo)                 │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐  │
│  │   forum-alpha    │  │ marketplace-beta │  │forum-gamma│  │
│  └────────┬─────────┘  └────────┬─────────┘  └─────┬─────┘  │
│           ▲                     ▲                  ▲        │
│           └──────────────┬──────┴──────────────────┘        │
│                          │ Routed via Internal Net          │
│            ┌─────────────┴─────────────┐                    │
│            │  Relay Pool (7 Nodes)     │                    │
│            │  + Directory Service      │                    │
│            └─────────────▲─────────────┘                    │
│                          │ Multi-Hop Onion Circuit          │
│            ┌─────────────┴─────────────┐                    │
│            │       onion_client        │                    │
│            └─────────────▲─────────────┘                    │
│                          │ Internal API                     │
│            ┌─────────────┴─────────────┐                    │
│            │       scraper_agent       │                    │
│            └─────────────┬─────────────┘                    │
└──────────────────────────┼──────────────────────────────────┘
                           │ POST /api/v1/ingest (API_CONTRACT.md)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      GOTHAMITE Backend                      │
│        (Ingestion → Graph Engine → Correlation Dashboard)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. System Reality Matrix

To ensure absolute integrity and clarity during technical evaluations and live demonstrations, the system delineates real technical implementations from deliberate sandbox simplifications:

| Claim / Component | Status | Technical Implementation |
|---|---|---|
| **Layered Encryption** | **REAL** | Per-hop onion peeling using standard AES-256-GCM (96-bit nonce) and RSA-2048-OAEP (SHA-256) via Python `cryptography`. |
| **Relay Isolation** | **REAL** | Relays execute in independent Docker containers with distinct ephemeral in-memory keypairs. |
| **Zero-Knowledge Next Hop** | **REAL** | Each relay decrypts exactly one layer, learns only its immediate predecessor and successor, and cannot inspect the origin or destination. |
| **Dynamic Path Selection** | **REAL** | Circuits are selected at random per session from available nodes via the directory service (`GET /path?hops=N`). |
| **Relay Pool Scale** | **SIMPLIFIED** | Fixed pool of 5–7 isolated relay containers rather than a global distributed volunteer network. |
| **Directory Service** | **SIMPLIFIED** | In-memory registry for health checks and route generation; no 9-authority consensus voting or BFT protocol. |
| **Service Resolution** | **SIMPLIFIED** | Direct container DNS resolution for `.onion.mock` endpoints; distributed hash table (DHT) descriptor lookups omitted. |
| **Marketplace & Forum Content** | **SYNTHETIC** | 100% deterministic, invented data. No scraped data from real marketplaces or forums. |

---

## 3. Architecture & Core Subsystems

### 3.1 Relay Pool (`relay/`)
- **Containerized Relay Nodes**: 5 to 7 independent Dockerized services (`relay-01` through `relay-07`).
- **Ephemeral Keypairs**: On boot, each relay generates an in-memory RSA-2048 keypair and publishes its public key to the directory service. Private keys never touch disk or network payloads.
- **Layer Peeling & Return Re-encryption**: Decrypts incoming outer layer, validates headers, routes the opaque inner ciphertext to the next hop, and symmetrically wraps return traffic on the return leg.

### 3.2 Directory Service (`directory/`)
- **In-Memory Registry**: Tracks active relays (`relay_id`, `host`, `port`, `public_key`, `status`).
- **Route Generation (`GET /path?hops=N`)**: Selects $N$ distinct active relays uniformly at random without replacement. Ensures a new randomized route is used across runs.
- **Observability (`GET /relays`)**: Real-time status reporting for demonstration monitoring.

### 3.3 Onion Client (`client/`)
- **Layered Construction**: Builds nested onion packets innermost-first using the public keys of the assigned route path.
- **Hybrid Cryptography**: Employs asymmetric RSA-OAEP for per-hop symmetric session key exchange, and symmetric AES-GCM for packet payload encryption.

### 3.4 Synthetic Hidden Services (`mock-sites/`)
Three containerized web services running on an isolated internal Docker bridge network with **no host port mappings** (reachable solely through the relay pool):

| Service | Synthetic Host | Archetype | Hosted Personas |
|---|---|---|---|
| `forum-alpha` | `alpha7fq2mx9k.onion.mock` | Underground Discussion Forum | `nightjar` (A1), `quillfeather` (B1) |
| `marketplace-beta` | `beta4np8vz3wc.onion.mock` | Vendor Marketplace | `n1ghtjar_` (A2), `bellwether` (D1) |
| `forum-gamma` | `gamma2xd6bt5hy.onion.mock` | Technical Breach Forum | `quill_v2` (B2), `nightjarr` (C1) |

- **Deterministic Planted Links**: Features planted correlation artifacts (matching PGP fingerprints, shared cryptocurrency wallet addresses, and rebrand narratives) alongside decoy profiles to test GOTHAMITE's entity resolution algorithms.

### 3.5 Scraper Agent (`scraper/`)
- **Strict Onion Routing**: Routes 100% of HTTP traffic via `onion_client.py`; direct socket connections to mock sites are structurally prevented.
- **Closed Source Bounds**: Strictly bounded to configured seed sites; no outward link following or unbounded crawling.
- **Inert Data Handling**: Treats all scraped markup as untrusted payload data (never evaluated, executed, or passed into shell/interpreter environments).
- **GOTHAMITE Submission**: Normalizes extracted handles, PGP fingerprints, crypto addresses, and SHA-256 page hashes, dispatching them to `POST /api/v1/ingest`.

---

## 4. GOTHAMITE Ingestion Seam

`API_CONTRACT.md` serves as the sole seam between `darkweb-sandbox` and `GOTHAMITE`. Extracted artifacts conform to the following JSON structure:

```json
{
  "source_id": "forum-alpha",
  "source_type": "forum",
  "page_type": "item",
  "url": "http://alpha7fq2mx9k.onion.mock/thread/14",
  "collected_at": "2026-09-06T14:22:31Z",
  "relay_path": ["relay-05", "relay-02", "relay-07"],
  "raw_content": "<!DOCTYPE html><html>...</html>",
  "content_hash": "sha256:4f3a98...",
  "persona": {
    "handle": "nightjar",
    "observed_at": "2026-03-11T09:14:00Z"
  },
  "identifiers": [
    {
      "type": "pgp_fingerprint",
      "value": "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D",
      "observed_at": "2026-03-11T09:14:00Z"
    },
    {
      "type": "wallet",
      "value": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
      "observed_at": "2026-03-11T09:14:00Z"
    }
  ]
}
```

---

## 5. Non-Negotiable Safety & Ethical Rules

1. **Zero Real Tor / Dark Web Interaction**: No real Tor relays, `.onion` services, or live dark web networks are ever contacted. All mock addresses use the `.onion.mock` TLD.
2. **No Real Illicit Data**: All personas, forum threads, marketplace listings, and credentials are pure synthetic fixtures.
3. **No Hand-Rolled Cryptography**: Cryptographic operations strictly employ standard primitives from Python’s verified `cryptography` library.
4. **Scraped Content is Inert**: Scraped content is parsed as static strings and never executed or evaluated.

---

## 6. Repository Layout & Documentation

```
darkweb-sandbox/
├── README.md                           # Master system documentation
├── requirements.txt                    # Phase-1 runtime dependency (cryptography only)
├── Dockerfile                          # Single image shared by every Phase-1 service
├── docker-compose.yml                  # Directory + 7 relays + Phase-1 endpoint
├── common/                             # Shared crypto envelope and HTTP helpers
│   ├── onion_crypto.py                 # RSA-OAEP + AES-GCM layer/response codec
│   └── http_util.py                    # JSON-over-HTTP helpers
├── directory/                          # In-memory relay registry and path selection
│   └── directory_service.py
├── relay/                              # Relay node: one-layer peeling and forwarding
│   └── relay_node.py
├── client/                             # Onion client: nested layers, ordered unwrap
│   └── onion_client.py
├── phase1_endpoint/                    # Phase-1 connectivity target (superseded at Phase 4)
│   └── static_endpoint.py
├── mock_sites/                         # Phase-4 synthetic sites (SPEC_DECISIONS.md SD-020)
│   ├── seed_data.py                    # Hardcoded personas, identifiers, and posts
│   ├── site_server.py                  # One server for all three sites, keyed by SITE_ID
│   └── docker-compose.sites.yml        # forum-alpha, marketplace-beta, forum-gamma
├── scripts/                            # Demo runners
│   ├── phase1_demo.py
│   └── phase4_demo.py
├── tests/                              # Verification suites
│   ├── harness.py
│   ├── test_phase1.py
│   └── test_phase4.py
├── AgentsDocs/                         # System specifications & architectural contracts
│   ├── MASTER_CONTEXT.md               # Scope lock, design rules, and requirements
│   ├── IMPLEMENTATION_PLAN.md          # 6-phase roadmap and gate criteria
│   ├── RELAY_PROTOCOL.md               # Wire protocol, cryptographic envelope, and layer spec
│   ├── DIRECTORY_SPEC.md               # Directory registry and path selection spec
│   ├── MOCK_SITES_SPEC.md              # Mock sites layout and synthetic persona spec
│   ├── SCRAPER_AGENT_SPEC.md           # Scraper crawl loop, extraction rules, and limits
│   ├── API_CONTRACT.md                 # Single ingestion interface definition for GOTHAMITE
│   ├── DATA_MODEL.md                   # Authoritative entity and identifier schema
│   ├── SPEC_DECISIONS.md               # Engineering decisions resolving spec blockers
│   └── reports/                        # Phase gate reports
│       ├── PHASE_1_REPORT.md
│       └── PHASE_4_REPORT.md
└── format/                             # Agent prompts, execution splits, and demo guides
    ├── MASTER_PROMPT.md                # System prompt and operational constraints
    ├── AGENT_TASK_SPLIT.md             # Ownership demarcation between parallel agents
    └── DEMO_SCRIPT.md                  # Hackathon presentation and live demonstration script
```

---

## 7. Implementation Roadmap & Phases

Development follows a strict phase-gate protocol documented in `AgentsDocs/IMPLEMENTATION_PLAN.md`:

- [x] **Phase 1: Single Hop & Proven Cryptography** — Single relay, mock endpoint, and layered RSA-OAEP + AES-GCM cryptographic verification.
- [x] **Phase 2: Directory Service** — Dynamic registration of 5–7 relays and randomized circuit path generation (`GET /path?hops=N`).
- [x] **Phase 3: Multi-Hop Layered Routing** — Nested 3-hop circuit construction, per-hop layer peeling, return leg re-encryption, and intermediate node blind forwarding.
- [x] **Phase 4: Synthetic Mock Sites** — Containerized deployment of `forum-alpha`, `marketplace-beta`, and `forum-gamma` with planted identifiers and cross-site linkages.
- [x] **Phase 5: Scraper Agent** — Automated crawl loop over `onion_client`, structured identifier extraction, and schema-validated dispatch to GOTHAMITE.
- [x] **Phase 6: Integration & Demo Hardening** — End-to-end `docker compose` validation, cold-start repeatability, and demo rehearsal.

> **Current status (2026-10-03).** Phases 1–6 are implemented (commit `46daed4`). The 171 unit
> tests pass (`python -m unittest discover -s tests -t .`). On the same date the Docker stack
> (directory, 7 relays, 3 mock sites) was run end to end: the scraper agent fetched 57 pages over
> 3-hop circuits and GOTHAMITE's ingest accepted 48. The 9 rejected pages are 3 index pages with
> no persona and 6 profile pages with no `observed_at`, both required by the ingest API; they
> carry no identifiers. The image does not include `scraper/`, so the run mounted it with
> `-v ./scraper:/app/scraper:ro`. Reports are in `AgentsDocs/reports/`,
> and the engineering decisions are recorded in `AgentsDocs/SPEC_DECISIONS.md`.
> The `docker compose` stack is **executed and verified**: seven relays register,
> `GET /path?hops=3` returns varying paths, and a 3-hop carry to
> `phase1sandbox.onion.mock` completes over `sandbox-net` with the §6 visibility
> table holding in the container logs.

---

## 8. Development & Quickstart

### Prerequisites
- Docker Engine 24.0+ & Docker Compose v2.20+
- Python 3.11+
- Virtual environment (`venv`) with `cryptography` (Phase 1). `requests` and
  `beautifulsoup4` are Phase-5 scraper dependencies and are not needed yet.

### Local setup

```bash
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

### Run the Phase-1 demo (no Docker required)

Starts the directory, seven relays and the Phase-1 endpoint on loopback ports,
then carries two requests through two different paths and prints what each relay
can decrypt:

```bash
python -m scripts.phase1_demo
```

### Run the tests

171 tests. Phase 1 (38) covers layer construction, the visibility table, nonce
discipline, log hygiene, invalid input and relay failure. Phase 4 (42) crawls all
three mock sites through real 3-hop paths and checks the planted corpus — including
that no page carries an identifier belonging to another persona. The Phase 5 and demo-viewer
suites cover the scraper and the bridge, and `test_collect_loop` covers the collection loop. No test touches the network:

```bash
python -m unittest discover -s tests -t . -v
```

### Scheduled collection loop (local, simulated network only)

`scripts/collect_loop.py` runs the scraper on an interval. Each cycle crawls the
three mock sites one at a time through the relay network, posts every page to
GOTHAMITE's `POST /api/v1/ingest`, calls `POST /api/v1/correlate`, and prints a
per-source summary (status, page counts, last successful scan). A source that
fails is logged and the others still run. It is started by hand, runs locally,
reaches only `.onion.mock` addresses, and is not part of the hosted demo.

| Option | Meaning | Default |
| --- | --- | --- |
| `--interval` | minutes between cycle starts | `10` |
| `--cycles` | number of cycles; `0` runs until Ctrl+C | `0` |
| `--backend` | base URL of a local GOTHAMITE `backend.main` | `http://127.0.0.1:8000` |
| `--directory` | relay directory URL | `http://directory:8000` |

The relays are reachable only inside `sandbox-net`, so the loop runs in a
container. The image does not include `scraper/` or `scripts/`, so they are
mounted. Inside a container `127.0.0.1` is the container itself, so pass
`--backend`. Start `backend.main` on the host with
`GOTHAMITE_PUBLIC_URL=http://host.docker.internal` so it accepts that host name:

```bash
docker compose -f docker-compose.yml -f mock_sites/docker-compose.sites.yml run --rm -T \
    -v "$PWD/scraper:/app/scraper:ro" -v "$PWD/scripts:/app/scripts:ro" \
    --entrypoint python directory -m scripts.collect_loop \
    --directory http://directory:8000 --backend http://host.docker.internal:8044 \
    --interval 10 --cycles 3
```

The loop opens a workbench session first. The session cookie and the CSRF token
are sent only to the backend's host. `last_scan` in the summary is the loop's own
record; GOTHAMITE stores a scan time at ingest, but no API or screen shows it yet.
Tests: `tests/test_collect_loop.py` (fake agent and clock, no network).

### Run a single request by hand

```bash
python -m client.onion_client --directory http://localhost:8000 --hops 3 \
    --host phase1sandbox.onion.mock --resource /
```

### Quick Start (Docker — verified)
```bash
# Clone repository
git clone https://github.com/axmitk/GOTHAMITE-Intelligence-Suite.git
cd GOTHAMITE-Intelligence-Suite/darkweb-sandbox

# Phase 1: directory + 7 relays + the Phase-1 endpoint
docker compose up --build -d

# Verify relay pool health -- verified: count=7, relay-01..relay-07 all "up"
curl http://localhost:8000/relays

# Request a randomized 3-hop circuit
curl "http://localhost:8000/path?hops=3"

# Phase 4 onward: layer the three mock sites on top
docker compose -f docker-compose.yml -f mock_sites/docker-compose.sites.yml up -d

# The sites publish no host port, by design. This must FAIL:
curl http://localhost/

# Reach them only through the relay chain:
docker compose run --rm --entrypoint python directory -m client.onion_client     --directory http://directory:8000 --hops 3     --host alpha7fq2mx9k.onion.mock --resource /thread/14
```

---

## 9. License

Developed for educational, research, and hackathon evaluation purposes for **Smart India Hackathon 2026** by **Team Shankh_AvivCREW**.
