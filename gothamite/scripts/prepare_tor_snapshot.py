"""Build the bounded Tor Project Onionoo snapshot from LOCAL Onionoo JSON files.

Offline only: this script never fetches anything. Download Onionoo ``details``
documents yourself (https://onionoo.torproject.org/details), then run:

    python -m scripts.prepare_tor_snapshot --retrieved 2026-09-28 details1.json [details2.json ...]

Writes backend/data_sources/tor/onionoo_snapshot.json. The runtime importer reads
only that file; GOTHAMITE never contacts Onionoo or the Tor network.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.data_sources.transform import TOR_TRANSFORMATION_VERSION, normalize_onionoo_relay

OUT = Path(__file__).resolve().parents[1] / "backend" / "data_sources" / "tor" / "onionoo_snapshot.json"


def build(files: list[Path], retrieved: str) -> dict:
    relays, published, rejected = {}, set(), 0
    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        published.add(doc.get("relays_published"))
        for raw in doc.get("relays", []):
            rec = normalize_onionoo_relay(raw)
            if rec is None:
                rejected += 1
                continue
            relays[rec["fingerprint"]] = rec  # same relay in two queries: keep one record
    snapshot = sorted(p for p in published if p)
    return {"source": "Tor Project Onionoo (details documents)",
            "source_url": "https://onionoo.torproject.org/details",
            "relays_published": snapshot[-1] if snapshot else None,
            "retrieved": retrieved, "transformation_version": TOR_TRANSFORMATION_VERSION,
            "note": "Bounded point-in-time snapshot for an offline prototype. It does not describe current Tor network state.",
            "stats": {"relays": len(relays), "rejected": rejected,
                      "exit_relays": sum(r["exit"] for r in relays.values()),
                      "running": sum(r["running"] for r in relays.values())},
            "relays": sorted(relays.values(), key=lambda r: (not r["exit"], not r["running"], r["nickname"].lower()))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()
    data = build(a.files, a.retrieved)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(data["stats"]))


if __name__ == "__main__":
    main()
