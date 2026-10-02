# PROBLEM_STATEMENT.md

**Repo:** `GOTHAMITE`
**Status:** Complete. §2 holds the official description from the SIH portal.

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

> • Background The dark web has become a preferred operating space for threat actors in the modern age, mainly because it lets them hide their identity behind Tor hidden services, which makes attribution of threat actors operating on darkweb the main challenge for any investigation. Such threat actors carry out a wide range of unlawful activities such as drugs and arms sale, stolen data and hacking services, money laundering, terror financing, etc. The objective of this problem statement is to build a system for the deanonymization of dark web threat actors and link them to suspect real-world entities.
>
> • Description The system shall deanonymize dark web threat actors by continuously gathering their footprints from a range of sources (marketplaces, forums, deep web etc.) and linking them to the identifying information available on those sources. The system envisages three core capabilities. First, finding misconfigurations in Tor hidden services—such as exposed server-status pages, SSL certificates tied to clearnet domains, default service banners, descriptor inconsistencies, etc and matching them with clearnet infrastructure to point to the likely origin servers. Second, mapping threat actors across multiple marketplaces into a single relationship graph of handles, PGP keys, wallets and trust links. Third, using AI-based analysis, including stylometric persona identification and behavioural profiling, to link rebranded or migrated personas to known threat actors. The system shall provide an analytical front end to query the database across a chosen timeline and shall work in an autonomous mode, drawing on available sources of good quality and reliability.
>
> • Expected Solution An end-to-end system shall be developed for the collection, storage, contextualization and querying (through GUI/dashboards) of dark web threat actor intelligence—covering actor profiles, identifiers (handles, PGP keys, wallets etc.), hidden service infrastructure indicators, persona linkages, attribution confidence, category, last scan date and source. The system shall also provide the facility to export the result set in CSV, JSON and report formats.

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
