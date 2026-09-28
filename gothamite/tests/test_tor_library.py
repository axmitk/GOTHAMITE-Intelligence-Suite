"""Tor exit-node intelligence (Onionoo snapshot) and the synthetic case library."""
import json
import socket
import subprocess

import pytest

from backend.data_sources import importer as imp
from backend.data_sources.importer import TOR_RULE, entity_id, import_datasets, load_manifest
from backend.data_sources.transform import normalize_ipv4, normalize_onionoo_relay
from backend.models.workbench import DatasetRecord, EvidenceEntity, IntelEntity, IntelEvidence, IntelRelationship, ResponseAction
from backend.services.workbench_analysis import risk_assessment
from backend.services.workbench_library import TOR_CASE_IP, seed_library
from scripts.prepare_tor_snapshot import build
from tests.test_workbench import workbench, BASE  # noqa: F401  (fixture reuse)

LIBRARY = ["INC-1047", "INC-1048", "INC-1049", "INC-1050", "INC-1051", "INC-1052"]
FPR = "9454F82D47EBA0CB0C2A4BFE7966181DBF108147"


@pytest.fixture
def library(workbench, monkeypatch):  # noqa: F811
    """Seed + import with outbound sockets and subprocesses forbidden."""
    real_connect = socket.socket.connect

    def no_network(sock, address, *a, **k):
        # Loopback is the event loop's own self-pipe on Windows; anything else is outbound.
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError(f"network access attempted: {address}")
        return real_connect(sock, address, *a, **k)

    def no_outbound(address, *a, **k):
        raise AssertionError(f"network access attempted: {address}")

    def no_process(*a, **k):
        raise AssertionError("external process attempted")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_outbound)
    monkeypatch.setattr(subprocess, "Popen", no_process)
    client, factory = workbench
    with factory() as db:
        seed_library(db)
        stats = import_datasets(db)
    assert stats["evidence"] > 0
    return client, factory


# ---------- Snapshot parsing and normalization ----------

def test_normalize_ipv4_exact_key():
    assert normalize_ipv4("185.220.100.242:9100") == "185.220.100.242"
    assert normalize_ipv4(" 010.001.002.003 ") == "10.1.2.3"
    assert normalize_ipv4("[2a0b:f4c0:16c:14::1]:9100") is None
    assert normalize_ipv4("256.1.1.1") is None and normalize_ipv4("host.example") is None


def test_onionoo_relay_normalization_and_malformed():
    raw = {"nickname": "Relay1", "fingerprint": FPR.lower(), "or_addresses": ["185.220.100.242:9100", "[::1]:9100"],
           "exit_addresses": ["185.220.100.242"], "running": True, "flags": ["Running", "Exit", "Valid"],
           "first_seen": "2020-01-29 18:00:00", "last_seen": "2026-09-28 17:00:00", "as_name": "F3 Netze e.V.",
           "contact": "ignored", "platform": "ignored"}
    r = normalize_onionoo_relay(raw)
    assert r["fingerprint"] == FPR and r["exit"] is True and r["running"] is True
    assert r["or_addresses"] == ["185.220.100.242"] and r["exit_addresses"] == ["185.220.100.242"]
    assert r["first_seen"] == "2020-01-29T18:00:00Z" and r["last_seen"] == "2026-09-28T17:00:00Z"
    assert "contact" not in r and "platform" not in r  # unnecessary metadata is dropped
    guard = normalize_onionoo_relay({**raw, "flags": ["Guard", "Running"], "exit_addresses": None, "running": False})
    assert guard["exit"] is False and guard["running"] is False and guard["exit_addresses"] == []
    assert normalize_onionoo_relay({**raw, "fingerprint": "nothex"}) is None
    assert normalize_onionoo_relay({**raw, "or_addresses": ["[::1]:1"], "exit_addresses": []}) is None


def test_bundled_snapshot_is_bounded_and_labelled():
    ds = load_manifest()["datasets"]["tor_project_onionoo"]
    assert ds["provenance_class"] == "dataset_derived" and ds["license"].startswith("CC0")
    snap = json.loads((imp.DATA / "tor" / "onionoo_snapshot.json").read_text(encoding="utf-8"))
    assert snap["relays_published"] == "2026-09-28 17:00:00" and snap["retrieved"] == "2026-09-28"
    assert "does not describe current Tor network state" in snap["note"]
    relays = snap["relays"]
    assert 10 <= len(relays) <= 50
    assert any(r["exit"] and r["running"] for r in relays) and any(r["exit"] and not r["running"] for r in relays)
    assert any(not r["exit"] for r in relays) and len({r["as_name"] for r in relays}) >= 5
    assert len({r["last_seen"] for r in relays}) >= 3


def test_prepare_script_builds_from_local_files_only(tmp_path):
    doc = {"relays_published": "2026-01-01 00:00:00", "relays": [
        {"nickname": "a", "fingerprint": FPR, "or_addresses": ["192.0.2.1:9001"], "flags": ["Exit"], "running": True},
        {"nickname": "a", "fingerprint": FPR, "or_addresses": ["192.0.2.1:9001"], "flags": ["Exit"], "running": True},
        {"nickname": "bad", "fingerprint": "x"}]}
    f = tmp_path / "d.json"
    f.write_text(json.dumps(doc))
    out = build([f], "2026-01-02")
    assert out["stats"] == {"relays": 1, "rejected": 1, "exit_relays": 1, "running": 1}
    assert out["relays_published"] == "2026-01-01 00:00:00"


# ---------- Import, provenance and correlation ----------

def test_tor_provenance_and_observation_fields(library):
    _, factory = library
    with factory() as db:
        evs = db.query(IntelEvidence).filter(IntelEvidence.source == "Tor Project Onionoo").all()
        assert evs and all(e.provenance == "dataset_derived" for e in evs)
        for e in evs:
            rec = db.get(DatasetRecord, ("evidence", e.id))
            assert rec.dataset == "tor_project_onionoo" and rec.license.startswith("CC0")
            assert rec.transformation_version == "gothamite-tor-1.0"
            d = rec.details
            assert d["observation_type"] in {"tor_exit_node", "tor_relay"} and d["snapshot"] == "2026-09-28 17:00:00 UTC"
            assert {"fingerprint", "nickname", "running", "exit", "first_seen", "last_seen", "as_name"} <= set(d)
            assert (e.kind == "tor_context") == (d["observation_type"] == "tor_exit_node")
            assert "not a malicious verdict" in e.content and "live" not in e.content.lower()


def test_tor_import_is_deterministic(library):
    _, factory = library
    with factory() as db:
        before = sorted(e.id for e in db.query(IntelEvidence).filter(IntelEvidence.id.like("EV-TOR-%")))
        db.query(DatasetRecord).filter_by(record_type="import").delete()
        db.commit()
        stats = import_datasets(db)
        assert stats["evidence"] == 0 and stats["relationships"] == 0 and stats["entities"] == 0
        assert sorted(e.id for e in db.query(IntelEvidence).filter(IntelEvidence.id.like("EV-TOR-%"))) == before


def test_exact_ip_correlation_reuses_known_entity(library):
    _, factory = library
    with factory() as db:
        # The synthetic telemetry IP is matched exactly: no duplicate dataset IP entity.
        assert db.query(IntelEntity).filter_by(kind="ip", label=TOR_CASE_IP).count() == 1
        assert db.get(IntelEntity, entity_id("ip", TOR_CASE_IP)) is None
        rels = db.query(IntelRelationship).filter_by(source_id="IP-L47", relation="ASSOCIATED_WITH").all()
        assert len(rels) == 2  # two relays publish this address; each stays its own observation
        for r in rels:
            assert db.get(IntelEntity, r.target_id).kind == "tor_relay"
            rec = db.get(DatasetRecord, ("evidence", r.evidence_id))
            assert rec.details["correlation_rule"] == TOR_RULE and rec.details["matched_existing_entities"] == ["IP-L47"]
        # Same AS, neighbouring address: never correlated (no ASN or range similarity).
        near = entity_id("ip", "185.220.100.241")
        assert db.get(IntelEntity, near) is not None
        assert not db.query(IntelRelationship).filter(IntelRelationship.source_id == near,
                                                      IntelRelationship.target_id.like("IP-%")).count()
        assert not db.query(EvidenceEntity).filter(EvidenceEntity.entity_id == near,
                                                   EvidenceEntity.evidence_id.like("EV-L47%")).count()
        # Exercise infrastructure (203.0.113.0/24) never matches a Tor relay.
        assert not db.query(IntelRelationship).filter(IntelRelationship.source_id.like("IP-0%"),
                                                      IntelRelationship.relation == "ASSOCIATED_WITH").count()


def test_tor_enrichment_in_ioc_profile(library):
    client, _ = library
    hits = client.get(f"{BASE}/search", params={"q": TOR_CASE_IP}).json()["results"]
    assert [h["id"] for h in hits] == ["IP-L47"] and hits[0]["provenance"] == "synthetic"
    profile = client.get(f"{BASE}/entities/IP-L47").json()
    tor = [e for e in profile["evidence"] if e["dataset_record"] and e["dataset_record"]["dataset"] == "tor_project_onionoo"]
    assert len(tor) == 2 and all(e["dataset_record"]["details"]["observation_type"] == "tor_exit_node" for e in tor)
    assert any(e["provenance"] == "synthetic" for e in profile["evidence"])  # telemetry stays synthetic
    assert "INC-1047" in [c["id"] for c in profile["related_cases"]]
    # The entity's own reputation is not rewritten by Tor context.
    assert profile["entity"]["attributes"]["reputation"] == "unknown"


def test_tor_graph_relationship(library):
    client, _ = library
    g = client.get(f"{BASE}/graph/INC-1047").json()
    kinds = {n["id"]: n["kind"] for n in g["nodes"]}
    tor_edges = [e for e in g["edges"] if e["relation"] == "ASSOCIATED_WITH"]
    assert tor_edges and all(kinds[e["source_id"]] == "ip" and kinds[e["target_id"]] == "tor_relay" for e in tor_edges)
    # Every edge in the case graph cites an observation attached to the case.
    case_ev = {e["id"] for e in client.get(f"{BASE}/cases/INC-1047").json()["evidence"]}
    assert all(e["evidence_id"] in case_ev for e in g["edges"])


def test_tor_is_context_not_verdict(library):
    client, _ = library
    case = client.get(f"{BASE}/cases/INC-1047").json()
    factors = {f["label"]: f for f in case["risk"]["factors"]}
    assert factors["TOR exit-node context"]["points"] == 5 and factors["TOR exit-node context"]["dimension"] == "TOR context"
    assert "Malicious reputation observation" not in factors
    assert {f["dimension"] for f in case["risk"]["factors"]} == {"TOR context", "observed behavior"}
    assert "Source infrastructure is a Tor exit relay" in [f["title"] for f in case["analysis"]["findings"]]
    # A Tor-only IP (no behavior) stays low priority.
    only = client.get(f"{BASE}/entities/{entity_id('ip', '37.221.208.71')}").json()
    assert all(e["kind"] == "tor_context" for e in only["evidence"])

    class E:
        def __init__(self, id, kind): self.id, self.kind = id, kind
    assert risk_assessment([E("t1", "tor_context"), E("t2", "tor_context")], [])["level"] == "low"
    detect = next(n for n in case["nist"] if n["function"] == "DETECT")
    assert any(i.startswith("EV-TOR-") for i in detect["evidence_ids"])


def test_missing_tor_snapshot_is_skipped(workbench, monkeypatch, tmp_path):  # noqa: F811
    client, factory = workbench
    for d in ("infoblox", "darkforums", "dwdata"):
        (tmp_path / d).mkdir()
    (tmp_path / "manifest.json").write_text(json.dumps(load_manifest()))
    (tmp_path / "infoblox" / "ioc_snapshot.json").write_text(json.dumps({"indicators": []}))
    (tmp_path / "darkforums" / "forum_snapshot.json").write_text(json.dumps({"threads": []}))
    (tmp_path / "dwdata" / "reconstruction.json").write_text(json.dumps({"listings": []}))
    monkeypatch.setattr(imp, "DATA", tmp_path)
    with factory() as db:
        import_datasets(db)
        assert not db.query(IntelEntity).filter_by(kind="tor_relay").count()


# ---------- Case library ----------

def test_library_cases_load_with_evidence_nist_and_reports(library):
    client, factory = library
    queue = {c["id"] for c in client.get(f"{BASE}/dashboard").json()["cases"]}
    assert set(LIBRARY) <= queue and {"INC-1042", "INC-1046"} <= queue
    for cid in LIBRARY:
        case = client.get(f"{BASE}/cases/{cid}").json()
        assert case["evidence"], cid
        with factory() as db:
            for e in case["entities"]:
                assert db.get(IntelEntity, e["id"]) is not None
            for r in case["relationships"]:
                assert db.get(IntelEntity, r["source_id"]) and db.get(IntelEntity, r["target_id"])
        ids = {e["id"] for e in case["evidence"]}
        assert [n["function"] for n in case["nist"]] == ["GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"]
        for n in case["nist"]:
            assert set(n["evidence_ids"]) <= ids, (cid, n["function"])
        report = client.get(f"{BASE}/cases/{cid}/report").text
        assert report.startswith(f"# GOTHAMITE / {cid}") and report.count("\n\n## ") == 9
        assert "## Audit trail" in report and "## NIST alignment" in report


def test_library_varies_state_severity_and_sources(library):
    client, _ = library
    cases = [client.get(f"{BASE}/cases/{c}").json() for c in LIBRARY]
    assert len({c["status"] for c in cases}) >= 5
    assert {c["severity"] for c in cases} >= {"low", "medium", "high"}
    assert len({len(c["evidence"]) for c in cases}) >= 4
    states = {a["status"] for c in cases for a in c["actions"]}
    assert {"pending", "approved", "simulated", "rejected"} <= states
    closed = next(c for c in cases if c["id"] == "INC-1052")
    assert closed["status"] == "CLOSED" and next(n for n in closed["nist"] if n["function"] == "RECOVER")["status"] == "documented"
    contained = next(c for c in cases if c["id"] == "INC-1048")
    assert any(a["rule"] == "block" and a["status"] == "simulated" for a in contained["actions"])
    # Audit trail replays approvals before simulations.
    audit = [e["action"] for e in contained["audit"]]
    assert audit.index("response_approved") < audit.index("response_simulated")


def test_library_response_workflow_still_enforced(library):
    client, factory = library
    case = client.get(f"{BASE}/cases/INC-1047").json()
    path = f"{BASE}/cases/INC-1047/actions/hunt"
    assert client.post(path, json={"version": case["version"], "decision": "simulated"}).status_code == 200
    with factory() as db:
        assert db.get(ResponseAction, "INC-1047:hunt").status == "simulated"
    case = client.get(f"{BASE}/cases/INC-1052").json()
    assert client.post(f"{BASE}/cases/INC-1052/actions/preserve", json={"version": case["version"], "decision": "rejected",
                                                                          "reason": "x"}).status_code == 409


def test_library_provenance_survives_reports(library):
    client, _ = library
    tor = client.get(f"{BASE}/cases/INC-1047/report").text
    assert "Dataset-derived evidence: 2 observation(s) from Tor Project Onionoo relay metadata" in tor
    assert "Synthetic demonstration evidence: 2 observation(s)" in tor and "CC0" in tor
    assert "Provenance: Dataset-derived | Tor Project Onionoo relay metadata" in tor
    forum = client.get(f"{BASE}/cases/INC-1049").json()
    assert forum["evidence"] and all(e["dataset_record"]["dataset"] == "darkforums_safe_corpus" for e in forum["evidence"])
    ioc = client.get(f"{BASE}/cases/INC-1050").json()
    reports = {e["dataset_record"]["details"]["report"] for e in ioc["evidence"]}
    assert len(reports) == 3 and len(ioc["evidence"]) == 3  # three listings, not merged
    for cid in ("INC-1048", "INC-1051", "INC-1052"):
        text = client.get(f"{BASE}/cases/{cid}/report").text
        assert "SYNTHETIC EXERCISE" in text and "Dataset-derived evidence:" not in text
    cred = client.get(f"{BASE}/cases/INC-1051/report").text
    assert "[placeholder]" in cred.replace("\\[", "[").replace("\\]", "]")


def test_datasets_stay_unconnected_and_canonical_case_unchanged(library):
    client, factory = library
    with factory() as db:
        forum_domains = {e.entity_id for e in db.query(EvidenceEntity).filter(EvidenceEntity.evidence_id.like("EV-DF-%"))}
        infoblox = {e.entity_id for e in db.query(EvidenceEntity).filter(EvidenceEntity.evidence_id.like("EV-IB-%"))}
        cases = {c.id for c in db.query(IntelEntity).filter_by(kind="incident")}
        assert not (forum_domains & infoblox) - cases
    case = client.get(f"{BASE}/cases/INC-1042").json()
    assert case["risk"]["score"] == 100 and len(case["evidence"]) == 6 and not case["audit"]
    assert all(e["provenance"] == "synthetic" for e in case["evidence"])
    assert client.get(f"{BASE}/search", params={"q": "203.0.113.42"}).json()["total"] == 1
