"""Phase 5 -- the scraper agent.

Crawls the three mock sites through the simulated onion-routed network and
POSTs one artifact per page to the GOTHAMITE ingestion seam defined in
`AgentsDocs/API_CONTRACT.md`.

This package is the sandbox half of that seam and nothing else.  It does not
store artifacts, deduplicate them, score them, correlate them, or build any
graph: `API_CONTRACT.md` section 5 rule 3 puts all of that on GOTHAMITE's side,
deliberately and after ingest.
"""
