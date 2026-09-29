# Third-party notices

GOTHAMITE evaluates four open-source CTI/OSINT projects as **source adapters**.
**No source code from any of them is vendored into this repository.** The core
(`gothamite/backend/collection/`) defines its own interfaces and synthetic
fixtures; real tools can only be reached as separately installed programs over a
process boundary, and that path is disabled by default.

Audited 2026-09-28 at the upstream commits listed below.

| Repository | Licence | Audited commit | Integration boundary | Vendored? | Enabled in demo | Status in this build |
| --- | --- | --- | --- | --- | --- | --- |
| [deepdarkCTI](https://github.com/fastfire/deepdarkCTI) | GPL-3.0 | `736e66b` | Parser reads a **local clone** supplied via `GOTHAMITE_DEEPDARKCTI_PATH` | No | Synthetic registry only | **Integrated** as source registry (parser + normalization) |
| [TorBot](https://github.com/DedSecInside/TorBot) | GPL-3.0 | `1cc500f` | Separate process (`torbot` CLI), one analyst-approved target per call | No | No (synthetic adapter) | Adapter wired, **disabled by default**; not exercised live |
| [horus](https://github.com/6abd/horus) | GPL-3.0 | `310bc10` | Separate process (`horus` CLI) | No | No (synthetic adapter) | Architectural only: live call **deliberately not wired** |
| [MailAccess](https://github.com/KatrielMoses/MailAccess) | MIT (declared in `pyproject.toml`; no LICENSE file in repo) | `ceac49b` (v0.17.6) | Separate process (`mailaccess` CLI) | No | No (synthetic adapter) | Architectural only: live call **deliberately not wired** |

## Public datasets (bundled as filtered snapshots)

| Dataset | Licence | Attribution | Bundled |
| --- | --- | --- | --- |
| Dataset for Threat Intelligence in Dark Web Forums (Safe Corpus) | CC BY 4.0 | Authors of the ICORIS 2026 study; DOI 10.5281/zenodo.21991378 | Filtered, transformed snapshot (`gothamite/backend/data_sources/darkforums/`) |
| Infoblox Threat Intelligence | CC BY 4.0 | Infoblox Threat Intel, github.com/infobloxopen/threat-intelligence @ 5b5a12d | Bounded 7-report snapshot (`gothamite/backend/data_sources/infoblox/`) |
| Tor Project Onionoo relay metadata | CC0 1.0 (Tor Metrics data) | The Tor Project, metrics.torproject.org / onionoo.torproject.org | Bounded 18-relay snapshot (`gothamite/backend/data_sources/tor/`) |
| DWData (crcresearch) | **No licence declared** | Notre Dame CRC research | **Not bundled.** Schema/taxonomy reference only |

Changes made to the CC BY 4.0 data: records filtered for safety (text withheld,
URLs removed), entities extracted, and fields normalized (see docs/DATA_SOURCES.md).
The GOTHAMITE reconstruction listings are not DWData content. The Onionoo
snapshot is reduced to the fields listed in docs/DATA_SOURCES.md. "Tor" is a trademark
of The Tor Project, Inc.; GOTHAMITE is not affiliated with or endorsed by it. The
Elastic Security Labs article on Tor exit-node monitoring was used as an
architectural reference only; no Elastic code is included.

## Audit notes

**deepdarkCTI.** Markdown tables of CTI *sources* (URL / status / name) across
~20 categories (Telegram, ransomware, forums, markets, exploits, CVEs), about
2,800 rows. Represented as **source metadata, not intelligence**. Catalogue
status `ONLINE`/`VALID` maps to `available` (a place an authorized analyst could
look), never to `connected`. GOTHAMITE never fetches any listed URL. Because the
catalogue is GPL-3.0, it is read from the operator's own clone at runtime rather
than copied into this repository.

**TorBot.** Onion crawler with link-tree, page metadata and liveness checks,
installed as the `torbot` CLI (httpx with SOCKS). Integrated only as a
collection adapter that requires, all together: `GOTHAMITE_LIVE_COLLECTION=1`,
`GOTHAMITE_ADAPTER_TORBOT=1`, an installed `torbot`, and an explicitly approved
target in the request. No queue or crawl from the UI; one target per call; a
timeout applies; failures are recorded as `error`. The live path has not been
run in this project.

**horus.** OSINT/forensics toolkit. Its dependencies include passive
lookups (whois, DNS, EXIF) but also active scanning (`python-nmap`), packet
capture (`pyshark`) and `onionshare_cli`. Only passive metadata is in scope.
No machine-readable passive-only mode could be guaranteed, so the live adapter
refuses to run and reports `available`/`unavailable`; the demo uses a synthetic
passive-metadata adapter.

**MailAccess.** Email OSINT platform (identity graph, exposure findings, exports).
It also contains active account-existence probing, mailbox verification and
proxy-rotation egress. Those capabilities are outside GOTHAMITE's defensive,
authorization-gated scope and are **not modelled or invoked**. The synthetic
adapter mirrors only its *findings shape* (identity, organization, exposure).
The declared MIT licence would permit reuse, but its text is not present in the
repository; confirm with upstream before copying any code.

## Licensing strategy

GPL-3.0 components are used only as independent programs communicating over a
process boundary (command-line invocation and stdout), which keeps them separate
works from GOTHAMITE. If any GPL code is ever copied or linked into GOTHAMITE,
the combined work must be distributed under GPL-3.0; review before doing so.
Upstream licence files and attribution remain with each upstream project.
