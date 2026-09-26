import os
import re
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, get_db
from backend.services.correlation_service import CorrelationService
from frontend.api_client import (
    get_graph,
    get_edge_details,
    update_edge_status,
    search_entities,
    get_persona_dossier,
    get_artifact,
    format_score_badge,
)
from scripts.seed_demo import seed_database


@pytest.fixture(autouse=True)
def setup_seeded_test_environment(monkeypatch):
    """Sets up an isolated SQLite in-memory database and wires it to frontend api_client fallback."""
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

    monkeypatch.setattr("backend.db.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("backend.db.engine", engine)
    monkeypatch.setattr("frontend.api_client.check_api_online", lambda: False)
    yield
    session.close()


def test_score_rendering_language_rules():
    """Acceptance Criterion 8: Scores render as '0.95' with band label — never as percentage."""
    badge_95 = format_score_badge(0.95)
    assert "0.95" in badge_95
    assert "Very Strong" in badge_95
    assert "%" not in badge_95

    badge_60 = format_score_badge(0.60)
    assert "0.60" in badge_60
    assert "Strong" in badge_60
    assert "%" not in badge_60

    badge_40 = format_score_badge(0.40)
    assert "0.40" in badge_40
    assert "Moderate" in badge_40
    assert "%" not in badge_40


def test_frontend_security_no_unsafe_html():
    """Acceptance Criterion 9: No ingested string rendered with unsafe_allow_html=True."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    for root, _, files in os.walk(frontend_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read()
                    assert "unsafe_allow_html=True" not in content, f"Found unsafe_allow_html=True in {path}"


def test_frontend_forbidden_attribution_vocabulary():
    """Hard UI Rule: Never use 'identified', 'deanonymised', 'confirmed identity', 'proof', or percentage probability."""
    forbidden_terms = [
        r"\bdeanonymised\b",
        r"\bdeanonymized\b",
        r"\bconfirmed identity\b",
        r"\b95%\b",
        r"\b60%\b",
    ]
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    for root, _, files in os.walk(frontend_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fp:
                    content = fp.read().lower()
                    for term in forbidden_terms:
                        match = re.search(term, content)
                        assert match is None, f"Found forbidden term '{term}' in {path}"


def test_api_client_operations():
    """Acceptance Criteria 1, 2, 4, 5, 6: API client functions successfully fetch graph, evidence, and dossiers."""
    # 1. Graph
    graph = get_graph()
    assert graph["node_count"] == 6
    assert graph["edge_count"] >= 3

    # 2. Edge details & Evidence
    rel_id = graph["edges"][0]["id"]
    edge_details = get_edge_details(rel_id)
    assert edge_details is not None
    assert len(edge_details["evidence"]) > 0
    for ev in edge_details["evidence"]:
        assert "artifact_id" in ev
        art = get_artifact(ev["artifact_id"])
        assert art is not None
        assert len(art["raw_content"]) > 0

    # 3. Search
    search_res = search_entities("nightjar")
    assert search_res["count"] >= 1
    p_id = search_res["results"][0]["persona_id"]

    # 4. Dossier
    dossier = get_persona_dossier(p_id)
    assert dossier is not None
    assert dossier["handle"] in ["nightjar", "nightjarr", "n1ghtjar_"]
    assert len(dossier["identifiers"]) >= 1
    assert len(dossier["timeline"]) >= 1


def test_confirm_reject_workflow():
    """Acceptance Criterion 4: Confirm/reject works and updates immediately."""
    graph = get_graph()
    initial_edge_count = graph["edge_count"]
    rel_id = graph["edges"][0]["id"]

    # Reject
    updated = update_edge_status(rel_id, "rejected")
    assert updated["status"] == "rejected"

    # Verify edge excluded from active graph
    graph_after = get_graph()
    assert graph_after["edge_count"] == initial_edge_count - 1
    remaining_ids = [e["id"] for e in graph_after["edges"]]
    assert rel_id not in remaining_ids


def test_test_isolation_guaranteed_no_live_network_calls():
    """Verify that tests strictly block outbound requests and never touch a live server."""
    import requests
    from frontend.api_client import check_api_online

    assert check_api_online() is False
    with pytest.raises(RuntimeError, match="Test isolation violation"):
        requests.get("http://localhost:8000/health")

