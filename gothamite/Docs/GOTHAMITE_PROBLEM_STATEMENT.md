# PROBLEM_STATEMENT.md

**Repo:** `GOTHAMITE`
**Status:** ⚠️ **INCOMPLETE — Tanish must paste the official description into §2 before any agent reads this file.**

---

## 1. Official metadata

Verified against `SIH_2026_Problem_Statements.xlsx` (SIH 2026 software problem statements, 172 entries).

| Field | Value |
|---|---|
| PS Code | **SIH26151** |
| S.No | 121 |
| Title | Dark web threat actor de-anonymization |
| Organisation | National Technical Research Organisation (NTRO) |
| Category | Software |
| Theme | Blockchain & Cybersecurity |
| Submissions / Cap | 0 / 500 |
| **SIH submission deadline** | **20 September 2026** |

**Note on deadlines:** 20 September is the SIH submission deadline from the official sheet. **8 September is the internal college hackathon deadline** — the qualifying round. Confirm both with the college SIH coordinator; internal cut-offs sometimes govern team selection regardless of the national date.

---

## 2. Official description

> **PASTE THE VERBATIM NTRO DESCRIPTION FROM THE SIH PORTAL HERE.**
>
> Do not paraphrase it, do not summarise it, do not clean it up. Agents and the pitch both read from this. The spreadsheet contains metadata only — no description field — so this text has to come from the portal.

---

## 3. Capabilities requested

Reproduced from the team's project design document, which derived them from the full PS description. **Verify each against the official text in §2 once pasted** — if any differ, §2 is correct and this section gets corrected.

1. Continuously gather threat-actor footprints from marketplaces, forums, deep web and other suitable sources
2. Link footprints to identifying information available on those sources
3. Find Tor hidden-service misconfigurations — exposed server-status pages, SSL certificates tied to clearnet domains, default service banners, descriptor inconsistencies
4. Match hidden-service indicators with clearnet infrastructure to point to likely origin servers
5. Map actors across multiple marketplaces into a relationship graph of handles, PGP keys, wallets and trust links
6. Use AI-based analysis including stylometric persona identification and behavioural profiling
7. Link rebranded or migrated personas to known threat actors
8. Provide an analytical front end that queries the intelligence database across a chosen timeline
9. Operate in an autonomous mode using sources of good quality and reliability
10. Provide actor profiles, identifiers, infrastructure indicators, persona linkages, attribution confidence, category, last scan date and source
11. Export result sets as CSV, JSON and reports

**What is NOT required by the PS** — these are implementation choices, not NTRO requirements: a fully air-gapped system, a local LLM, TF-IDF, NetworkX, React, EXIF extraction, SQLite, or any particular language or framework.

This matters because the previous version of the team's pitch deck presented several of these as though they were requirements or differentiators. They are neither.

---

## 4. Build status

**This document states what was asked for. It says nothing about what was built.**

For the honest mapping of each capability above to BUILT / PARTIAL / DESIGNED / NOT BUILT, see **`REQUIREMENTS.md`**.

Nothing may be claimed on a slide, in the demo, or in Q&A unless `REQUIREMENTS.md` supports it.
