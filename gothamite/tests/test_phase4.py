import csv
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, get_db
from backend.main import app
from backend.models.entities import Persona, Identifier, Relationship, Evidence, Artifact
from backend.services.correlation_service import CorrelationService
from backend.services.graph_service import GraphService
from scripts.seed_demo import seed_database


@pytest.fixture
def seeded_client_and_db():
    """Sets up an isolated SQLite in-memory test database, seeds it, correlates it, and yields TestClient."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    seed_database(session)
    CorrelationService.run_correlation(session)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal
    app.dependency_overrides.clear()
    session.close()


def test_get_graph_endpoint(seeded_client_and_db):
    """Acceptance Criterion 1: GET /graph returns nodes + edges + scores."""
    client, _ = seeded_client_and_db
    res = client.get("/api/v1/graph")
    assert res.status_code == 200
    data = res.json()

    assert "nodes" in data
    assert "edges" in data
    assert data["node_count"] == 6
    assert data["edge_count"] == 3

    # Check node fields
    for node in data["nodes"]:
        assert "id" in node
        assert "handle" in node
        assert "source_id" in node
        assert "post_count" in node

    # Check edge fields
    handles_linked = {(e["from_handle"], e["to_handle"]) for e in data["edges"]}
    assert ("nightjar", "n1ghtjar_") in handles_linked or ("n1ghtjar_", "nightjar") in handles_linked
    assert ("quillfeather", "quill_v2") in handles_linked or ("quill_v2", "quillfeather") in handles_linked
    assert ("bellwether", "n1ghtjar_") in handles_linked


def test_get_edge_evidence(seeded_client_and_db):
    """Acceptance Criterion 2: GET /graph/edge/{id} returns every evidence row with weight, direction, artifact_id."""
    client, _ = seeded_client_and_db
    # Get all edges first
    graph_res = client.get("/api/v1/graph").json()
    edge = graph_res["edges"][0]
    rel_id = edge["id"]

    res = client.get(f"/api/v1/graph/edge/{rel_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["relationship_id"] == rel_id
    assert "from_persona" in data
    assert "to_persona" in data
    assert "evidence" in data
    assert len(data["evidence"]) > 0

    for ev in data["evidence"]:
        assert "weight" in ev
        assert "direction" in ev
        assert ev["direction"] in ["supporting", "contradicting"]
        assert "artifact_id" in ev
        assert len(ev["artifact_id"]) > 0
        assert "note" in ev


def test_patch_edge_status_and_rejection_filter(seeded_client_and_db):
    """Acceptance Criterion 3: PATCH /graph/edge/{id} sets confirmed/rejected; rejected disappears from /graph."""
    client, _ = seeded_client_and_db
    graph_before = client.get("/api/v1/graph").json()
    rel_to_reject = graph_before["edges"][0]["id"]
    initial_edge_count = graph_before["edge_count"]

    # 1. Reject edge
    patch_res = client.patch(f"/api/v1/graph/edge/{rel_to_reject}", json={"status": "rejected"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "rejected"

    # 2. Verify edge disappeared from /graph
    graph_after = client.get("/api/v1/graph").json()
    assert graph_after["edge_count"] == initial_edge_count - 1
    edge_ids_after = [e["id"] for e in graph_after["edges"]]
    assert rel_to_reject not in edge_ids_after

    # 3. Confirm another edge
    rel_to_confirm = graph_after["edges"][0]["id"]
    patch_confirm = client.patch(f"/api/v1/graph/edge/{rel_to_confirm}", json={"status": "confirmed"})
    assert patch_confirm.status_code == 200
    assert patch_confirm.json()["status"] == "confirmed"

    # Edge remains in /graph with confirmed status
    graph_confirmed = client.get("/api/v1/graph").json()
    confirmed_edge = next(e for e in graph_confirmed["edges"] if e["id"] == rel_to_confirm)
    assert confirmed_edge["status"] == "confirmed"


def test_entities_search(seeded_client_and_db):
    """Acceptance Criterion 4: GET /entities/search?q= finds by handle, PGP fingerprint and wallet."""
    client, _ = seeded_client_and_db

    # 1. Search by handle
    res_handle = client.get("/api/v1/entities/search?q=night")
    assert res_handle.status_code == 200
    data_handle = res_handle.json()
    handles_found = [r["handle"] for r in data_handle["results"]]
    assert "nightjar" in handles_found
    assert "nightjarr" in handles_found

    # 2. Search by PGP fingerprint
    res_pgp = client.get("/api/v1/entities/search?q=9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D")
    assert res_pgp.status_code == 200
    data_pgp = res_pgp.json()
    pgp_handles = [r["handle"] for r in data_pgp["results"]]
    assert "nightjar" in pgp_handles or "n1ghtjar_" in pgp_handles

    # 3. Search by cryptocurrency wallet
    res_wallet = client.get("/api/v1/entities/search?q=1Kp7dR3zXw9QfM4vB2nHtL6sYcJ8gAeU5o")
    assert res_wallet.status_code == 200
    data_wallet = res_wallet.json()
    wallet_handles = [r["handle"] for r in data_wallet["results"]]
    assert "quillfeather" in wallet_handles or "quill_v2" in wallet_handles


def test_entities_persona_dossier(seeded_client_and_db):
    """Acceptance Criterion 5: GET /entities/persona/{id} returns identifiers, links, timeline, sources."""
    client, session_factory = seeded_client_and_db
    db = session_factory()
    try:
        p = db.query(Persona).filter_by(handle="nightjar").first()
        persona_id = p.persona_id
    finally:
        db.close()

    res = client.get(f"/api/v1/entities/persona/{persona_id}")
    assert res.status_code == 200
    dossier = res.json()

    assert dossier["handle"] == "nightjar"
    assert dossier["source_id"] == "forum-alpha"
    assert "identifiers" in dossier
    assert len(dossier["identifiers"]) >= 2
    assert "correlated_links" in dossier
    assert len(dossier["correlated_links"]) >= 1
    assert "timeline" in dossier
    assert len(dossier["timeline"]) >= 1


def test_artifact_provenance_endpoint(seeded_client_and_db):
    """Acceptance Criterion 6: GET /artifacts/{id} returns the raw stored artifact."""
    client, session_factory = seeded_client_and_db
    db = session_factory()
    try:
        art = db.query(Artifact).first()
        art_id = art.artifact_id
        expected_raw = art.raw_content
        expected_hash = art.content_hash
    finally:
        db.close()

    res = client.get(f"/api/v1/artifacts/{art_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["artifact_id"] == art_id
    assert data["raw_content"] == expected_raw
    assert data["content_hash"] == expected_hash
    assert "collected_at" in data
    assert "relay_path" in data


def test_export_json_and_csv(seeded_client_and_db):
    """Acceptance Criterion 7: CSV and JSON export both include artifact_id on every evidence row."""
    client, _ = seeded_client_and_db

    # 1. JSON Export
    res_json = client.get("/api/v1/export?format=json")
    assert res_json.status_code == 200
    data_json = res_json.json()
    assert "nodes" in data_json
    assert "relationships" in data_json

    for rel in data_json["relationships"]:
        for ev in rel["evidence"]:
            assert "artifact_id" in ev
            assert len(ev["artifact_id"]) > 0, "JSON export evidence missing artifact_id!"

    # 2. CSV Export
    res_csv = client.get("/api/v1/export?format=csv")
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    csv_text = res_csv.text

    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) > 0

    assert "artifact_id" in reader.fieldnames
    for row in rows:
        if row["signal_type"]:  # if this is an evidence row
            assert len(row["artifact_id"]) > 0, f"CSV export row missing artifact_id: {row}"


def test_graph_service_stateless(seeded_client_and_db):
    """Acceptance Criterion 8: Graph service holds no state between requests."""
    _, session_factory = seeded_client_and_db
    db = session_factory()
    try:
        g1 = GraphService.build_networkx_graph(db)
        g2 = GraphService.build_networkx_graph(db)
        assert g1 is not g2, "GraphService must instantiate a fresh graph object per invocation"
        assert len(g1.nodes) == len(g2.nodes)
        assert len(g1.edges) == len(g2.edges)
    finally:
        db.close()
