"""Prepare GOTHAMITE's offline dataset snapshots (run once, by hand).

Reads raw public datasets the operator has downloaded, filters and normalizes
them, and writes bounded snapshots under ``backend/data_sources/``. The running
application never downloads anything; it only reads these snapshots.

Usage (from gothamite/):
  python scripts/prepare_datasets.py --darkforums path/to/safe_corpus.json \\
      --infoblox path/to/threat-intelligence [--infoblox-commit 5b5a12d]

Inputs:
  DarkForums Safe Corpus  https://doi.org/10.5281/zenodo.21991378  (CC BY 4.0)
  Infoblox Threat Intel   https://github.com/infobloxopen/threat-intelligence (CC BY 4.0)
DWData is NOT processed: no redistribution licence has been verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.data_sources.transform import (  # noqa: E402
    TRANSFORMATION_VERSION, normalize_forum_thread, normalize_infoblox_rows)

OUT = ROOT / "backend" / "data_sources"

# Bounded, deterministic Infoblox subset: small defensive CTI reports, including
# the three that independently list the same Decoy Dog infrastructure.
INFOBLOX_REPORTS = [
    "c2_beacon_20230414_iocs.csv",
    "decoy_dog_cta_20230420_iocs.csv",
    "decoy_dog_cta_20230714_iocs.csv",
    "detour_dog_20250930_iocs.csv",
    "pig_butchering_20250506_iocs.csv",
    "fake_captcha_20260423_iocs.csv",
    "volta_stealer_20260629_iocs.csv",
]

# Reference-derived marketplace reconstruction. These are NOT DWData records:
# categories follow DWData's documented per-market file taxonomy only; vendors,
# titles and prices are illustrative placeholders.
RECONSTRUCTION = [
    ("Security", "Reconstructed listing: account-security service (category template)", "illustrative band 10-50 USD"),
    ("Services", "Reconstructed listing: hosting service (category template)", "illustrative band 50-200 USD"),
    ("SoftwareandMalware", "Reconstructed listing: stealer malware offering (category template)", "illustrative band 100-500 USD"),
    ("SoftwareandMalware", "Reconstructed listing: loader offering (category template)", "illustrative band 200-800 USD"),
    ("DigitalProducts", "Reconstructed listing: data-leak bundle (category template)", "illustrative band 20-100 USD"),
    ("GuidesandTutorials", "Reconstructed listing: OPSEC guide (category template)", "illustrative band 5-30 USD"),
]


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--darkforums", required=True, type=Path)
    ap.add_argument("--infoblox", required=True, type=Path)
    ap.add_argument("--infoblox-commit", default="unknown")
    args = ap.parse_args()

    # DarkForums Safe Corpus (JSON Lines).
    threads, dropped, malformed = [], 0, 0
    for line in args.darkforums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        rec = normalize_forum_thread(raw)
        if rec is None:
            dropped += 1
        else:
            threads.append(rec)
    threads.sort(key=lambda t: int(t["thread_id"]) if t["thread_id"].isdigit() else 0)
    posts = [p for t in threads for p in t["posts"]]
    df_stats = {"threads_in": len(threads) + dropped + malformed, "threads_kept": len(threads),
                "threads_dropped": dropped, "malformed_lines": malformed, "posts_kept": len(posts),
                "posts_suppressed": sum(p["suppressed"] for p in posts)}
    (OUT / "darkforums").mkdir(parents=True, exist_ok=True)
    (OUT / "darkforums" / "forum_snapshot.json").write_text(
        json.dumps({"threads": threads}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # Infoblox bounded subset.
    iocs, rejected = [], 0
    for name in INFOBLOX_REPORTS:
        path = args.infoblox / "indicators" / "csv" / name
        rows, rej = normalize_infoblox_rows(path.read_text(encoding="utf-8", errors="replace"), name)
        iocs.extend(rows)
        rejected += rej
    ib_stats = {"reports": len(INFOBLOX_REPORTS), "indicators": len(iocs),
                "unique_indicators": len({r["indicator"] for r in iocs}), "rows_rejected": rejected}
    (OUT / "infoblox").mkdir(parents=True, exist_ok=True)
    (OUT / "infoblox" / "ioc_snapshot.json").write_text(
        json.dumps({"indicators": iocs}, indent=1) + "\n", encoding="utf-8")

    (OUT / "dwdata").mkdir(parents=True, exist_ok=True)
    (OUT / "dwdata" / "reconstruction.json").write_text(json.dumps({"listings": [
        {"id": f"RECON-{i + 1:02d}", "market": "reconstruction", "vendor": f"reconstruction-vendor-{i % 3 + 1:02d}",
         "category": cat, "title": title, "price": price, "rating": None}
        for i, (cat, title, price) in enumerate(RECONSTRUCTION)]}, indent=1) + "\n", encoding="utf-8")

    manifest = {
        "transformation_version": TRANSFORMATION_VERSION,
        "datasets": {
            "darkforums_safe_corpus": {
                "name": "Dataset for Threat Intelligence in Dark Web Forums (Safe Corpus)",
                "role": "forum intelligence", "provenance_class": "dataset_derived",
                "license": "CC BY 4.0", "doi": "10.5281/zenodo.21991378",
                "source_url": "https://zenodo.org/records/21991378",
                "dataset_version": "2026-08-18 (Zenodo record 21991378)",
                "raw_sha256": file_sha(args.darkforums), "bundled": "filtered snapshot",
                "snapshot": "darkforums/forum_snapshot.json", "stats": df_stats,
            },
            "infoblox_threat_intelligence": {
                "name": "Infoblox Threat Intelligence indicators",
                "role": "IOC intelligence", "provenance_class": "dataset_derived",
                "license": "CC BY 4.0", "doi": None,
                "source_url": "https://github.com/infobloxopen/threat-intelligence",
                "dataset_version": f"git {args.infoblox_commit}",
                "bundled": "bounded snapshot", "reports": INFOBLOX_REPORTS,
                "snapshot": "infoblox/ioc_snapshot.json", "stats": ib_stats,
            },
            "dwdata": {
                "name": "DWData dark web marketplace data (crcresearch)",
                "role": "marketplace reference", "provenance_class": "reference_derived",
                "license": "No licence declared; redistribution not verified",
                "doi": None, "source_url": "https://github.com/crcresearch/DWData",
                "dataset_version": "schema/taxonomy only", "bundled": "no raw records",
                "snapshot": "dwdata/reconstruction.json",
                "stats": {"reconstruction_listings": len(RECONSTRUCTION), "raw_records": 0},
            },
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"darkforums": df_stats, "infoblox": ib_stats}, indent=1))


if __name__ == "__main__":
    main()
