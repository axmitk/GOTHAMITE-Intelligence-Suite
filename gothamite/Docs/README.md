# Design documents (historical)

These files are the original planning and design notes for the persona
correlation subsystem and the early build plan. They are kept for context, not
as a description of what is implemented. Where they disagree with the code,
the code and these current documents win:

- [README](../../README.md): what runs, the demo path and verification results
- [ARCHITECTURE](../../docs/ARCHITECTURE.md): implemented architecture and boundaries
- [DATA_SOURCES](../../docs/DATA_SOURCES.md): datasets, provenance and the case library
- [THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES.md): licences and attribution

Superseded numbers: the wallet weight is now +0.25 (it was +0.45), so the rebrand
link scores 0.40 (it was 0.60); see [scoring rationale](../../docs/scoring_rationale.md).
"Benchmark" in these notes means the team-written scenario set, which checks the rules
and does not measure real-world accuracy. Streamlit and `docker compose` describe the
original build; the current demo is the React workbench.

`reports/` holds per-phase build reports from that earlier work.
