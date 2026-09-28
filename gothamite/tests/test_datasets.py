"""Public-dataset ingestion: parsing, safety, provenance, dedup, correlation,
graph, search, cases, reports, and the unchanged synthetic demo."""
import json

import pytest

from backend.data_sources import importer as imp
from backend.data_sources.importer import DATASET_CASE, entity_id, import_datasets
from backend.data_sources.transform import (
    TRANSFORMATION_VERSION, excerpt, extract_entities, normalize_forum_thread,
    normalize_infoblox_rows, parse_forum_date, project_marketplace_record, safety_reasons)
from backend.models.workbench import DatasetRecord, EvidenceEntity, IntelEntity, IntelEvidence, IntelRelationship
from backend.services.workbench_library import seed_library
from tests.test_workbench import workbench, BASE  # noqa: F401  (fixture reuse)


@pytest.fixture
def imported(workbench):  # noqa: F811
    client, factory = workbench
    with factory() as db:
        seed_library(db)  # the demo seeds the case library before importing snapshots
        import_datasets(db)
    return client, factory


# ---------- DarkForums parsing ----------

def test_forum_thread_parsing_and_placeholders():
    raw = {"thread_id": "7", "title": "Acme Corp (acme-example.com) database [DATABASE]", "category": "Leaks",
           "forum_name": "Databases", "author": "[AUTHOR]", "date_posted": "04-08-23, 07:01 PM",
           "posts": [{"post_id": "1", "post_number": "#1", "author": "[AUTHOR]", "post_date": "Less than 1 minute ago",
                      "content": "sample [EMAIL] [PHONE] [NAME] from Indonesia"},
                     {"post_id": "2", "post_number": "#2", "post_date": "05-08-23, 01:00 AM",
                      "content": "thanks for sharing https://mega.nz/file/abc"}]}
    rec = normalize_forum_thread(raw)
    assert rec["date_posted"] == "2023-08-04T19:01:00Z" and rec["date_basis"] == "source"
    assert rec["entities"]["domain"] == ["acme-example.com"]
    assert rec["entities"]["country"] == ["Indonesia"]
    p1, p2 = rec["posts"]
    # Placeholders are markers: the post is withheld and nothing is "recovered".
    assert p1["suppressed"] and p1["excerpt"] is None and p1["post_date"] is None
    assert "contains redacted personal data" in p1["suppression_reasons"]
    assert all("EMAIL" not in v and "PHONE" not in v for vals in p1["entities"].values() for v in vals)
    # URLs are stripped from what can be displayed.
    assert p2["excerpt"] == "thanks for sharing [link removed]"


def test_forum_malformed_and_missing_fields():
    assert normalize_forum_thread({}) is None
    assert normalize_forum_thread({"thread_id": "1"}) is None
    assert normalize_forum_thread("not a dict") is None
    rec = normalize_forum_thread({"thread_id": "9", "title": "x leak", "posts": [{"content": "no id"}, 5]})
    assert rec["posts"] == [] and rec["date_posted"] is None
    assert parse_forum_date("Less than 1 minute ago") == (None, "relative or unparseable in source")


def test_forum_title_with_secret_is_dropped():
    assert normalize_forum_thread({"thread_id": "3", "title": "admin password: hunter2", "posts": []}) is None


# ---------- Safety ----------

@pytest.mark.parametrize("text,reason", [
    ("password = letmein", "credential or secret reference"),
    ("api_key sk_live_abc", "credential or secret reference"),
    ("card 4111 1111 1111 1111", "payment card number"),
    ("IBAN DE89370400440532013000", "financial account number"),
    ("mail me at a.b@corp.example", "contact detail (email)"),
    ("call +44 20 7946 0958", "contact detail (phone-like number)"),
    ("-----BEGIN RSA PRIVATE KEY-----", "credential or secret reference"),
    ("powershell -e SQBFAFgA", "executable or script content"),
    ("A" * 90, "encoded blob or key material"),
])
def test_safety_filter_suppresses_sensitive_material(text, reason):
    assert reason in safety_reasons(text)
    assert excerpt(text) == (None, safety_reasons(text))


def test_safety_filter_allows_plain_claim_text():
    assert safety_reasons("Ukraine database of stolen vehicles, May 2023, 29 MB") == []


def test_extractor_supports_cve_cwe_attack_and_skips_non_orgs():
    e = extract_entities("CVE-2024-3400 CWE-79 T1566.001 via gmail.com and portal.gov.il and 1.2.3")
    assert e["cve"] == ["CVE-2024-3400"] and e["cwe"] == ["CWE-79"] and e["attack_technique"] == ["T1566.001"]
    assert e["domain"] == ["portal.gov.il"]


# ---------- Infoblox parsing ----------

def test_infoblox_parsing_bom_defang_missing_and_malformed():
    text = ("﻿type,indicator,classification,detected_date\n"
            "domain,evil[.]example,malicious,2023-04-20\n"
            "ip,198.51.100.7,suspicious,\n"
            "sha256,ABCDEF,malicious,2023-01-01\n"
            "email,x@y.example,malicious,2023-01-01\n"
            "unknown,foo,malicious,2023-01-01\n"
            "domain,,malicious,2023-01-01\n")
    rows, rejected = normalize_infoblox_rows(text, "r.csv")
    assert [(r["type"], r["indicator"]) for r in rows] == [("domain", "evil.example"), ("ip", "198.51.100.7"), ("hash", "abcdef")]
    assert rows[1]["detected_date"] is None and rows[1]["classification"] == "suspicious"
    assert rejected == 3  # email (contact data), unknown type, empty indicator


def test_marketplace_projection_schema():
    rec = project_marketplace_record({"vendor": "v1", "name": "RAT builder", "category": "Malware",
                                      "price": "120", "rating": "4.5"}, "abacus")
    assert (rec["vendor"], rec["title"], rec["category"], rec["price"], rec["rating"]) == ("v1", "RAT builder", "Malware", "120", "4.5")
    assert project_marketplace_record({"vendor": "v"}, "m") is None


# ---------- Import: provenance, dedup, determinism ----------

def test_import_provenance_fields(imported):
    _, factory = imported
    with factory() as db:
        ev = db.get(IntelEvidence, "EV-DF-T934")
        rec = db.get(DatasetRecord, ("evidence", "EV-DF-T934"))
        assert ev.provenance == "dataset_derived"
        assert rec.dataset == "darkforums_safe_corpus" and rec.license == "CC BY 4.0"
        assert rec.doi == "10.5281/zenodo.21991378" and rec.source_record_id == "thread:934"
        assert rec.transformation_version == TRANSFORMATION_VERSION and rec.imported_at and rec.dataset_version
        # Synthetic seed rows are untouched and carry no dataset record.
        assert db.get(IntelEvidence, "EV-1-NETWORK").provenance == "synthetic"
        assert db.get(DatasetRecord, ("evidence", "EV-1-NETWORK")) is None
        listing = db.query(IntelEntity).filter_by(kind="market_listing").first()
        assert listing.provenance == "reference_derived"


def test_import_twice_creates_no_duplicates(imported):
    _, factory = imported
    with factory() as db:
        counts = (db.query(IntelEvidence).count(), db.query(IntelRelationship).count(), db.query(IntelEntity).count())
        assert import_datasets(db) == {"skipped": "snapshot already imported"}
        # Bypass the fast path: record-level dedup must also hold.
        db.query(DatasetRecord).filter_by(record_type="import").delete()
        db.commit()
        stats = import_datasets(db)
        assert stats["evidence"] == 0 and stats["relationships"] == 0 and stats["entities"] == 0
        assert (db.query(IntelEvidence).count(), db.query(IntelRelationship).count(), db.query(IntelEntity).count()) == counts


def test_no_raw_suppressed_text_is_stored(imported):
    _, factory = imported
    with factory() as db:
        rows = db.query(IntelEvidence).filter(IntelEvidence.provenance != "synthetic").all()
        assert rows
        for r in rows:
            assert "[EMAIL]" not in r.content and "[PHONE]" not in r.content and "[CREDENTIAL]" not in r.content
            assert "http" not in r.content.lower()


# ---------- Correlation and graph ----------

def test_same_indicator_across_reports_keeps_each_observation(imported):
    client, _ = imported
    eid = entity_id("domain", "claudfront.net")
    profile = client.get(f"{BASE}/entities/{eid}").json()
    reports = {e["dataset_record"]["details"]["report"] for e in profile["evidence"]}
    assert len(reports) >= 2  # independent report listings, not merged away
    assert all(e["provenance"] == "dataset_derived" for e in profile["evidence"])


def test_cross_dataset_entity_retains_both_provenances(workbench, monkeypatch, tmp_path):  # noqa: F811
    """The real snapshots share no entity; prove the rule with a fixture."""
    client, factory = workbench
    manifest = imp.load_manifest()
    (tmp_path / "infoblox").mkdir()
    (tmp_path / "darkforums").mkdir()
    (tmp_path / "dwdata").mkdir()
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "infoblox" / "ioc_snapshot.json").write_text(json.dumps({"indicators": [
        {"type": "domain", "indicator": "shared-example.com", "classification": "malicious",
         "detected_date": "2024-01-02", "report": "fixture_20240102_iocs.csv"}]}))
    (tmp_path / "darkforums" / "forum_snapshot.json").write_text(json.dumps({"threads": [
        normalize_forum_thread({"thread_id": "555", "title": "shared-example.com leak", "category": "Leaks",
                                "forum_name": "Databases", "date_posted": "01-02-24, 10:00 AM", "posts": []})]}))
    (tmp_path / "dwdata" / "reconstruction.json").write_text(json.dumps({"listings": []}))
    monkeypatch.setattr(imp, "DATA", tmp_path)
    with factory() as db:
        import_datasets(db)
    eid = entity_id("domain", "shared-example.com")
    profile = client.get(f"{BASE}/entities/{eid}").json()
    datasets = sorted(e["dataset_record"]["dataset"] for e in profile["evidence"])
    assert datasets == ["darkforums_safe_corpus", "infoblox_threat_intelligence"]
    rels = {(r["relation"]) for r in profile["relationships"]}
    assert rels == {"OBSERVED_IN", "MENTIONS"}


def test_only_supported_relationships_become_edges(imported):
    _, factory = imported
    with factory() as db:
        rels = db.query(IntelRelationship).join(
            DatasetRecord, (DatasetRecord.record_id == IntelRelationship.id) & (DatasetRecord.record_type == "relationship")).all()
        assert rels
        for r in rels:
            assert r.relation in {"OBSERVED_IN", "MENTIONS", "INVESTIGATES", "ASSOCIATED_WITH"}
            # Each edge cites evidence linked to both endpoints (or the case scope).
            linked = {x.entity_id for x in db.query(EvidenceEntity).filter_by(evidence_id=r.evidence_id)}
            case_scope = r.relation == "INVESTIGATES" and db.get(IntelEntity, r.source_id).kind == "incident"
            assert r.target_id in linked and (r.source_id in linked or case_scope)
        # The reconstruction produces no relationships at all.
        listings = [e.id for e in db.query(IntelEntity).filter_by(kind="market_listing")]
        assert not db.query(IntelRelationship).filter(IntelRelationship.source_id.in_(listings)).count()


def test_graph_for_dataset_indicator(imported):
    client, _ = imported
    g = client.get(f"{BASE}/graph/{entity_id('domain', 'claudfront.net')}").json()
    kinds = {n["kind"] for n in g["nodes"]}
    assert {"domain", "report"} <= kinds and g["edges"]


# ---------- Search, case, report, dashboard ----------

def test_search_distinguishes_provenance(imported):
    client, _ = imported
    ds = client.get(f"{BASE}/search", params={"q": "claudfront"}).json()["results"]
    assert ds and all(r["provenance"] == "dataset_derived" for r in ds)
    syn = client.get(f"{BASE}/search", params={"q": "203.0.113.42"}).json()["results"]
    assert syn[0]["id"] == "IP-001" and syn[0]["provenance"] == "synthetic"
    threads = client.get(f"{BASE}/search", params={"kind": "forum_thread"}).json()
    assert threads["total"] == 200


def test_dataset_case_report_and_nist(imported):
    client, _ = imported
    case = client.get(f"{BASE}/cases/{DATASET_CASE}").json()
    assert case["evidence"] and all(e["provenance"] == "dataset_derived" for e in case["evidence"])
    assert all(e["dataset_record"]["dataset"] == "infoblox_threat_intelligence" for e in case["evidence"])
    # Existing rules only: malicious listings -> reputation factor; no invented factors.
    assert {f["label"] for f in case["risk"]["factors"]} == {"Malicious reputation observation"}
    nist = {n["function"]: n for n in case["nist"]}
    assert nist["DETECT"]["evidence_ids"] and not nist["IDENTIFY"]["evidence_ids"]
    assert "dataset-derived" in case["analysis"]["summary"]
    report = client.get(f"{BASE}/cases/{DATASET_CASE}/report").text
    assert "CONTAINS DATASET-DERIVED EVIDENCE" in report and "### Evidence sources" in report
    assert "Dataset-derived evidence:" in report and "CC BY 4.0" in report
    assert "Provenance: Dataset-derived | Infoblox Threat Intelligence indicators" in report
    assert report.count("\n\n## ") == 9


def test_canonical_demo_unchanged_with_datasets(imported):
    client, _ = imported
    assert client.get(f"{BASE}/search", params={"q": "203.0.113.42"}).json()["total"] == 1
    case = client.get(f"{BASE}/cases/INC-1042").json()
    assert case["risk"]["score"] == 100 and len(case["evidence"]) == 6
    assert all(e["provenance"] == "synthetic" and e["dataset_record"] is None for e in case["evidence"])
    report = client.get(f"{BASE}/cases/INC-1042/report").text
    assert report.startswith("# GOTHAMITE / INC-1042") and "SYNTHETIC EXERCISE" in report
    assert "Synthetic demonstration evidence: 6 observation(s)" in report
    dash = client.get(f"{BASE}/dashboard").json()
    assert dash["provenance"]["evidence"]["dataset_derived"] > 0
    assert all(r["provenance"] == "synthetic" for r in dash["recent"])
