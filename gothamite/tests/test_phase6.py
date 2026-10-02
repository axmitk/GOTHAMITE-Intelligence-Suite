"""
Phase 6 Acceptance Test Suite: Integration, Packaging & Demo Hardening.
Verifies:
1. Packaging files exist and are valid (Dockerfile, docker-compose.yml, .env.example, DEMO_SCRIPT.md).
2. Fallback path works autonomously: fresh DB -> seed_demo -> run_correlation -> dashboard/api ready.
3. Cold start to populated graph runs in seconds (well under the 2-minute threshold).
4. Three consecutive end-to-end pipeline executions run with zero failures and total idempotency.
5. All 6 benchmark personas, 4 expected relationships, and exact evidence scores hold.
6. Export functionality (CSV/JSON) with mandatory artifact_id provenance.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base
from backend.main import app
from backend.models.entities import Persona, Artifact, Identifier, Relationship, Evidence, Source
from backend.services.correlation_service import CorrelationService
from backend.services.graph_service import GraphService
from backend.services.export_service import ExportService
from scripts.seed_demo import seed_database, verify_seed_invariants

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_phase6_packaging_files_exist():
    """Verifies all required Phase 6 deployment and documentation assets exist and are non-empty."""
    assert (PROJECT_ROOT / "Dockerfile").is_file(), "Dockerfile missing"
    assert (PROJECT_ROOT / "docker-compose.yml").is_file(), "docker-compose.yml missing"
    assert (PROJECT_ROOT / ".env.example").is_file(), ".env.example missing"
    assert (PROJECT_ROOT / ".dockerignore").is_file(), ".dockerignore missing"
    assert (PROJECT_ROOT / "DEMO_SCRIPT.md").is_file(), "DEMO_SCRIPT.md missing"

    dockerfile_content = (PROJECT_ROOT / "Dockerfile").read_text()
    assert "python:3.11-slim" in dockerfile_content
    assert "requirements.txt" in dockerfile_content
    assert "uvicorn" in dockerfile_content

    compose_content = (PROJECT_ROOT / "docker-compose.yml").read_text()
    assert "backend:" in compose_content
    assert "frontend:" in compose_content
    assert "8000:8000" in compose_content
    assert "8501:8501" in compose_content
    assert "API_BASE_URL" in compose_content

    demo_script = (PROJECT_ROOT / "DEMO_SCRIPT.md").read_text()
    assert "nightjar" in demo_script
    assert "quillfeather" in demo_script
    assert "nightjarr" in demo_script
    assert "0.95" in demo_script
    assert "0.40" in demo_script


def test_phase6_cold_start_and_fallback_path():
    """
    Acceptance Criterion 3 & 4:
    Fallback path works completely with external sandbox absent.
    Cold start to visible graph completes in seconds (under 2 minutes).
    """
    start_time = time.time()

    # Create isolated in-memory DB
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()

    try:
        # Step 1: Run seed loader
        seed_database(db)
        verify_seed_invariants(db)

        # Step 2: Run correlation engine
        result = CorrelationService.run_correlation(db)
        assert result["status"] == "success"
        assert result["relationships_created"] == 3  # 2 identity links + 1 transaction link
        assert result["evaluated_pairs"] > 0

        # Step 3: Query graph payload for dashboard
        graph = GraphService.get_graph_payload(db)
        assert len(graph["nodes"]) == 6
        assert len(graph["edges"]) == 3  # 2 identity + 1 transaction

        # Step 4: Verify headline attribution
        edge_map = {f"{e['from_handle']}->{e['to_handle']}": e for e in graph["edges"]}
        assert any(e["score"] == 0.95 for e in graph["edges"]), "Headline 0.95 edge missing"
        assert any(e["score"] == 0.40 for e in graph["edges"]), "Rebrand 0.40 edge missing"
        assert any(e["type"] == "transacted_with" for e in graph["edges"]), "Transaction edge missing"

        # Verify time elapsed is well under 120s
        elapsed = time.time() - start_time
        assert elapsed < 10.0, f"Cold start took too long: {elapsed:.2f}s"
    finally:
        db.close()


def test_phase6_three_consecutive_runs_idempotency():
    """
    Acceptance Criterion 5:
    Run the entire seed -> correlate -> inspect pipeline three consecutive times.
    Verifies total stability, no duplicates, no schema errors.
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()

    try:
        for run_idx in range(1, 4):
            # Seed pass
            seed_database(db)
            personas = db.query(Persona).all()
            assert len(personas) == 6, f"Run {run_idx}: Expected 6 personas, found {len(personas)}"

            # Correlation pass
            corr_res = CorrelationService.run_correlation(db)
            assert corr_res["status"] == "success"
            assert corr_res["active_relationships"] == 3
            if run_idx == 1:
                assert corr_res["relationships_created"] == 3
            else:
                assert corr_res["relationships_created"] == 0
                assert corr_res["relationships_updated"] == 2

            # Total relationships in DB must remain exactly 3
            total_rels = db.query(Relationship).count()
            assert total_rels == 3, f"Run {run_idx}: Expected exactly 3 relationships, found {total_rels}"

            # Graph payload check
            graph = GraphService.get_graph_payload(db)
            assert len(graph["nodes"]) == 6
            assert len(graph["edges"]) == 3
    finally:
        db.close()


def test_phase6_full_api_export_and_provenance():
    """
    Verifies full integration through FastAPI endpoints:
    Graph -> Edge Inspection -> Raw Provenance Artifact -> CSV & JSON Export.
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()

    try:
        seed_database(db)
        CorrelationService.run_correlation(db)

        def override_get_db():
            yield db

        from backend.db import get_db
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        # 1. Health check
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # 2. Graph endpoint
        resp = client.get("/api/v1/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 6
        assert len(data["edges"]) == 3

        # 3. Edge details & Evidence inspection
        headline_edge = [e for e in data["edges"] if e["score"] == 0.95][0]
        rel_id = headline_edge["id"]
        resp = client.get(f"/api/v1/graph/edge/{rel_id}")
        assert resp.status_code == 200
        edge_detail = resp.json()
        assert edge_detail["score"] == 0.95
        assert len(edge_detail["evidence"]) == 2

        # 4. Provenance Artifact lookup
        art_id = edge_detail["evidence"][0]["artifact_id"]
        assert art_id is not None
        resp = client.get(f"/api/v1/artifacts/{art_id}")
        assert resp.status_code == 200
        art_data = resp.json()
        assert art_data["artifact_id"] == art_id
        assert "<html>" in art_data["raw_content"]
        assert art_data["content_hash"].startswith("sha256:")

        # 5. Export JSON
        resp = client.get("/api/v1/export?format=json")
        assert resp.status_code == 200
        export_json = resp.json()
        assert "platform" in export_json
        assert export_json["exported_relationships"] == 3
        assert len(export_json["relationships"]) == 3
        for r in export_json["relationships"]:
            for ev in r["evidence"]:
                assert "artifact_id" in ev and ev["artifact_id"] is not None

        # 6. Export CSV
        resp = client.get("/api/v1/export?format=csv")
        assert resp.status_code == 200
        csv_text = resp.text
        assert "artifact_id" in csv_text
        assert "relationship_id" in csv_text
    finally:
        app.dependency_overrides.clear()
        db.close()
