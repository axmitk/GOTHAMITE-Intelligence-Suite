<div align="center">
    <h1>GOTHAMITE INTELLIGENCE SUITE</h1>
    <p><b>Advanced Cyber-Intelligence & Entity Resolution Platform</b></p>
    <a href="https://github.com/axmitk/GOTHAMITE-Intelligence-Suite"><img alt="Version" src="https://img.shields.io/badge/version-2.0.0-blue.svg?style=flat-square"></a>
    <a href="https://github.com/axmitk/GOTHAMITE-Intelligence-Suite"><img alt="Status" src="https://img.shields.io/badge/status-production_ready-success.svg?style=flat-square"></a>
    <a href="https://github.com/axmitk/GOTHAMITE-Intelligence-Suite"><img alt="License" src="https://img.shields.io/badge/license-MIT-darkgray.svg?style=flat-square"></a>
    <br><br>
    <p>An end-to-end operational intelligence platform engineered for deep-web source monitoring, multi-factor entity resolution, and explainable intelligence correlation. GOTHAMITE transforms fragmented digital observations into a unified, actionable intelligence dossier.</p>
    <a href="#architecture">Architecture</a> &bull; <a href="#nist-csf-integration">NIST CSF Integration</a> &bull; <a href="#core-capabilities">Core Capabilities</a> &bull; <a href="#installation-and-deployment">Installation</a>
</div>

<br>

<div align="center">
  <img src="gothamite/frontend-react/scripts/overview_rendered.png" alt="GOTHAMITE Dashboard" width="800">
</div>

<br>

## Architecture

The GOTHAMITE platform operates on a robust data-fusion pipeline designed to minimize analyst fatigue and maximize actionable intelligence. The system continuously ingests, normalizes, and scores data from multiple external vectors.

<b>Entity Resolution & Correlation Pipeline</b>

| Pipeline Stage | Module | Technique / Technology |
|---|---|---|
| **Collection** | darkweb-sandbox/bridge_collector.py | Headless autonomous scraping of authenticated .onion environments |
| **Extraction** | ackend/services/ingest_service.py | NER, REGEX parsing for Handles, Emails, PGP Keys, and Crypto Wallets |
| **Normalization** | ackend/api/ingest.py | Data standardization (e.g. whitespace stripping for precise PGP matching) |
| **Correlation** | ackend/services/correlation_service.py | Cross-referencing identifiers to build confidence-scored deterministic linkage |
| **Analysis** | rontend/views/graph_view.py | 3D visual analysis of the identity relationship graph (streamlit-agraph / 3d-force-graph) |
| **Risk Engine** | rontend/views/investigation_view.py | Multi-factor risk scoring based on exposure, correlation strength, and activity |

<br>

## NIST CSF Integration

The GOTHAMITE user interface is designed as a professional cyber-intelligence workstation, operationally mapping directly to the National Institute of Standards and Technology (NIST) Cybersecurity Framework to guide analysts through a disciplined investigation cycle.

<table>
  <tr>
    <td width="20%"><b>IDENTIFY</b></td>
    <td>Asset and entity discovery, threat surface mapping, and digital identity resolution queues.</td>
  </tr>
  <tr>
    <td><b>DETECT</b></td>
    <td>Continuous intelligence collection, source health monitoring, and intelligence-driven alerts.</td>
  </tr>
  <tr>
    <td><b>PROTECT</b></td>
    <td>Risk prioritization, exposure assessment, and high-value entity identification.</td>
  </tr>
  <tr>
    <td><b>RESPOND</b></td>
    <td>3D visual analysis of resolved identities, infrastructure sharing, and chronological timeline construction.</td>
  </tr>
  <tr>
    <td><b>RECOVER</b></td>
    <td>Generation of comprehensive intelligence dossiers preserving evidence provenance and investigation history.</td>
  </tr>
</table>

<br>

## Core Capabilities

<b>Transparent Cross-Source Correlation</b><br>
Unlike black-box AI platforms, GOTHAMITE provides explainable linkage. Every relationship in the 3D entity graph is backed by a specific evidence node (e.g., matching PGP signatures across two distinct marketplaces) and assigned a confidence score.

<b>Investigation Timeline Construction</b><br>
Events from completely disparate sources are merged into a single chronological timeline, allowing analysts to trace the evolution of a threat actor's infrastructure from profile creation to credential exposure.

<b>Automated Dossier Generation</b><br>
The platform compiles all collected artifacts, resolved identities, correlated aliases, and risk assessments into a single actionable report ready for incident response teams.

<br>

## Technology Stack

- **Frontend**: Streamlit + React (Custom 3D Force Graph via Three.js)
- **Backend API**: FastAPI (Python 3.11+)
- **Relational Store**: SQLite / PostgreSQL (SQLAlchemy ORM)
- **Deployment**: Docker + Docker Compose (Isolated microservices)
- **Collection**: Headless autonomous crawlers and Open-Web Browser Intelligence plugins

<br>

## Installation and Deployment

GOTHAMITE utilizes a containerized microservice architecture, allowing for isolated and reproducible deployments.

<b>Prerequisites</b><br>
Ensure Docker and Docker Compose are installed on your host system.

<b>Deploying the Workstation</b><br>
Navigate to the primary application directory and initialize the containers. The analyst workstation will be available at http://localhost:8501.

`ash
cd gothamite
docker compose up --build -d
`

<b>Initializing Synthetic Intelligence Sources</b><br>
For demonstration and testing purposes, the platform includes a sandbox of simulated intelligence sources.

`ash
cd darkweb-sandbox/mock_sites
docker compose -f docker-compose.sites.yml up -d
`

<b>Running the Autonomous Collector</b><br>
Execute the collection script to simulate the intelligence pipeline scraping the mock .onion sites, extracting entities, and pushing them to the GOTHAMITE ingest API.

`ash
cd darkweb-sandbox
python bridge_collector.py
`

<br>

## Demonstration Scenario

The included synthetic dataset provides a highly deterministic investigation narrative, ideal for presentations or capability demonstrations.

1. <b>Discover:</b> Search for the entity 
ightjar.
2. <b>Collect:</b> Observe that 
ightjar operates on orum-gamma.
3. <b>Correlate:</b> The engine identifies a shared PGP fingerprint, linking 
ightjar to the known threat actor en0m.
4. <b>Graph:</b> The 3D entity graph visually maps this connection, highlighting the HIGH confidence score due to the deterministic key match.
5. <b>Timeline:</b> The chronological view reveals en0m was previously active on marketplace-beta, exposing a cryptocurrency wallet.
6. <b>Risk Assessment:</b> The entity's risk automatically elevates to CRITICAL due to cross-source confirmation and marketplace activity.
7. <b>Report:</b> Generate the final Intelligence Dossier for the unified identity.

<br>
<div align="center">
    <p><i>Developed for SIH 2026</i></p>
</div>
