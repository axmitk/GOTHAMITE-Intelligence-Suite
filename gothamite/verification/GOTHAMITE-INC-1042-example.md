# GOTHAMITE / INC-1042



SYNTHETIC EXERCISE — no real intelligence or response execution.



Finance gateway beaconing

Generated from the saved investigation trail. Observations, interpretation and approvals are distinct.

Status: CONTAINMENT | Analyst: Demo analyst | Severity: critical

Created: 2026-09-28T09:00:00Z | Updated: 2026-09-28T10:28:37.377676Z | Version: 5



## Executive summary

6 synthetic observations and 16 evidence-backed relationships support this case. Baseline risk is 100/100 (critical) from 6 evidenced factors.

Rule-based findings: Infrastructure contact warrants investigation (medium confidence); Known exercise sample observed internally (high confidence); Possible credential exposure requires validation (low confidence); Campaign association is contextual (low confidence).

Response: 1 of 7 recommendations reviewed (1 simulated, 0 rejected). Case stage: CONTAINMENT.



## Observed evidence (synthetic)

### OBS-DNS-001 — DNS resolution: glass-harbor-sync.example

2026-09-28T08:35:00Z | Synthetic DNS | confidence annotation: 0.9

EXERCISE DNS: glass-harbor-sync.example resolves to 203.0.113.42. This is a generated observation, not a network lookup.

SHA-256: 086e1b99cdabe3207fff482863944c73c8c021605f2eadcc307c5bf426a11541



### EV-1-CONTEXT — Campaign context and asset inventory

2026-09-28T08:38:00Z | Synthetic intelligence / CMDB | confidence annotation: 0.7

EXERCISE: Grey Moth is the fictional cluster assigned to Glass Harbor; SableLoader is its sample label. FIN-GW-01 is owned by the named service team. These associations are scenario context, not proof of actor identity.

SHA-256: dadc32f8ab6ad883a026f848d6b4e521a2553664b8d6ac7ec553b88823b45478



### EV-1-NETWORK — Repeated outbound connections

2026-09-28T08:42:00Z | Synthetic network sensor | confidence annotation: 0.94

EXERCISE sensor: FIN-GW-01 connected to 203.0.113.42 via glass-harbor-sync.example. 14 connections at 60-second intervals; review potential beaconing.

SHA-256: ae9aeba746031c216c13fd715f45ba752e793d67b3d91ea7016de5a09424db68



### EV-1-REPUTATION — Infrastructure flagged by exercise feed

2026-09-28T08:44:00Z | Synthetic reputation feed | confidence annotation: 0.9

EXERCISE feed marks glass-harbor-sync.example and 203.0.113.42 as malicious based on the synthetic campaign fixture. No external reputation service was queried.

SHA-256: 447947dfb69b30624131874aac92782840daba5a23f00db939f9fc6b80197bdc



### EV-1-MALWARE — Sample hash matched on finance gateway

2026-09-28T08:51:00Z | Synthetic EDR | confidence annotation: 0.96

EXERCISE EDR: b9523b207b7122270a8351adec7d86e567b8585a5eacebe5d25449c510e7f75b observed on FIN-GW-01; the exercise catalog associates this hash with SableLoader. A hash match alone does not prove execution or data loss.

SHA-256: f76888099585b504bcd1dcbfcdaf8058374978a0003df6632d0f95ef71cfa1f8



### EV-1-EXPOSURE — Unverified service identity exposure

2026-09-28T08:56:00Z | Synthetic exposure bulletin | confidence annotation: 0.6

EXERCISE bulletin references svc-1@meridian.example alongside glass-harbor-sync.example. This is a source claim; credential validity and account compromise are not established.

SHA-256: 205fea0ab4146a3e15a1a69aa738beeb60b2243712c5e7000972f3b482436687



## Correlated context

Evidence-backed associations; not proof of actor identity or compromise.

- threat_actor: Grey Moth (ACT-001)

- asset: FIN-GW-01 (AST-001)

- asset: FIN-WS-07 (AST-005)

- campaign: Glass Harbor (CAM-001)

- hash: b9523b207b7122270a8351adec7d86e567b8585a5eacebe5d25449c510e7f75b (HASH-001)

- malware: SableLoader (MAL-001)

- organization: Meridian Research (ORG-DEMO)

- vulnerability: SYN-VULN-2026-0001 (VULN-001)

- domain: glass-harbor-sync.example (DOM-001)

- darkweb_mention: Meridian mention / Glass Harbor (DW-001)

- email: svc-1@meridian.example (EMAIL-001)

- ip: 203.0.113.42 (IP-001)

- url: https://glass-harbor-sync.example/update (URL-001)

### Supporting relationships

- Grey Moth → ASSOCIATED_WITH → Glass Harbor. Confidence: 0.7. Evidence: EV-1-CONTEXT

- FIN-GW-01 → BELONGS_TO → Meridian Research. Confidence: 0.7. Evidence: EV-1-CONTEXT

- FIN-GW-01 → CONNECTED_TO → FIN-WS-07. Confidence: 0.7. Evidence: EV-1-CONTEXT

- Glass Harbor → USES → glass-harbor-sync.example. Confidence: 0.75. Evidence: OBS-DNS-001

- Glass Harbor → USES → SableLoader. Confidence: 0.7. Evidence: EV-1-CONTEXT

- glass-harbor-sync.example → RESOLVES_TO → 203.0.113.42. Confidence: 0.85. Evidence: OBS-DNS-001

- Meridian mention / Glass Harbor → ASSOCIATED_WITH → Glass Harbor. Confidence: 0.6. Evidence: EV-1-EXPOSURE

- Meridian mention / Glass Harbor → MENTIONS → svc-1@meridian.example. Confidence: 0.6. Evidence: EV-1-EXPOSURE

- b9523b207b7122270a8351adec7d86e567b8585a5eacebe5d25449c510e7f75b → CONTACTS → glass-harbor-sync.example. Confidence: 0.7. Evidence: EV-1-CONTEXT

- b9523b207b7122270a8351adec7d86e567b8585a5eacebe5d25449c510e7f75b → OBSERVED_ON → FIN-GW-01. Confidence: 0.96. Evidence: EV-1-MALWARE

- Finance gateway beaconing → AFFECTS → FIN-GW-01. Confidence: 0.7. Evidence: EV-1-CONTEXT

- Finance gateway beaconing → INVESTIGATES → Glass Harbor. Confidence: 0.7. Evidence: EV-1-CONTEXT

- 203.0.113.42 → OBSERVED_ON → FIN-GW-01. Confidence: 0.85. Evidence: EV-1-NETWORK

- SableLoader → HAS_SAMPLE → b9523b207b7122270a8351adec7d86e567b8585a5eacebe5d25449c510e7f75b. Confidence: 0.7. Evidence: EV-1-CONTEXT

- https://glass-harbor-sync.example/update → HOSTED_ON → glass-harbor-sync.example. Confidence: 0.7. Evidence: EV-1-CONTEXT

- SYN-VULN-2026-0001 → AFFECTS → FIN-GW-01. Confidence: 0.7. Evidence: EV-1-CONTEXT



## Automated interpretation (offline evidence rules)

Automated interpretation, not observed fact. This exercise uses a deterministic rule provider, not an LLM.

Evidence rules v1 — offline analysis (not an LLM)

6 synthetic observations support this investigation, with 2 assets in its evidence context. Prioritize validation of internal observations before response.

- Infrastructure contact warrants investigation [medium] — Observed network contact supports a scoped hunt. Contact alone does not establish malicious execution. Evidence: EV-1-NETWORK. Next: Validate process ancestry and compare connection cadence with expected application traffic.

- Known exercise sample observed internally [high] — The sample hash matches the synthetic catalog. Process execution and persistence require separate evidence. Evidence: EV-1-MALWARE. Next: Preserve host telemetry and inspect related processes before simulated isolation.

- Possible credential exposure requires validation [low] — A synthetic source references a service identity. Neither a valid password nor account takeover is established. Evidence: EV-1-EXPOSURE. Next: Review identity logs and validate exposure before approving a simulated credential reset.

- Campaign association is contextual [low] — Shared scenario infrastructure supports a campaign link. It does not establish an individual actor's identity. Evidence: EV-1-CONTEXT. Next: Compare independent telemetry and retain alternative hypotheses.

### Uncertainties

No confirmed data exfiltration or real-world actor attribution.

Synthetic source confidence is an exercise annotation, not a calibrated probability.

Simulated response does not validate recovery of real systems.



## Risk assessment

100/100 — critical

risk-v1: sum of evidenced factors, capped at 100. Priority score, not probability. Missing evidence contributes zero.

Exercise baseline risk; approving a simulated action does not prove real risk reduction.

- +20 Malicious reputation observation — The exercise feed flags infrastructure; this is a synthetic reputation observation. Evidence: EV-1-REPUTATION

- +25 Internal sample detection — A catalogued sample hash was observed internally. Execution and exfiltration remain unproven. Evidence: EV-1-MALWARE

- +15 Network contact — An internal sensor observed a connection to associated infrastructure. Evidence: EV-1-NETWORK

- +20 Critical business asset — Inventory classifies an affected asset as business-critical. Evidence: EV-1-CONTEXT

- +10 Exposure source claim — An unverified exposure claim adds investigation priority, not proof of compromise. Evidence: EV-1-EXPOSURE

- +10 Multiple observation types — At least three observation types corroborate investigation scope; sources may not be independent. Evidence: OBS-DNS-001, EV-1-NETWORK, EV-1-REPUTATION, EV-1-MALWARE, EV-1-EXPOSURE



## NIST alignment

NIST CSF 2.0 investigation workflow: function applicability, supporting evidence and linked response status. Not a compliance assessment.

- GOVERN / GV.RR: Assign an accountable analyst and document approval decisions. (documented). Basis: Accountable analyst: Demo analyst. 1 response decision recorded in the audit trail.

- IDENTIFY / ID.AM: Validate affected assets, ownership and business criticality. (documented). Basis: Asset inventory context identifies affected assets and their business criticality. Evidence: EV-1-CONTEXT.

- PROTECT / PR.AA: Review exposed identities and strengthen access controls. (pending review). Basis: An exposure claim references an identity; access review is warranted. Evidence: EV-1-EXPOSURE. Response: Review and revoke exposed credentials — pending.

- DETECT / DE.AE: Correlate observations and preserve their provenance. (documented). Basis: 4 detection observations correlated with preserved provenance and integrity hashes. Evidence: OBS-DNS-001, EV-1-NETWORK, EV-1-REPUTATION, EV-1-MALWARE. Response: Preserve forensic evidence — pending.

- RESPOND / RS.MI: Review, approve and record simulated containment and remediation. (documented). Basis: 1 of 4 mitigation recommendations approved and simulated. Evidence: EV-1-MALWARE, EV-1-NETWORK, EV-1-REPUTATION. Response: Isolate affected endpoint — simulated; Block associated infrastructure — pending; Hunt related assets for indicators — pending; Remove persistence and validate configuration — pending.

- RECOVER / RC.RP: Record restoration checks and lessons before closure. (pending review). Basis: Recovery validation notes: 0; lessons learned: 0. Closure requires both and the simulated recovery action. Response: Validate restoration and record lessons — pending.

Source: https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf



## Response recommendations

Recommendation → analyst approval → simulation. No external system is changed.

- Preserve forensic evidence / pending / P1 — Capture evidence before changing the environment. Expected effect: Retains an investigation baseline. Evidence: OBS-DNS-001, EV-1-CONTEXT, EV-1-NETWORK, EV-1-REPUTATION, EV-1-MALWARE, EV-1-EXPOSURE. Decision note: No note recorded.

- Isolate affected endpoint / simulated / P1 — Internal sample detection and network contact warrant analyst-reviewed isolation. Expected effect: Would restrict lateral movement; may interrupt the business service. Evidence: EV-1-MALWARE. Decision note: No note recorded.

- Block associated infrastructure / pending / P1 — Review the corroborated network and reputation observations. Expected effect: Would interrupt associated outbound communication; validate dependencies first. Evidence: EV-1-REPUTATION. Decision note: No note recorded.

- Review and revoke exposed credentials / pending / P2 — An exposure bulletin references a service identity; validate it first. Expected effect: Would invalidate affected sessions; coordinate service-account rotation. Evidence: EV-1-EXPOSURE. Decision note: No note recorded.

- Hunt related assets for indicators / pending / P2 — The network observation identifies a starting point for a scoped hunt. Expected effect: Would establish whether activity extends beyond the observed host. Evidence: EV-1-NETWORK. Decision note: No note recorded.

- Remove persistence and validate configuration / pending / P2 — Sample detection warrants a reviewed remediation plan after containment. Expected effect: Would remove confirmed persistence and validate service configuration. Evidence: EV-1-MALWARE. Decision note: No note recorded.

- Validate restoration and record lessons / pending / P2 — Recovery requires analyst checks; absence of new alerts is not sufficient. Expected effect: Records backup validation, service checks and follow-up monitoring in the exercise. Evidence: OBS-DNS-001, EV-1-CONTEXT, EV-1-NETWORK, EV-1-REPUTATION, EV-1-MALWARE, EV-1-EXPOSURE. Decision note: No note recorded.



## Analyst decisions

Assigned analyst: Demo analyst. Local exercise seat; not verified identity.

### Response approvals

- Isolate affected endpoint: simulated. Note: No note recorded.

### Analyst conclusions and hypotheses

- 2026-09-28T10:28:36.484334Z / hypothesis / Demo analyst: Validate process ancestry. &lt;img src=x onerror=alert(1)&gt;



## Audit trail

Every case change, note, approval and simulation, in order. UTC.

- 2026-09-28T10:28:36.484334Z / Demo analyst / note_added: Added hypothesis entry

- 2026-09-28T10:28:37.238356Z / Demo analyst / response_approved: Isolate affected endpoint: Analyst reviewed supporting evidence. Simulation only; no system command executed.

- 2026-09-28T10:28:37.306247Z / Demo analyst / response_simulated: Isolate affected endpoint: Analyst reviewed supporting evidence. Simulation only; no system command executed.

- 2026-09-28T10:28:37.381779Z / Demo analyst / case_updated: status: INVESTIGATING → CONTAINMENT