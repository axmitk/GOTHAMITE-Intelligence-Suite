# Data sources

GOTHAMITE holds three provenance classes of data. They are never mixed without a label.

| Dataset | Role | License | Bundled? | Provenance |
| --- | --- | --- | --- | --- |
| DarkForums Safe Corpus | Forum intelligence | CC BY 4.0 | Yes, filtered snapshot | Dataset-derived |
| Infoblox Threat Intelligence | IOC intelligence | CC BY 4.0 | Yes, bounded snapshot | Dataset-derived |
| Tor Project Onionoo | TOR exit-node intelligence | CC0 1.0 (Tor Metrics data) | Yes, bounded point-in-time snapshot | Dataset-derived |
| DWData | Marketplace reference | No licence declared; redistribution not verified | No raw records | Reference-derived |
| GOTHAMITE seed data | Deterministic demo | Project-owned | Yes | Synthetic |

All data is read from local files. **No live collection occurs**: nothing in the
application downloads, crawls, contacts a forum or marketplace, or starts Tor.

## 1. What is real public data

**DarkForums Safe Corpus** — *Dataset for Threat Intelligence in Dark Web Forums*,
DOI [10.5281/zenodo.21991378](https://doi.org/10.5281/zenodo.21991378), published
2026-08-18, CC BY 4.0. One `safe_corpus.json` file (JSON Lines, 201 threads, 154
posts), already PII-redacted by its authors. **Actual scope:** every thread is in
one sub-forum ("Databases", category "Leaks"). The threads are data-leak
advertisements, and the corpus contains **no CVE, CWE or ATT&CK identifiers**.
Raw file SHA-256: `c44b98f6d1a9faec0e1bf61d2a78461c5547b6a2216eb74fa42675dc75147949`.

**Infoblox Threat Intelligence** — <https://github.com/infobloxopen/threat-intelligence>,
commit `5b5a12d` (2026-09-15), CC BY 4.0. Bounded snapshot of seven reports:
`c2_beacon_20230414`, `decoy_dog_cta_20230420`, `decoy_dog_cta_20230714`,
`detour_dog_20250930`, `pig_butchering_20250506`, `fake_captcha_20260423`,
`volta_stealer_20260629`. That is 140 report listings of 121 unique indicators
(domains, IPs, hashes). The published `classification` is kept verbatim.

**Tor Project Onionoo** — relay metadata from <https://onionoo.torproject.org/details>
(Tor Metrics; data released under CC0 1.0). One bounded snapshot, **relays published
2026-09-28 17:00:00 UTC, retrieved 2026-09-28**: 18 relays (16 with the Exit flag,
12 running at snapshot time; 6 exit relays not running; 2 non-exit guard relays;
11 AS names). It is a point-in-time sample chosen for variety, **not current Tor
network state and not live Tor monitoring**. Kept per relay: fingerprint, nickname,
running, Exit flag, flags, exit and OR IPv4 addresses, first/last seen, AS/AS name,
country, observed bandwidth. Contact, platform, exit policy and IPv6 are dropped.
Transformation `gothamite-tor-1.0` (`transform.normalize_onionoo_relay`). The
architecture follows Elastic Security Labs' Tor exit-node monitoring pattern
(Onionoo → collection → normalization → stored relay intelligence → correlation
with security telemetry), reduced to a frozen snapshot: the app never contacts
Onionoo and never starts Tor.

## 2. What is filtered

`scripts/prepare_datasets.py` builds the snapshots, using
`backend/data_sources/transform.py` (`gothamite-ds-1.0`).

| Step | DarkForums | Infoblox |
| --- | --- | --- |
| Records in | 201 threads, 154 posts | 7 report CSVs |
| Dropped | 1 thread (title failed the safety check), with its 1 post | 1 row rejected |
| Kept | 200 threads, 153 posts | 140 listings |
| Text withheld | **110 of 153 posts** (redaction markers 106, credential references 17, phone-like numbers 14, encoded blobs 4, empty 2, financial 1) | n/a (no free text) |

Safety rules: redaction placeholders (`[EMAIL]`, `[PHONE]`, `[CREDENTIAL]`, …) are
markers, never entities, and are never reversed. Content with credentials,
secrets, card or account numbers, contact details, key material, encoded blobs or
executable content is withheld; only its SHA-256 is kept. URLs are replaced with
`[link removed]` in excerpts. Email indicators are not imported. Raw post content
is **not** in the bundle; the importer re-checks all free text at runtime.

Extraction keeps only defensive, non-personal entities: organization domains
(free-mail and file-hosting hosts excluded), countries, and CVE/CWE/ATT&CK
identifiers when present (none are present in this corpus).

## 3. What is synthetic

The GOTHAMITE seed: the four exercise cases (INC-1042 to INC-1045), 252
indicators, the Meridian Research organization and assets, and every observation
behind `203.0.113.42`. **The canonical demo remains fully synthetic.** No dataset
contains `203.0.113.42`, and none is linked to INC-1042.

### Synthetic case library (INC-1047 to INC-1052)

The library exists to exercise the complete workflow with different combinations
of the same primitives. **None of it describes a real incident.**

| Case | Pattern | Evidence | Status / severity | Response state |
| --- | --- | --- | --- | --- |
| INC-1042 | Canonical IOC exercise (unchanged) | 6 synthetic | Investigating / critical | All pending |
| INC-1047 | IOC + Tor context | 2 synthetic + 2 Onionoo | Investigating / medium | Preserve simulated; hunt approved, awaiting simulation |
| INC-1048 | One IOC, several independent sources | 5 synthetic (firewall, proxy, DNS, feed, CMDB) | Containment / high | Block and preserve simulated; hunt approved |
| INC-1049 | Forum claim + extracted entity | 7 DarkForums (thread 1289 and its posts) | Triaged / low | All pending |
| INC-1050 | Repeated Infoblox IOC (`ads-tm-glb.click`) | 3 Infoblox listings, one per report | New / medium | Preserve approved; block rejected with reason |
| INC-1051 | Credential exposure (placeholders only) | 3 synthetic | Investigating / high | Preserve approved; identity reset awaiting approval; hunt rejected |
| INC-1052 | Lookalike domain + DNS | 4 synthetic | Closed / low | Preserve, block, hunt, recover simulated; recovery and lesson notes |

Synthetic library values use documentation ranges (198.51.100.0/24) and reserved
`.example` domains. The one exception is INC-1047's source IP, 185.220.100.242,
a real Tor exit address taken from the snapshot: the VPN log that names it is
synthetic, and the Tor context reaches the case only through the exact-IP rule
below. INC-1049 and INC-1050 are dataset-derived cases built from imported
records; their workflow position is preset. Preset states are written with the
audit events that would produce them (approval before simulation, one stage at a
time) and fixed timestamps, so the library is deterministic. No credential,
password or secret value exists anywhere in the library.

## 4. What is reconstructed

DWData (<https://github.com/crcresearch/DWData>) declares no licence. Its README
says the data is "made publicly available" for security professionals, which is
not a redistribution grant. Therefore:

- **No DWData records are downloaded, bundled or redistributed.**
- `transform.project_marketplace_record()` implements the documented schema
  (vendor, name, category, price, rating) for data an operator supplies locally.
- Six **reference-derived reconstruction** listings follow only DWData's documented
  category taxonomy (DigitalProducts, GuidesandTutorials, Security, Services,
  SoftwareandMalware). Vendors, titles and prices are illustrative placeholders,
  labelled "Reference reconstruction", with confidence 0.3 and no relationships.

## 5. Provenance model

- `wb_entities.provenance` / `wb_evidence.provenance` ∈ `synthetic`,
  `dataset_derived`, `reference_derived`. Collection states for adapters
  (`synthetic`, `connected`, `available`, `unavailable`, `error`) are unchanged.
- `wb_dataset_records` (new, additive table) stores, per dataset-derived entity,
  evidence row and relationship: dataset, name, version, licence, source URL, DOI,
  `source_record_id`, `transformation_version`, `imported_at`, plus details
  (report file, thread/post ids, `observed_at_basis`).
- `observed_at` comes from the source when available. When a forum date is
  relative ("Less than 1 minute ago"), the dataset publication date is used for
  ordering and `observed_at_basis` records that substitution.
- Confidence values annotate how directly a record supports a relationship:
  0.9 = indicator in a published list, 0.6 = entity named in an unverified forum
  claim, 0.3 = reconstruction. They are not reputation scores.

## 6. Correlation (what the data actually supports)

- Infoblox: `indicator --OBSERVED_IN--> report`, one edge per report listing.
  **14 domains are listed in more than one report** and keep a separate supporting
  observation for each report (e.g. `claudfront.net`, `ads-tm-glb.click` in the C2
  beacon and both Decoy Dog reports).
- DarkForums: `thread --MENTIONS--> domain | country`, supported by the thread
  record. Several organization domains recur across threads (e.g. `castandcrew.com`).
- Cross-dataset: entity ids derive from the normalized value, so a domain present
  in both datasets becomes one entity with both observations. **In the bundled
  snapshots there is no overlap** (exact match: 0). The rule is proven with a test
  fixture, not claimed for the real data. No edge is created from text similarity.
- Tor Onionoo (rule `tor-exact-ip-v1`): `ip --ASSOCIATED_WITH--> tor_relay`, one
  edge and one observation per relay address. If GOTHAMITE already holds an IP entity
  with the **exact normalized IPv4 value** (from any source), the Onionoo observation
  is attached to that entity instead of creating a duplicate, and to any case whose
  evidence already cites it. No ASN, hostname, address-range or similarity match is
  used: 185.220.100.241 (same AS as INC-1047's address) is not linked to INC-1047.
  In the bundled data the only match is INC-1047's synthetic telemetry IP; the
  exercise 203.0.113.0/24 addresses and all Infoblox IPs match no relay.
- Tor context is **not a verdict**. Exit-relay observations are `tor_context`
  evidence: a separate "TOR context" risk dimension worth +5, a finding
  that states its limits, and DETECT evidence in NIST. Tor presence never
  sets reputation, never becomes a reputation factor and does not count toward
  "multiple observation types". A Tor-only IP scores 5/100 (low). Non-exit relay
  addresses are `tor_relay` observations and carry no risk points.
- Only Infoblox labels `malicious` and `malware` become reputation observations,
  scored by the existing +20 risk rule. `phishing`, `clickfix`, `suspicious` and
  `other` remain unscored classification observations.

## 7. Dataset-backed case

INC-1046 "Decoy Dog DNS infrastructure review" collects the 50 listings from the
C2 beacon and two Decoy Dog reports. Existing rules give it one risk factor
(malicious reputation, +20) and DETECT evidence. It states that no internal
telemetry links these domains to exercise assets. Its report carries an
"Evidence sources" block and a provenance line per observation.

## 8. Limitations

- One forum sub-forum; no CVE/ATT&CK content; no real cross-dataset overlap.
  The DarkForums and Infoblox datasets are deliberately left unconnected.
- The Tor snapshot is 18 relays from one moment; a relay's state changes hourly.
  A deployment would refresh Onionoo on a schedule; this prototype does not.
- 82 of 200 threads have no recoverable date.
- Report-level Infoblox data only; no enrichment beyond the published listing.
- DWData remains reference-only until a licence is confirmed with its maintainers.

## Rebuilding the snapshots

The Tor snapshot is rebuilt from Onionoo `details` documents you download
yourself; the script only reads local files:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_tor_snapshot --retrieved 2026-09-28 run.json down.json nonexit.json
```

The other datasets:

```powershell
# After downloading safe_corpus.json and cloning the Infoblox repository:
.\.venv\Scripts\python.exe scripts\prepare_datasets.py --darkforums <path>\safe_corpus.json `
    --infoblox <path>\threat-intelligence --infoblox-commit 5b5a12d
```
