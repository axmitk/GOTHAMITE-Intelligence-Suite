"""Adapter interfaces and the normalized observation shape.

The GOTHAMITE core consumes only what is defined here. An adapter takes an
analyst-approved request and returns an :class:`AdapterResult`: an explicit
:class:`SourceState`, zero or more normalized :class:`Observation` records with
provenance, and (on failure) a captured error — never a raised exception that
could break the core investigation flow.

Nothing in this module performs network I/O. Concrete adapters live in
``backend.collection.adapters`` and either return synthetic fixtures or shell
out to a process-isolated external tool that is disabled by default.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Protocol, runtime_checkable


class SourceState(str, Enum):
    """Explicit collection state. Never render SYNTHETIC as live intelligence."""

    SYNTHETIC = "synthetic"      # deterministic fixture data (demo/tests)
    CONNECTED = "connected"      # adapter enabled and reachable now
    AVAILABLE = "available"      # adapter installed/configured but not queried this run
    UNAVAILABLE = "unavailable"  # adapter disabled, tool absent, or offline
    ERROR = "error"             # last attempt failed; see AdapterResult.error


# GOTHAMITE indicator/entity kinds an observation may resolve to. Kept aligned
# with backend.services.workbench_intelligence.INDICATOR_KINDS plus the
# correlation entity kinds the workbench already models.
ENTITY_KINDS = (
    "ip", "domain", "hash", "url", "email",
    "identity", "account", "organization", "exposure",
    "threat_actor", "campaign", "malware", "source",
)

_ISO = "%Y-%m-%dT%H:%M:%SZ"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime(_ISO)


@dataclass(frozen=True)
class Source:
    """A registry entry: where intelligence *could* be collected from.

    A source is catalogue metadata, not collected intelligence. ``reliability``
    is an analyst-facing annotation, not a measured score.
    """

    id: str
    name: str
    category: str           # telegram | forum | ransomware | market | ...
    reference: str          # url or handle (may be non-navigable)
    collection_method: str  # manual | torbot | api | none
    state: SourceState
    reliability: str        # high | medium | low | unknown
    provenance: str         # where this registry row came from
    last_observed: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        return d


@dataclass(frozen=True)
class Observation:
    """One normalized, provenance-bearing finding from an adapter.

    ``entity_kind`` maps into the GOTHAMITE entity model; ``value`` is the
    indicator/identifier; ``attributes`` carries structured, non-authoritative
    context. ``confidence`` is a 0..1 annotation, never a probability of guilt.
    """

    adapter: str
    source: str
    entity_kind: str
    value: str
    observed_at: str
    confidence: float
    provenance: str
    synthetic: bool
    summary: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    source_type: str = "osint"            # email-osint | dark-web | osint-metadata | registry
    relationship: str = "observed_with"   # relation to the queried indicator
    collection_status: str = "synthetic"  # SourceState value at collection time

    def __post_init__(self) -> None:
        if self.entity_kind not in ENTITY_KINDS:
            raise ValueError(f"unknown entity_kind: {self.entity_kind!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence!r}")
        if not self.value:
            raise ValueError("observation value must be non-empty")

    @property
    def id(self) -> str:
        """Stable content id, used for deduplication across adapters/runs."""
        basis = f"{self.entity_kind}|{self.value.strip().lower()}|{self.source}"
        return "obs-" + hashlib.sha256(basis.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id
        return d


@dataclass
class AdapterResult:
    """Uniform adapter return: state, observations, provenance, optional error."""

    adapter: str
    state: SourceState
    observations: list[Observation] = field(default_factory=list)
    error: str | None = None
    queried_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "state": self.state.value,
            "queried_at": self.queried_at,
            "error": self.error,
            "count": len(self.observations),
            "observations": [o.to_dict() for o in self.observations],
        }


def dedupe(observations: Iterable[Observation]) -> list[Observation]:
    """Collapse observations with the same content id, keeping the highest
    confidence. Order-stable on first appearance."""
    best: dict[str, Observation] = {}
    order: list[str] = []
    for obs in observations:
        key = obs.id
        if key not in best:
            best[key] = obs
            order.append(key)
        elif obs.confidence > best[key].confidence:
            best[key] = obs
    return [best[k] for k in order]


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_IP_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def infer_kind(value: str) -> str | None:
    """Best-effort indicator classification for adapter inputs (offline)."""
    v = value.strip()
    if _EMAIL_RE.match(v):
        return "email"
    if _IP_RE.match(v):
        return "ip"
    if re.fullmatch(r"[a-fA-F0-9]{32,64}", v):
        return "hash"
    if v.startswith(("http://", "https://")):
        return "url"
    if "." in v and " " not in v:
        return "domain"
    return None


@runtime_checkable
class Adapter(Protocol):
    """Common adapter metadata contract."""

    name: str

    def state(self) -> SourceState: ...


class CollectionAdapter:
    """Collects observations from a (usually external) source for an approved
    target. Subclasses must not raise on collection failure; return an
    ``AdapterResult`` with ``SourceState.ERROR`` instead."""

    name: str = "collection"
    kinds: tuple[str, ...] = ()

    def state(self) -> SourceState:  # pragma: no cover - overridden
        return SourceState.UNAVAILABLE

    def collect(self, target: str, *, approved: bool = False) -> AdapterResult:
        raise NotImplementedError


class EnrichmentAdapter:
    """Enriches an existing GOTHAMITE indicator with normalized observations."""

    name: str = "enrichment"
    kinds: tuple[str, ...] = ()

    def state(self) -> SourceState:  # pragma: no cover - overridden
        return SourceState.UNAVAILABLE

    def enrich(self, value: str, kind: str | None = None) -> AdapterResult:
        raise NotImplementedError


class SourceRegistryAdapter:
    """Exposes a catalogue of sources (registry), not collected intelligence."""

    name: str = "registry"

    def state(self) -> SourceState:  # pragma: no cover - overridden
        return SourceState.AVAILABLE

    def sources(self) -> list[Source]:
        raise NotImplementedError
