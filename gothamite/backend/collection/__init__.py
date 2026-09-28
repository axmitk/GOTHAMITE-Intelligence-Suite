"""Collection and enrichment adapter layer for GOTHAMITE.

This package defines a source-adapter abstraction between external open-source
CTI/OSINT tools and the GOTHAMITE core. The core depends only on the interfaces
and the normalized ``Observation`` shape in :mod:`.base` — never on any third
party tool's internal code. Real tools (TorBot, horus, MailAccess) are reached
only through process-isolated adapters that are disabled by default; the demo
and tests run entirely on synthetic fixtures.

See ``THIRD_PARTY_NOTICES.md`` and ``ARCHITECTURE.md`` (Collection model).
"""
from backend.collection.base import (
    Observation,
    Source,
    SourceState,
    AdapterResult,
    CollectionAdapter,
    EnrichmentAdapter,
    SourceRegistryAdapter,
)
from backend.collection.registry import AdapterRegistry, default_registry

__all__ = [
    "Observation",
    "Source",
    "SourceState",
    "AdapterResult",
    "CollectionAdapter",
    "EnrichmentAdapter",
    "SourceRegistryAdapter",
    "AdapterRegistry",
    "default_registry",
]
