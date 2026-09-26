import hashlib
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, get_db
from backend.main import app
from backend.models.entities import Source, Artifact, Persona, Identifier, Relationship, Evidence


def compute_sha256(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


@pytest.fixture
def client_with_db():
    """Sets up an isolated in-memory SQLite database and FastAPI TestClient."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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


def make_valid_payload(
    handle: str = "nightjar",
    raw_content: str = "<html><body>Post 1: Hello from forum-alpha</body></html>",
    observed_at: str = "2026-03-11T09:14:00Z",
    source_id: str = "forum-alpha",
    url: str = "alpha7fq2mx9k.onion.mock/thread/1",
):
    c_hash = compute_sha256(raw_content)
    return {
        "source_id": source_id,
        "source_type": "forum",
        "url": url,
        "collected_at": "2026-09-06T14:22:31Z",
        "relay_path": ["relay-05", "relay-02", "relay-07"],
        "raw_content": raw_content,
        "content_hash": c_hash,
        "persona": {
            "handle": handle,
            "observed_at": observed_at,
        },
        "identifiers": [
            {
                "type": "pgp_fingerprint",
                "value": "9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D",
                "observed_at": observed_at,
            },
            {
                "type": "wallet",
                "value": "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZaEuT6",
                "observed_at": observed_at,
            },
        ],
    }


def test_valid_payload_ingest(client_with_db):
    """Acceptance Criterion 1: Valid payload -> 202, artifact + persona + identifiers persisted."""
    client, session_factory = client_with_db
    payload = make_valid_payload()

    res = client.post("/api/v1/ingest", json=payload)
    assert res.status_code == 202
    data = res.json()
    assert data["accepted"] is True
    assert "artifact_id" in data
    assert data["identifiers_stored"] == 2

    # Check persistence in DB
    db = session_factory()
    try:
        art = db.query(Artifact).filter_by(artifact_id=data["artifact_id"]).first()
        assert art is not None
        assert art.content_hash == payload["content_hash"]

        pers = db.query(Persona).filter_by(handle="nightjar").first()
        assert pers is not None
        assert pers.post_count == 1

        idents = db.query(Identifier).filter_by(persona_id=pers.persona_id).all()
        assert len(idents) == 2
    finally:
        db.close()


def test_raw_content_verbatim(client_with_db):
    """Acceptance Criterion 2: raw_content stored verbatim (byte-identical)."""
    client, session_factory = client_with_db
    verbatim_text = "<html>\n  <body>\n    <script>alert('xss');</script>\n    <pre>Raw content with special \t chars</pre>\n  </body>\n</html>"
    payload = make_valid_payload(raw_content=verbatim_text)

    res = client.post("/api/v1/ingest", json=payload)
    assert res.status_code == 202
    artifact_id = res.json()["artifact_id"]

    db = session_factory()
    try:
        art = db.query(Artifact).filter_by(artifact_id=artifact_id).first()
        assert art.raw_content == verbatim_text
    finally:
        db.close()


def test_hash_mismatch_rejected(client_with_db):
    """Acceptance Criterion 3: Hash recomputed and mismatch rejected with 400."""
    client, session_factory = client_with_db
    payload = make_valid_payload()
    payload["content_hash"] = "sha256:0000000000000000000000000000000000000000000000000000000000000000"

    res = client.post("/api/v1/ingest", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["detail"]["accepted"] is False
    assert any("mismatch" in err.lower() for err in data["detail"]["errors"])

    # Ensure nothing persisted
    db = session_factory()
    try:
        assert db.query(Artifact).count() == 0
        assert db.query(Persona).count() == 0
    finally:
        db.close()


def test_duplicate_content_hash(client_with_db):
    """Acceptance Criterion 4: Duplicate (source_id, content_hash) -> 200 duplicate, no second artifact."""
    client, session_factory = client_with_db
    payload = make_valid_payload()

    # First ingest -> 202
    res1 = client.post("/api/v1/ingest", json=payload)
    assert res1.status_code == 202
    orig_art_id = res1.json()["artifact_id"]

    # Second ingest of exact same content -> 200
    res2 = client.post("/api/v1/ingest", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["accepted"] is False
    assert data2["reason"] == "duplicate_content_hash"
    assert data2["artifact_id"] == orig_art_id

    # Check that only one artifact exists
    db = session_factory()
    try:
        assert db.query(Artifact).count() == 1
    finally:
        db.close()


def test_malformed_payload_rejected(client_with_db):
    """Acceptance Criterion 5: Malformed payload -> 400 naming the field, nothing persisted."""
    client, session_factory = client_with_db
    payload = make_valid_payload()
    del payload["source_id"]  # Missing required field

    res = client.post("/api/v1/ingest", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["accepted"] is False
    assert any("source_id" in err for err in data["errors"])

    db = session_factory()
    try:
        assert db.query(Artifact).count() == 0
    finally:
        db.close()


def test_repeat_persona_widens_window(client_with_db):
    """Acceptance Criterion 6: Repeat persona ingest widens first_seen/last_seen without duplicating."""
    client, session_factory = client_with_db
    
    # Ingest 1 (May)
    payload1 = make_valid_payload(
        handle="quillfeather",
        raw_content="Post 1 in May",
        observed_at="2026-05-01T10:00:00Z",
        url="alpha7fq2mx9k.onion.mock/thread/1",
    )
    res1 = client.post("/api/v1/ingest", json=payload1)
    assert res1.status_code == 202

    # Ingest 2 (January - earlier)
    payload2 = make_valid_payload(
        handle="quillfeather",
        raw_content="Post 2 in Jan",
        observed_at="2026-01-15T12:00:00Z",
        url="alpha7fq2mx9k.onion.mock/thread/2",
    )
    res2 = client.post("/api/v1/ingest", json=payload2)
    assert res2.status_code == 202

    # Ingest 3 (August - later)
    payload3 = make_valid_payload(
        handle="quillfeather",
        raw_content="Post 3 in August",
        observed_at="2026-08-20T18:00:00Z",
        url="alpha7fq2mx9k.onion.mock/thread/3",
    )
    res3 = client.post("/api/v1/ingest", json=payload3)
    assert res3.status_code == 202

    db = session_factory()
    try:
        personas = db.query(Persona).filter_by(handle="quillfeather").all()
        assert len(personas) == 1, "Persona was duplicated!"
        p = personas[0]
        assert p.post_count == 3
        
        # Verify first_seen is Jan and last_seen is Aug
        first_iso = p.first_seen.isoformat()
        last_iso = p.last_seen.isoformat()
        assert "2026-01-15" in first_iso
        assert "2026-08-20" in last_iso
    finally:
        db.close()


def test_same_identifier_different_artifacts_both_retained(client_with_db):
    """Acceptance Criterion 7: Same identifier from two artifacts -> two rows, both retained."""
    client, session_factory = client_with_db

    payload1 = make_valid_payload(
        handle="nightjar",
        raw_content="Article 1 content",
        url="alpha7fq2mx9k.onion.mock/thread/101",
    )
    res1 = client.post("/api/v1/ingest", json=payload1)
    assert res1.status_code == 202
    art1_id = res1.json()["artifact_id"]

    payload2 = make_valid_payload(
        handle="nightjar",
        raw_content="Article 2 content with same PGP and wallet",
        url="alpha7fq2mx9k.onion.mock/thread/102",
    )
    res2 = client.post("/api/v1/ingest", json=payload2)
    assert res2.status_code == 202
    art2_id = res2.json()["artifact_id"]

    db = session_factory()
    try:
        idents = db.query(Identifier).filter_by(type="pgp_fingerprint").all()
        assert len(idents) == 2, f"Expected 2 PGP identifier rows, got {len(idents)}"
        art_ids = {i.artifact_id for i in idents}
        assert art_ids == {art1_id, art2_id}
    finally:
        db.close()


def test_no_relationships_created_at_ingest(client_with_db):
    """Acceptance Criterion 8: No relationship is created by any ingest call."""
    client, session_factory = client_with_db

    # Ingest persona A1
    payload1 = make_valid_payload(handle="nightjar", source_id="forum-alpha", url="alpha7fq2mx9k.onion.mock/p/1")
    client.post("/api/v1/ingest", json=payload1)

    # Ingest persona A2 (shares PGP & wallet on different source!)
    payload2 = make_valid_payload(handle="n1ghtjar_", source_id="marketplace-beta", url="beta3kx8pm2v.onion.mock/p/2")
    client.post("/api/v1/ingest", json=payload2)

    db = session_factory()
    try:
        # Crucial architectural invariant: relationships and evidence MUST remain 0!
        assert db.query(Relationship).count() == 0
        assert db.query(Evidence).count() == 0
    finally:
        db.close()


def test_security_boundary_validations(client_with_db):
    """Acceptance Criterion 9: Validation constraints from SECURITY.md §2 enforced at the boundary."""
    client, _ = client_with_db

    # 1. Invalid source_id
    bad_source = make_valid_payload()
    bad_source["source_id"] = "unknown-darkweb-site"
    assert client.post("/api/v1/ingest", json=bad_source).status_code == 400

    # 2. Non-onion mock URL
    bad_url = make_valid_payload()
    bad_url["url"] = "https://clearnet-exploit.com/evil"
    assert client.post("/api/v1/ingest", json=bad_url).status_code == 400

    # 3. Content exceeding 1 MB limit
    huge_content = "A" * (1024 * 1024 + 50)
    huge_payload = make_valid_payload(raw_content=huge_content)
    assert client.post("/api/v1/ingest", json=huge_payload).status_code == 400

    # 4. Handle with control character
    ctrl_handle = make_valid_payload(handle="night\x00jar")
    assert client.post("/api/v1/ingest", json=ctrl_handle).status_code == 400

    # 5. Invalid PGP (non-hex or wrong length)
    bad_pgp = make_valid_payload()
    bad_pgp["identifiers"][0]["value"] = "9F2A4C81Z"  # non-hex char 'Z' and too short
    assert client.post("/api/v1/ingest", json=bad_pgp).status_code == 400

    # 6. Invalid wallet (non-base58)
    bad_wallet = make_valid_payload()
    bad_wallet["identifiers"][1]["value"] = "1Hx4kQ9mVn2RtYbP7sLdF3wCgN8jZa0000"  # '0' not in base58
    assert client.post("/api/v1/ingest", json=bad_wallet).status_code == 400
