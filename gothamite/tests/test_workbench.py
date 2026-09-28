import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.db import Base, get_db
from backend.main import app
from backend.models.workbench import IntelEntity, IntelEvidence, IntelRelationship, CaseNote
from backend.services.workbench_seed import seed_workbench
from backend.services.workbench_security import _buckets
from backend.services.workbench_analysis import EvidenceRuleProvider, risk_assessment

BASE = "/api/v1/workbench"


@pytest.fixture
def workbench():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        seed_workbench(db)
    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    _buckets.clear()
    client = TestClient(app)
    session = client.post(f"{BASE}/session", headers={"X-Gothamite-Client": "workbench"})
    assert session.status_code == 200
    client.headers["X-CSRF-Token"] = session.json()["csrf"]
    yield client, factory
    client.close()
    app.dependency_overrides.clear()
    engine.dispose()


def test_seed_integrity_and_idempotence(workbench):
    _, factory = workbench
    with factory() as db:
        assert db.query(IntelEntity).filter_by(kind="ip").count() == 120
        assert db.query(IntelEntity).filter_by(kind="domain").count() == 120
        count = db.query(IntelEntity).count()
        seed_workbench(db)
        assert db.query(IntelEntity).count() == count
        for ev in db.query(IntelEvidence):
            assert hashlib.sha256(ev.content.encode()).hexdigest() == ev.content_hash
        for edge in db.query(IntelRelationship):
            assert db.get(IntelEntity, edge.source_id)
            assert db.get(IntelEntity, edge.target_id)
            assert db.get(IntelEvidence, edge.evidence_id)


def test_search_profile_graph_and_evidence_path(workbench):
    client, _ = workbench
    search = client.get(f"{BASE}/search", params={"q": "203.0.113.42"}).json()
    assert search["total"] == 1
    id = search["results"][0]["id"]
    profile = client.get(f"{BASE}/entities/{id}").json()
    assert "INC-1042" in [c["id"] for c in profile["related_cases"]]
    graph = client.get(f"{BASE}/graph/{id}").json()
    assert len(graph["nodes"]) <= 28
    assert {"domain", "ip", "incident", "asset"} <= {n["kind"] for n in graph["nodes"]}
    nodes = {n["id"] for n in graph["nodes"]}
    assert all(e["source_id"] in nodes and e["target_id"] in nodes for e in graph["edges"])
    assert client.get(f"{BASE}/search", params={"q": "%"}).json()["total"] == 0
    assert client.get(f"{BASE}/search", params={"kind": "ip", "page": 2}).json()["total"] == 120
    assert client.get(f"{BASE}/entities/missing").status_code == 404
    assert client.get(f"{BASE}/graph/{id}?depth=99").status_code == 400


def test_analysis_is_evidence_bound_and_risk_reconstructs(workbench):
    client, _ = workbench
    case = client.get(f"{BASE}/cases/INC-1042").json()
    ids = {e["id"] for e in case["evidence"]}
    assert case["risk"]["score"] == sum(f["points"] for f in case["risk"]["factors"])
    for finding in case["analysis"]["findings"]:
        assert set(finding["evidence_ids"]) <= ids
    assert "Insufficient evidence" in EvidenceRuleProvider().analyze([], [])["summary"]
    assert risk_assessment([], [])["score"] == 0
    assert {n["function"] for n in case["nist"]} == {"GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"}


def test_case_review_persistence_conflict_and_report(workbench):
    client, factory = workbench
    path = f"{BASE}/cases/INC-1042"
    case = client.get(path).json()
    assert client.post(path + "/actions/isolate", json={"version":case["version"],"decision":"simulated"}).status_code == 409
    note = client.post(path + "/notes", json={"version":case["version"], "kind":"hypothesis", "text":"Verify service traffic <script>alert(1)</script>\n\n## Forged section"})
    assert note.status_code == 200
    assert client.patch(path, json={"version":case["version"],"severity":"high"}).status_code == 409
    case = note.json()
    for decision in ["approved", "simulated"]:
        result = client.post(path + "/actions/isolate", json={"version":case["version"],"decision":decision})
        assert result.status_code == 200, result.text
        case = result.json()
    assert client.post(path + "/actions/isolate", json={"version":case["version"],"decision":"simulated"}).status_code == 409
    result = client.patch(path, json={"version":case["version"],"status":"CONTAINMENT"})
    assert result.status_code == 200
    with factory() as db:
        seed_workbench(db)
        assert db.query(CaseNote).count() == 1
    report = client.get(path + "/report")
    assert report.status_code == 200
    assert "Automated interpretation" in report.text
    sections = ["Executive summary", "Observed evidence", "Correlated context", "Automated interpretation", "Risk assessment",
                "NIST alignment", "Response recommendations", "Analyst decisions", "Audit trail"]
    positions = [report.text.index("## " + section) for section in sections]
    assert positions == sorted(positions)
    assert report.text.count("\n\n## ") == 9
    assert "Isolate affected endpoint: simulated" in report.text
    assert "Supporting relationships" in report.text and "response_approved" in report.text
    assert "&lt;script&gt;" in report.text and "<script>" not in report.text
    assert "response_simulated" in [e["action"] for e in result.json()["audit"]]


def test_security_and_validation(workbench):
    client, _ = workbench
    second_tab = client.post(f"{BASE}/session", headers={"X-Gothamite-Client": "workbench"})
    assert second_tab.json()["csrf"] == client.headers["X-CSRF-Token"]
    assert TestClient(app).get(f"{BASE}/dashboard").status_code == 401
    assert client.post(f"{BASE}/session", headers={"X-Gothamite-Client":"workbench","Origin":"https://untrusted.example"}).status_code == 403
    path = f"{BASE}/cases/INC-1042/notes"
    assert client.post(path, json={"version":1,"text":" "}).status_code == 400
    assert client.post(path, json={"version":1,"text":"x"}, headers={"X-CSRF-Token":"wrong"}).status_code == 403
    assert client.get(f"{BASE}/dashboard", headers={"Host":"attacker.example"}).status_code == 400


def test_close_requires_recovery_and_lessons(workbench):
    client, _ = workbench
    path = f"{BASE}/cases/INC-1042"
    case = client.get(path).json()
    for rule in ["isolate", "recover"]:
        for decision in ["approved", "simulated"]:
            case = client.post(path + f"/actions/{rule}", json={"version":case["version"],"decision":decision}).json()
    for state in ["CONTAINMENT", "REMEDIATION", "RECOVERY"]:
        result = client.patch(path, json={"version":case["version"],"status":state})
        assert result.status_code == 200, result.text
        case = result.json()
    assert client.patch(path, json={"version":case["version"],"status":"CLOSED"}).status_code == 409
    for kind in ["recovery", "lesson"]:
        case = client.post(path + "/notes", json={"version":case["version"],"kind":kind,"text":"Exercise validation recorded."}).json()
    result = client.patch(path, json={"version":case["version"],"status":"CLOSED"})
    assert result.status_code == 200
    assert result.json()["nist"][-1]["status"] == "documented"


def test_nist_mapping_cites_evidence_and_response(workbench):
    client, _ = workbench
    path = f"{BASE}/cases/INC-1042"
    case = client.get(path).json()
    ids = {e["id"] for e in case["evidence"]}
    rows = {n["function"]: n for n in case["nist"]}
    for row in rows.values():
        assert row["basis"] and set(row["evidence_ids"]) <= ids
    assert rows["DETECT"]["evidence_ids"] and rows["IDENTIFY"]["evidence_ids"]
    assert {"isolate", "block", "remediate"} <= {a["rule"] for a in rows["RESPOND"]["actions"]}
    assert [a["rule"] for a in rows["PROTECT"]["actions"]] == ["identity"]
    assert case["advance"] == {"next": "CONTAINMENT", "ready": False, "requirement": case["advance"]["requirement"]}
    assert "containment" in case["advance"]["requirement"]
    for decision in ["approved", "simulated"]:
        case = client.post(path + "/actions/block", json={"version": case["version"], "decision": decision}).json()
    rows = {n["function"]: n for n in case["nist"]}
    assert rows["RESPOND"]["status"] == "documented"
    assert next(a for a in rows["RESPOND"]["actions"] if a["rule"] == "block")["status"] == "simulated"
    assert case["advance"]["ready"] is True
    report = client.get(path + "/report").text
    assert "Basis:" in report and "Block associated infrastructure — simulated" in report
