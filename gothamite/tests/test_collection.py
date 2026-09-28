"""Source adapter layer: interfaces, normalization, provenance, state, dedup,
failure handling, synthetic fallback, and that the core demo is unaffected."""
import subprocess

import pytest

from backend.collection import default_registry
from backend.collection.base import (
    AdapterResult, CollectionAdapter, EnrichmentAdapter, Observation, SourceState, dedupe, infer_kind)
from backend.collection.adapters.isolated import TorBotCollectionAdapter, HorusEnrichmentAdapter, MailAccessEnrichmentAdapter
from backend.collection.adapters.synthetic import SyntheticMailAccessAdapter, SyntheticTorBotAdapter
from backend.collection.registry import AdapterRegistry
from backend.collection.sources import DeepDarkCTIRegistry, parse_catalogue_markdown
from tests.test_workbench import workbench, BASE  # noqa: F401  (fixture reuse)

LIVE_VARS = ["GOTHAMITE_LIVE_COLLECTION", "GOTHAMITE_ADAPTER_TORBOT", "GOTHAMITE_ADAPTER_HORUS",
             "GOTHAMITE_ADAPTER_MAILACCESS", "GOTHAMITE_DEEPDARKCTI_PATH"]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for v in LIVE_VARS:
        monkeypatch.delenv(v, raising=False)
    # Any subprocess launch in these tests is a bug: the demo must stay offline.
    def forbidden(*a, **k):
        raise AssertionError("adapter attempted to launch an external process")
    monkeypatch.setattr(subprocess, "run", forbidden)


def obs(**kw):
    base = dict(adapter="t", source="S", entity_kind="email", value="a@b.example",
                observed_at="2026-09-28T09:00:00Z", confidence=0.5, provenance="p", synthetic=True)
    return Observation(**{**base, **kw})


def test_observation_schema_and_validation():
    o = obs()
    d = o.to_dict()
    for field in ("source", "source_type", "observed_at", "collection_status", "provenance",
                  "confidence", "entity_kind", "value", "relationship", "synthetic", "id"):
        assert field in d
    with pytest.raises(ValueError):
        obs(entity_kind="not-a-kind")
    with pytest.raises(ValueError):
        obs(confidence=1.5)
    with pytest.raises(ValueError):
        obs(value="")


def test_dedupe_keeps_highest_confidence_and_order():
    a, b = obs(confidence=0.4), obs(value="A@B.example", confidence=0.9)
    c = obs(value="c@d.example")
    out = dedupe([a, c, b])
    assert [o.value for o in out] == ["A@B.example", "c@d.example"]
    assert out[0].confidence == 0.9


def test_infer_kind():
    assert infer_kind("x@y.example") == "email"
    assert infer_kind("203.0.113.42") == "ip"
    assert infer_kind("glass-harbor-sync.example") == "domain"
    assert infer_kind("http://a.example/x") == "url"


def test_interfaces_and_default_state_is_offline():
    reg = default_registry()
    assert all(isinstance(live, EnrichmentAdapter) for live, _ in reg.enrichers)
    assert all(isinstance(live, CollectionAdapter) for live, _ in reg.collectors)
    for row in reg.status():
        if row["type"] != "source-registry":
            assert row["live_state"] == "unavailable" and row["mode"] == "synthetic"
    assert TorBotCollectionAdapter().state() is SourceState.UNAVAILABLE


def test_synthetic_fallback_enrichment_has_provenance():
    result = default_registry().enrich("svc-1@meridian.example")
    assert result["kind"] == "email" and result["observations"]
    for o in result["observations"]:
        assert o["synthetic"] is True and o["provenance"] and o["source"].endswith("(synthetic)")
        assert o["collection_status"] == "synthetic" and 0 <= o["confidence"] <= 1
    assert {o["entity_kind"] for o in result["observations"]} >= {"identity", "organization", "exposure"}
    # Deterministic: same input, same output.
    assert default_registry().enrich("svc-1@meridian.example")["observations"] == result["observations"]


def test_collection_requires_approval_and_never_goes_live_by_default():
    reg = default_registry()
    denied = reg.collect("http://synthetic-leak.example.onion", approved=False)
    assert denied["results"][0]["state"] == "unavailable" and denied["results"][0]["count"] == 0
    ok = reg.collect("http://synthetic-leak.example.onion", approved=True)
    assert ok["results"][0]["state"] == "synthetic"
    assert ok["results"][0]["observations"][0]["attributes"]["live"] is False


def test_live_adapters_refuse_without_opt_in():
    assert TorBotCollectionAdapter().collect("x.onion", approved=True).state is SourceState.UNAVAILABLE
    assert HorusEnrichmentAdapter().enrich("glass-harbor-sync.example").state is SourceState.UNAVAILABLE
    assert MailAccessEnrichmentAdapter().enrich("a@b.example").state is SourceState.UNAVAILABLE


def test_live_opt_in_with_missing_tool_is_unavailable(monkeypatch):
    monkeypatch.setenv("GOTHAMITE_LIVE_COLLECTION", "1")
    monkeypatch.setenv("GOTHAMITE_ADAPTER_TORBOT", "1")
    monkeypatch.setenv("GOTHAMITE_TORBOT_CMD", "definitely-not-installed-torbot")
    r = TorBotCollectionAdapter().collect("x.onion", approved=True)
    assert r.state is SourceState.UNAVAILABLE and "not installed" in r.error


def test_adapter_exception_is_captured_not_raised():
    class Broken(EnrichmentAdapter):
        name, kinds = "broken", ("email",)
        def state(self): return SourceState.SYNTHETIC
        def enrich(self, value, kind=None): raise RuntimeError("boom")
    class Off(EnrichmentAdapter):
        name, kinds = "broken", ("email",)
        def state(self): return SourceState.UNAVAILABLE
    reg = AdapterRegistry([(Off(), Broken()), (MailAccessEnrichmentAdapter(), SyntheticMailAccessAdapter())],
                          [(TorBotCollectionAdapter(), SyntheticTorBotAdapter())], DeepDarkCTIRegistry(path=""))
    out = reg.enrich("a@b.example")
    assert any(r["state"] == "error" and "boom" in r["error"] for r in out["results"])
    assert out["observations"]  # the healthy adapter still contributed


CATALOGUE = """|Telegram|Status|Name|
| ------ | ------ | ------ |
|https://t.me/example_one|ONLINE|Example Logs|
|https://t.me/example_two|OFFLINE|Old Channel|
|https://t.me/example_one|ONLINE|Example Logs|
"""


def test_catalogue_parser_is_registry_metadata():
    rows = parse_catalogue_markdown(CATALOGUE, "telegram", "deepdarkCTI/test.md (GPL-3.0, upstream)")
    assert len(rows) == 2  # header, separator, duplicate skipped
    assert rows[0].state is SourceState.AVAILABLE and rows[1].state is SourceState.UNAVAILABLE
    assert all(r.collection_method == "manual" and "deepdarkCTI" in r.provenance for r in rows)
    # A catalogue "ONLINE" is a place to look, never GOTHAMITE collecting now.
    assert all(r.state is not SourceState.CONNECTED for r in rows)


def test_registry_reads_local_clone_only(tmp_path):
    (tmp_path / "telegram_infostealer.md").write_text(CATALOGUE, encoding="utf-8")
    (tmp_path / "README.md").write_text("|x|ONLINE|y|", encoding="utf-8")
    reg = DeepDarkCTIRegistry(path=str(tmp_path))
    cats = {s.category for s in reg.sources() if s.provenance.startswith("deepdarkCTI")}
    assert cats == {"telegram"} and reg.state() is SourceState.AVAILABLE
    assert DeepDarkCTIRegistry(path="").state() is SourceState.SYNTHETIC


def test_api_endpoints_and_core_demo_unaffected(workbench):  # noqa: F811
    client, _ = workbench
    adapters = client.get(f"{BASE}/sources/adapters").json()["adapters"]
    assert {a["adapter"] for a in adapters} == {"mailaccess", "horus", "torbot", "deepdarkcti"}
    reg = client.get(f"{BASE}/sources/registry").json()
    assert reg["summary"]["total"] >= 5 and "Not collected intelligence" in reg["note"]
    enr = client.get(f"{BASE}/enrichment", params={"value": "glass-harbor-sync.example"}).json()
    assert enr["kind"] == "domain" and all(o["synthetic"] for o in enr["observations"])
    col = client.post(f"{BASE}/collection", json={"target": "http://synthetic-leak.example.onion"}).json()
    assert col["results"][0]["state"] == "unavailable"  # not approved
    # The canonical path is unchanged and works offline.
    assert client.get(f"{BASE}/search", params={"q": "203.0.113.42"}).json()["results"][0]["id"] == "IP-001"
    assert client.get(f"{BASE}/cases/INC-1042").json()["risk"]["score"] == 100
