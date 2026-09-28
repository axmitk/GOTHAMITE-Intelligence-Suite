"""Adapter registry: picks live or synthetic adapters and merges results.

For each capability the registry prefers the process-isolated live adapter only
when it is enabled and available; otherwise it falls back to the deterministic
synthetic adapter. Adapter failures are captured per adapter and never raised.
"""
from __future__ import annotations

from backend.collection.base import AdapterResult, SourceState, dedupe, infer_kind
from backend.collection.sources import DeepDarkCTIRegistry


class AdapterRegistry:
    def __init__(self, enrichers, collectors, source_registry) -> None:
        # enrichers/collectors: list of (live_adapter, synthetic_adapter) pairs
        self.enrichers = enrichers
        self.collectors = collectors
        self.source_registry = source_registry

    @staticmethod
    def _pick(pair):
        live, synthetic = pair
        state = live.state()
        if state in (SourceState.AVAILABLE, SourceState.CONNECTED):
            return live
        return synthetic

    def status(self) -> list[dict]:
        rows = []
        for kind, pairs in (("enrichment", self.enrichers), ("collection", self.collectors)):
            for live, synthetic in pairs:
                live_state = live.state()
                active = self._pick((live, synthetic))
                rows.append({
                    "adapter": live.name, "type": kind, "kinds": list(live.kinds),
                    "live_state": live_state.value,
                    "active_state": active.state().value,
                    "mode": "live" if active is live else "synthetic",
                })
        rows.append({"adapter": self.source_registry.name, "type": "source-registry",
                     "kinds": ["source"], "live_state": self.source_registry.state().value,
                     "active_state": self.source_registry.state().value,
                     "mode": "registry"})
        return rows

    def enrich(self, value: str) -> dict:
        kind = infer_kind(value)
        results: list[AdapterResult] = []
        for pair in self.enrichers:
            adapter = self._pick(pair)
            if kind not in adapter.kinds:
                continue
            try:
                results.append(adapter.enrich(value, kind))
            except Exception as exc:  # adapters must never break the core
                results.append(AdapterResult(adapter.name, SourceState.ERROR, [], error=str(exc)[:300]))
        observations = dedupe(o for r in results for o in r.observations)
        return {"value": value, "kind": kind,
                "results": [{k: v for k, v in r.to_dict().items() if k != "observations"} for r in results],
                "observations": [o.to_dict() for o in observations]}

    def collect(self, target: str, *, approved: bool) -> dict:
        results = []
        for pair in self.collectors:
            adapter = self._pick(pair)
            try:
                results.append(adapter.collect(target, approved=approved))
            except Exception as exc:
                results.append(AdapterResult(adapter.name, SourceState.ERROR, [], error=str(exc)[:300]))
        return {"target": target, "approved": approved, "results": [r.to_dict() for r in results]}


def default_registry() -> AdapterRegistry:
    from backend.collection.adapters.isolated import (
        HorusEnrichmentAdapter, MailAccessEnrichmentAdapter, TorBotCollectionAdapter)
    from backend.collection.adapters.synthetic import (
        SyntheticHorusAdapter, SyntheticMailAccessAdapter, SyntheticTorBotAdapter)
    return AdapterRegistry(
        enrichers=[(MailAccessEnrichmentAdapter(), SyntheticMailAccessAdapter()),
                   (HorusEnrichmentAdapter(), SyntheticHorusAdapter())],
        collectors=[(TorBotCollectionAdapter(), SyntheticTorBotAdapter())],
        source_registry=DeepDarkCTIRegistry(),
    )
