"""Source registry: the deepdarkCTI catalogue, normalized.

deepdarkCTI (GPL-3.0) is a catalogue of CTI *sources* (Telegram channels,
forums, ransomware sites, markets, ...). GOTHAMITE treats it as a **source
registry**, not as collected intelligence: a list of where an authorized analyst
*could* look, with status and provenance. The raw catalogue is never vendored
into this repository; the parser reads a local clone the operator supplies via
``GOTHAMITE_DEEPDARKCTI_PATH``. A small, clearly-synthetic registry is bundled so
the demo and tests need no external data.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from backend.collection.base import Source, SourceState, SourceRegistryAdapter
from backend.collection.config import config

# Map catalogue filenames to GOTHAMITE source categories. Files not listed are
# still parsed, defaulting to their stem as the category.
_CATEGORY = {
    "telegram_infostealer": "telegram",
    "telegram_threat_actors": "telegram",
    "ransomware_gang": "ransomware",
    "forum": "forum",
    "markets": "market",
    "discord": "discord",
    "exploits": "exploit-db",
    "cve_most_exploited": "exploit-db",
    "rat": "malware",
    "malware_samples": "malware",
    "maas": "malware-as-a-service",
    "phishing": "phishing",
    "search_engines": "search-engine",
}

# Upstream status vocabulary -> explicit GOTHAMITE SourceState. Anything the
# catalogue marks live/valid maps to AVAILABLE (a *place* to collect), never to
# CONNECTED (which means GOTHAMITE itself is collecting now).
_STATUS = {
    "VALID": SourceState.AVAILABLE,
    "ONLINE": SourceState.AVAILABLE,
    "UP": SourceState.AVAILABLE,
    "OFFLINE": SourceState.UNAVAILABLE,
    "EXPIRED": SourceState.UNAVAILABLE,
    "DOWN": SourceState.UNAVAILABLE,
}

_RELIABILITY = {
    SourceState.AVAILABLE: "medium",
    SourceState.UNAVAILABLE: "low",
}

_ROW = re.compile(r"^\|(.+)\|$")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "src"


def parse_catalogue_markdown(text: str, category: str, provenance: str) -> list[Source]:
    """Parse one deepdarkCTI markdown table into normalized Source records.

    Rows look like ``|<url>|<STATUS>|<name>|``. The header and separator rows,
    and any row whose first cell is not a reference, are skipped.
    """
    sources: list[Source] = []
    seen: set[str] = set()
    for line in text.splitlines():
        m = _ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) < 2:
            continue
        ref = cells[0]
        # Skip header/separator rows and non-reference rows.
        if not ref or set(ref) <= {"-", " ", ":"}:
            continue
        low = ref.lower()
        if low in {"telegram", "url", "name", "link", "source", "status"}:
            continue
        status_raw = cells[1].upper() if len(cells) > 1 else ""
        name = cells[2] if len(cells) > 2 else cells[-1]
        state = _STATUS.get(status_raw, SourceState.UNAVAILABLE)
        sid = f"ddcti-{category}-{_slug(name or ref)}"
        if sid in seen:
            continue
        seen.add(sid)
        sources.append(Source(
            id=sid,
            name=name or ref,
            category=category,
            reference=ref,
            collection_method="manual",
            state=state,
            reliability=_RELIABILITY.get(state, "unknown"),
            provenance=provenance,
            last_observed=None,
        ))
    return sources


# A small, explicitly-synthetic registry so the demo shows the model without any
# external clone. These are illustrative categories, not real destinations.
_SYNTHETIC_REGISTRY = [
    Source("syn-telegram-logs", "Synthetic infostealer log channel", "telegram",
           "tg://synthetic-exercise-channel", "manual", SourceState.SYNTHETIC,
           "medium", "GOTHAMITE synthetic registry", None),
    Source("syn-ransomware-leak", "Synthetic ransomware leak site", "ransomware",
           "http://synthetic-leak.example.onion", "torbot", SourceState.SYNTHETIC,
           "medium", "GOTHAMITE synthetic registry", None),
    Source("syn-forum-broker", "Synthetic access-broker forum", "forum",
           "http://synthetic-forum.example.onion", "torbot", SourceState.SYNTHETIC,
           "low", "GOTHAMITE synthetic registry", None),
    Source("syn-market-listing", "Synthetic marketplace", "market",
           "http://synthetic-market.example.onion", "torbot", SourceState.SYNTHETIC,
           "low", "GOTHAMITE synthetic registry", None),
    Source("syn-paste-exposure", "Synthetic paste/exposure feed", "exposure",
           "https://synthetic-paste.example", "api", SourceState.SYNTHETIC,
           "medium", "GOTHAMITE synthetic registry", None),
]


class DeepDarkCTIRegistry(SourceRegistryAdapter):
    """Source-registry adapter over a local deepdarkCTI clone plus a synthetic
    baseline. Never fetches anything; only reads local catalogue files."""

    name = "deepdarkcti"

    def __init__(self, path: str | None = None) -> None:
        self._path = path if path is not None else config.deepdarkcti_path

    def state(self) -> SourceState:
        return SourceState.AVAILABLE if self._path else SourceState.SYNTHETIC

    def sources(self) -> list[Source]:
        catalogue = self._from_clone() if self._path else []
        # The synthetic baseline always appears, clearly labelled, so the demo is
        # self-contained even when a real catalogue is present.
        return list(_SYNTHETIC_REGISTRY) + catalogue

    def _from_clone(self) -> list[Source]:
        root = Path(self._path or "")
        if not root.is_dir():
            return []
        out: list[Source] = []
        for md in sorted(root.glob("*.md")):
            stem = md.stem.lower()
            if stem in {"readme", "methods", "contributing"}:
                continue
            category = _CATEGORY.get(stem, stem.replace("_", "-"))
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            out.extend(parse_catalogue_markdown(
                text, category, provenance=f"deepdarkCTI/{md.name} (GPL-3.0, upstream)"))
        return out


def registry_summary(sources: list[Source]) -> dict:
    """Counts by category and state for the registry overview panel."""
    by_category: dict[str, int] = {}
    by_state: dict[str, int] = {}
    for s in sources:
        by_category[s.category] = by_category.get(s.category, 0) + 1
        by_state[s.state.value] = by_state.get(s.state.value, 0) + 1
    return {
        "total": len(sources),
        "synthetic": sum(1 for s in sources if s.state is SourceState.SYNTHETIC),
        "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
        "by_state": by_state,
    }
