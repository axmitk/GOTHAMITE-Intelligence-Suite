import os
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.db import Base
from backend.models.entities import (
    Source,
    Artifact,
    Persona,
    Identifier,
    Relationship,
    Evidence,
    Actor,
)
from scripts.seed_demo import (
    seed_database,
    verify_seed_invariants,
    compute_hash,
    parse_iso,
    normalize_pgp,
)


@pytest.fixture
def test_db():
    """Creates a temporary in-memory SQLite database for testing."""
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_tables_created_cleanly(test_db):
    """Acceptance Criterion 1: All seven tables create cleanly."""
    tables = Base.metadata.tables.keys()
    expected_tables = {
        "sources",
        "artifacts",
        "personas",
        "identifiers",
        "relationships",
        "evidence",
        "actors",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - set(tables)}"


def test_persona_unique_constraint(test_db):
    """Acceptance Criterion 2a: Persona unique on (handle, source_id)."""
    src = Source(source_id="forum-alpha", type="forum", reliability="high", status="up")
    test_db.add(src)
    test_db.commit()

    p1 = Persona(
        persona_id="p-1",
        handle="nightjar",
        source_id="forum-alpha",
        first_seen=parse_iso("2026-01-01T00:00:00Z"),
        last_seen=parse_iso("2026-01-02T00:00:00Z"),
        post_count=1,
    )
    test_db.add(p1)
    test_db.commit()

    p2 = Persona(
        persona_id="p-2",
        handle="nightjar",  # Duplicate handle on same source_id
        source_id="forum-alpha",
        first_seen=parse_iso("2026-01-03T00:00:00Z"),
        last_seen=parse_iso("2026-01-04T00:00:00Z"),
        post_count=1,
    )
    test_db.add(p2)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_identifier_foreign_keys(test_db):
    """Acceptance Criterion 2b: Identifiers require persona_id and artifact_id."""
    # Attempting to save an identifier without persona_id or artifact_id fails
    ident = Identifier(
        identifier_id="i-orphan",
        type="wallet",
        value="1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
        persona_id=None,
        artifact_id=None,
        observed_at=parse_iso("2026-01-01T00:00:00Z"),
    )
    test_db.add(ident)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_seed_demo_idempotence_and_vectors(test_db):
    """Acceptance Criteria 3, 4, 5, 6: Seed demo loads exact vectors, PGP normalized, idempotent."""
    # First seed run
    seed_database(test_db)
    verify_seed_invariants(test_db)

    count_personas_1 = test_db.query(Persona).count()
    count_artifacts_1 = test_db.query(Artifact).count()
    count_identifiers_1 = test_db.query(Identifier).count()

    assert count_personas_1 == 6, f"Expected 6 personas, found {count_personas_1}"

    # Second seed run (must be idempotent - no duplicates)
    seed_database(test_db)
    verify_seed_invariants(test_db)

    count_personas_2 = test_db.query(Persona).count()
    count_artifacts_2 = test_db.query(Artifact).count()
    count_identifiers_2 = test_db.query(Identifier).count()

    assert count_personas_2 == count_personas_1, "Idempotency failed: personas duplicated"
    assert count_artifacts_2 == count_artifacts_1, "Idempotency failed: artifacts duplicated"
    assert count_identifiers_2 == count_identifiers_1, "Idempotency failed: identifiers duplicated"


def test_pgp_normalization_helper():
    """Acceptance Criterion 4: PGP fingerprints must be uppercase, 40 hex chars, whitespace stripped."""
    raw = "9f2a 4c81 d3e5 b706 9a1c 4f82 d6e3 0b57 a4c1 9e8d"
    normalized = normalize_pgp(raw)
    assert normalized == "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D"
    assert len(normalized) == 40
    assert normalized.isupper()

    # Invalid cases
    with pytest.raises(ValueError):
        normalize_pgp("too_short")

    with pytest.raises(ValueError):
        normalize_pgp("9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8Z")  # 'Z' is not hex
