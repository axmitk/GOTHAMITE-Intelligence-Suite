import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, get_db
from backend.main import app
from backend.models.entities import Persona, Identifier, Relationship, Evidence, Artifact
from backend.services.correlation_service import CorrelationService
from scripts.seed_demo import seed_database


@pytest.fixture
def test_db_session():
    """Sets up an isolated SQLite in-memory test database seeded with benchmark data."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    seed_database(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client_with_seeded_db(test_db_session):
    """FastAPI TestClient backed by seeded database."""
    def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_seed_benchmark_results(test_db_session):
    """
    Acceptance Criteria 1, 2, 3, 4:
    - nightjar <-> n1ghtjar_ == 0.95 (PGP +0.70, wallet +0.45)
    - quillfeather -> quill_v2 == 0.60 (wallet +0.45, succession +0.15)
    - nightjar <-> nightjarr == NO EDGE (0.05 - 0.30 below threshold)
    - bellwether -> n1ghtjar_ == transacted_with ONLY
    """
    result = CorrelationService.run_correlation(test_db_session)
    assert result["status"] == "success"

    # Map handles to personas
    personas = {p.handle: p for p in test_db_session.query(Persona).all()}
    
    # 1. nightjar <-> n1ghtjar_ (A1 <-> A2)
    rel_a = (
        test_db_session.query(Relationship)
        .filter(
            Relationship.type == "same_actor_suspected",
            (
                (Relationship.from_persona_id == personas["nightjar"].persona_id)
                & (Relationship.to_persona_id == personas["n1ghtjar_"].persona_id)
            )
            | (
                (Relationship.from_persona_id == personas["n1ghtjar_"].persona_id)
                & (Relationship.to_persona_id == personas["nightjar"].persona_id)
            ),
        )
        .first()
    )
    assert rel_a is not None, "nightjar <-> n1ghtjar_ edge missing!"
    assert rel_a.score == 0.95, f"Expected score 0.95, got {rel_a.score}"
    
    ev_a = test_db_session.query(Evidence).filter_by(relationship_id=rel_a.relationship_id).all()
    ev_a_types = {e.signal_type for e in ev_a}
    assert ev_a_types == {"shared_pgp", "shared_wallet"}
    assert {e.weight for e in ev_a} == {0.70, 0.45}

    # 2. quillfeather -> quill_v2 (B1 -> B2)
    rel_b = (
        test_db_session.query(Relationship)
        .filter(
            Relationship.type == "same_actor_suspected",
            (
                (Relationship.from_persona_id == personas["quillfeather"].persona_id)
                & (Relationship.to_persona_id == personas["quill_v2"].persona_id)
            )
            | (
                (Relationship.from_persona_id == personas["quill_v2"].persona_id)
                & (Relationship.to_persona_id == personas["quillfeather"].persona_id)
            ),
        )
        .first()
    )
    assert rel_b is not None, "quillfeather -> quill_v2 edge missing!"
    assert rel_b.score == 0.60, f"Expected score 0.60, got {rel_b.score}"

    ev_b = test_db_session.query(Evidence).filter_by(relationship_id=rel_b.relationship_id).all()
    ev_b_types = {e.signal_type for e in ev_b}
    assert ev_b_types == {"shared_wallet", "temporal_succession"}
    assert {e.weight for e in ev_b} == {0.45, 0.15}

    # 3. nightjar <-> nightjarr (A1 <-> C1: Decoy correctly rejected)
    rel_c = (
        test_db_session.query(Relationship)
        .filter(
            (
                (Relationship.from_persona_id == personas["nightjar"].persona_id)
                & (Relationship.to_persona_id == personas["nightjarr"].persona_id)
            )
            | (
                (Relationship.from_persona_id == personas["nightjarr"].persona_id)
                & (Relationship.to_persona_id == personas["nightjar"].persona_id)
            ),
        )
        .first()
    )
    assert rel_c is None, "CRITICAL: nightjar <-> nightjarr must produce NO edge!"

    # 4. bellwether -> n1ghtjar_ (D1 -> A2: Transaction edge only)
    rel_d = (
        test_db_session.query(Relationship)
        .filter(
            Relationship.from_persona_id == personas["bellwether"].persona_id,
            Relationship.to_persona_id == personas["n1ghtjar_"].persona_id,
        )
        .first()
    )
    assert rel_d is not None, "bellwether -> n1ghtjar_ transaction edge missing!"
    assert rel_d.type == "transacted_with", f"Expected transacted_with, got {rel_d.type}"
    assert rel_d.type != "same_actor_suspected", "Transaction edge must NEVER be same_actor_suspected"


def test_evidence_provenance_and_weights(test_db_session):
    """
    Acceptance Criteria 5, 7, 9:
    - Every relationship has evidence rows naming an artifact_id
    - Score reconstructs by summing evidence weights (clamped to 0.95)
    - No score exceeds 0.95
    """
    CorrelationService.run_correlation(test_db_session)
    relationships = test_db_session.query(Relationship).all()

    for rel in relationships:
        evidence_items = test_db_session.query(Evidence).filter_by(relationship_id=rel.relationship_id).all()
        assert len(evidence_items) > 0, f"Relationship {rel.relationship_id} missing evidence rows"
        
        for ev in evidence_items:
            assert ev.artifact_id is not None and len(ev.artifact_id) > 0
            art = test_db_session.query(Artifact).filter_by(artifact_id=ev.artifact_id).first()
            assert art is not None, f"Evidence refers to nonexistent artifact {ev.artifact_id}"

        if rel.type == "same_actor_suspected":
            expected_score = round(min(0.95, max(0.0, sum(e.weight for e in evidence_items))), 2)
            assert rel.score == expected_score, f"Score mismatch: {rel.score} != {expected_score}"
            assert rel.score <= 0.95, f"Score {rel.score} exceeds 0.95 ceiling!"


def test_idempotence_three_runs(test_db_session):
    """Acceptance Criterion 8: Running correlation three times produces identical results."""
    res1 = CorrelationService.run_correlation(test_db_session)
    count1 = test_db_session.query(Relationship).count()
    ev_count1 = test_db_session.query(Evidence).count()

    res2 = CorrelationService.run_correlation(test_db_session)
    count2 = test_db_session.query(Relationship).count()
    ev_count2 = test_db_session.query(Evidence).count()

    res3 = CorrelationService.run_correlation(test_db_session)
    count3 = test_db_session.query(Relationship).count()
    ev_count3 = test_db_session.query(Evidence).count()

    assert count1 == count2 == count3 == 3, f"Relationship count changed across runs: {count1}, {count2}, {count3}"
    assert ev_count1 == ev_count2 == ev_count3, "Evidence count changed across runs"


def test_rejected_relationships_preserved(test_db_session):
    """Acceptance Criterion 10: A rejected relationship is not recreated on re-run."""
    CorrelationService.run_correlation(test_db_session)
    
    # Reject nightjar <-> n1ghtjar_
    personas = {p.handle: p for p in test_db_session.query(Persona).all()}
    rel = (
        test_db_session.query(Relationship)
        .filter(
            Relationship.type == "same_actor_suspected",
            (
                (Relationship.from_persona_id == personas["nightjar"].persona_id)
                & (Relationship.to_persona_id == personas["n1ghtjar_"].persona_id)
            )
            | (
                (Relationship.from_persona_id == personas["n1ghtjar_"].persona_id)
                & (Relationship.to_persona_id == personas["nightjar"].persona_id)
            ),
        )
        .first()
    )
    rel.status = "rejected"
    test_db_session.commit()

    # Re-run correlation
    res = CorrelationService.run_correlation(test_db_session)
    assert res["rejected_skipped"] >= 1

    # Verify status is still rejected
    rel_after = test_db_session.query(Relationship).filter_by(relationship_id=rel.relationship_id).first()
    assert rel_after.status == "rejected"


def test_correlate_api_endpoint(client_with_seeded_db):
    """Test POST /api/v1/correlate endpoint."""
    res = client_with_seeded_db.post("/api/v1/correlate")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["active_relationships"] == 3
    assert len(data["edges"]) == 3
