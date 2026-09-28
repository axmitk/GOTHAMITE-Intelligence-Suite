"""Offline analysis provider: transparent rules, never generated intelligence."""
from typing import Protocol
from backend.services.workbench_intelligence import context_for
from backend.services.workbench_seed import SNAPSHOT

STATES = ["NEW", "TRIAGED", "INVESTIGATING", "CONTAINMENT", "REMEDIATION", "RECOVERY", "CLOSED"]
NIST = [
    ("GOVERN", "GV.RR", "Roles, Responsibilities, and Authorities", "Assign an accountable analyst and document approval decisions."),
    ("IDENTIFY", "ID.AM", "Asset Management", "Validate affected assets, ownership and business criticality."),
    ("PROTECT", "PR.AA", "Identity Management, Authentication, and Access Control", "Review exposed identities and strengthen access controls."),
    ("DETECT", "DE.AE", "Adverse Event Analysis", "Correlate observations and preserve their provenance."),
    ("RESPOND", "RS.MI", "Incident Mitigation", "Review, approve and record simulated containment and remediation."),
    ("RECOVER", "RC.RP", "Incident Recovery Plan Execution", "Record restoration checks and lessons before closure."),
]


def risk_assessment(evidence, entities):
    by_kind = {}
    for ev in evidence:
        by_kind.setdefault(ev.kind, []).append(ev.id)
    factors = []

    def factor(label, points, ids, reason, dimension):
        if ids:
            factors.append({"label": label, "points": points, "evidence_ids": ids, "reason": reason, "dimension": dimension})

    factor("Malicious reputation observation", 20, by_kind.get("reputation", []), "A reputation source classifies this infrastructure as malicious; see each observation's provenance.", "reputation")
    factor("Internal sample detection", 25, by_kind.get("malware_detection", []), "A catalogued sample hash was observed internally. Execution and exfiltration remain unproven.", "observed behavior")
    factor("Network contact", 15, by_kind.get("network", []), "An internal sensor observed a connection to associated infrastructure.", "observed behavior")
    critical = [e for e in entities if e.kind == "asset" and e.attributes.get("business_criticality") == "critical"]
    factor("Critical business asset", 20, by_kind.get("context", []) if critical else [], "Inventory classifies an affected asset as business-critical.", "asset impact")
    factor("Exposure source claim", 10, by_kind.get("credential_exposure", []), "An unverified exposure claim adds investigation priority, not proof of compromise.", "exposure")
    # Tor exit-node listing is context about the infrastructure, not behavior: low weight, never a verdict.
    factor("TOR exit-node context", 5, by_kind.get("tor_context", []), "A Tor Project directory snapshot lists the IP as a Tor exit relay. Traffic from it may originate from any Tor user; this is context, not evidence of malicious intent.", "TOR context")
    kinds = {e.kind for e in evidence} - {"context", "mention", "tor_context", "tor_relay"}
    factor("Multiple observation types", 10, [e.id for e in evidence if e.kind in kinds] if len(kinds) >= 3 else [], "At least three observation types corroborate investigation scope; sources may not be independent.", "source corroboration")
    score = min(100, sum(f["points"] for f in factors))
    return {"score": score, "level": "critical" if score >= 80 else "high" if score >= 50 else "medium" if score >= 25 else "low",
            "factors": factors, "method": "risk-v1.1: sum of evidenced factors, capped at 100. Priority score, not probability. Missing evidence contributes zero.",
            "as_of": SNAPSHOT, "limitation": "Exercise baseline risk; approving a simulated action does not prove real risk reduction."}


def _provenance_phrase(evidence) -> str:
    counts = {}
    for e in evidence:
        p = getattr(e, "provenance", "synthetic")
        counts[p] = counts.get(p, 0) + 1
    label = {"synthetic": "synthetic", "dataset_derived": "dataset-derived", "reference_derived": "reference-derived"}
    parts = [f"{n} {label.get(k, k)}" for k, n in sorted(counts.items())]
    return (" and ".join(parts) + (" observation" if len(evidence) == 1 else " observations")) if parts else "0 observations"


class AnalysisProvider(Protocol):
    def analyze(self, evidence, entities) -> dict: ...


class EvidenceRuleProvider:
    def analyze(self, evidence, entities):
        findings = []
        rules = [
            ("network", "Infrastructure contact warrants investigation", "Observed network contact supports a scoped hunt. Contact alone does not establish malicious execution.", "Validate process ancestry and compare connection cadence with expected application traffic.", "medium"),
            ("malware_detection", "Known exercise sample observed internally", "The sample hash matches the synthetic catalog. Process execution and persistence require separate evidence.", "Preserve host telemetry and inspect related processes before simulated isolation.", "high"),
            ("credential_exposure", "Possible credential exposure requires validation", "A synthetic source references a service identity. Neither a valid password nor account takeover is established.", "Review identity logs and validate exposure before approving a simulated credential reset.", "low"),
            ("tor_context", "Source infrastructure is a Tor exit relay", "The Tor Project directory snapshot lists the IP as an exit relay, so the true origin is hidden and may be shared by many users. This neither confirms nor excludes malicious activity.", "Decide whether the affected service should accept Tor-originated connections, and judge the activity by its observed behavior.", "high"),
            ("context", "Campaign association is contextual", "Shared scenario infrastructure supports a campaign link. It does not establish an individual actor's identity.", "Compare independent telemetry and retain alternative hypotheses.", "low"),
        ]
        for kind, title, interpretation, next_step, confidence in rules:
            supporting = [e for e in evidence if e.kind == kind]
            if kind == "context" and not any(e.kind == "campaign" for e in entities):
                continue  # inventory-only context makes no campaign claim
            if supporting:
                findings.append({"id": f"finding-{kind}", "title": title, "interpretation": interpretation,
                                 "evidence_ids": [e.id for e in supporting], "confidence": confidence,
                                 "reasoning": [e.title for e in supporting], "next_step": next_step})
        assets = [e.label for e in entities if e.kind == "asset"]
        return {"provider": "Evidence rules v1 — offline analysis (not an LLM)", "generated": False,
                "summary": f"{_provenance_phrase(evidence)} support this investigation, with {_count(len(assets), 'asset')} in its evidence context. Prioritize validation of internal observations before response." if evidence else "Insufficient evidence. No classification or response inference is available.",
                "findings": findings, "uncertainties": ["No confirmed data exfiltration or real-world actor attribution.",
                    "Source confidence is an annotation, not a calibrated probability." if any(getattr(e, "provenance", "synthetic") != "synthetic" for e in evidence)
                    else "Synthetic source confidence is an exercise annotation, not a calibrated probability.",
                    "Simulated response does not validate recovery of real systems."]}


def analyze(db, id):
    evidence, entities = context_for(db, id)
    return EvidenceRuleProvider().analyze(evidence, entities)


def recommendations(evidence):
    kinds = {e.kind for e in evidence}
    definitions = [
        ("preserve", "Preserve forensic evidence", "P1", "DE.AE", "Capture evidence before changing the environment.", "Retains an investigation baseline.", kinds),
        ("isolate", "Isolate affected endpoint", "P1", "RS.MI", "Internal sample detection and network contact warrant analyst-reviewed isolation.", "Would restrict lateral movement; may interrupt the business service.", {"malware_detection"}),
        ("block", "Block associated infrastructure", "P1", "RS.MI", "Review the corroborated network and reputation observations.", "Would interrupt associated outbound communication; validate dependencies first.", {"reputation"}),
        ("identity", "Review and revoke exposed credentials", "P2", "PR.AA", "An exposure bulletin references a service identity; validate it first.", "Would invalidate affected sessions; coordinate service-account rotation.", {"credential_exposure"}),
        ("hunt", "Hunt related assets for indicators", "P2", "RS.AN", "The network observation identifies a starting point for a scoped hunt.", "Would establish whether activity extends beyond the observed host.", {"network"}),
        ("remediate", "Remove persistence and validate configuration", "P2", "RS.MI", "Sample detection warrants a reviewed remediation plan after containment.", "Would remove confirmed persistence and validate service configuration.", {"malware_detection"}),
        ("recover", "Validate restoration and record lessons", "P2", "RC.RP", "Recovery requires analyst checks; absence of new alerts is not sufficient.", "Records backup validation, service checks and follow-up monitoring in the exercise.", kinds),
    ]
    return [{"rule": rule, "title": title, "priority": priority, "nist": nist, "reason": reason, "effect": effect,
             "evidence_ids": [e.id for e in evidence if e.kind in required], "simulated": True}
            for rule, title, priority, nist, reason, effect, required in definitions if kinds & required]


NIST_EVIDENCE = {"IDENTIFY": {"context"}, "PROTECT": {"credential_exposure"},
                 "DETECT": {"dns", "network", "reputation", "malware_detection", "mention", "tor_context"}}


def _count(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def nist_mapping(case, notes, actions, evidence=(), recs=()):
    """Map case evidence and response decisions to CSF 2.0 functions.

    Every row cites the observations and response recommendations it is based on,
    so the framework view is traceable rather than decorative."""
    statuses = {a.rule: a.status for a in actions}
    reviewed = any(statuses.get(rule) == "simulated" for rule in ("isolate", "block", "identity", "remediate"))
    completed = [bool(case.analyst), True, statuses.get("identity") == "simulated", True, reviewed,
                 case.status == "CLOSED" and any(n.kind == "recovery" for n in notes)]
    decisions = sum(1 for a in actions if a.status in ("approved", "simulated", "rejected"))
    note_kinds = [n.kind for n in notes]
    rows = []
    for i, (function, category, title, activity) in enumerate(NIST):
        prefix = category.split(".")[0]
        linked = [{"rule": r["rule"], "title": r["title"], "category": r["nist"], "status": statuses.get(r["rule"], "pending")}
                  for r in recs if r["nist"].split(".")[0] == prefix]
        ids = [e.id for e in evidence if e.kind in NIST_EVIDENCE.get(function, set())]
        if function == "GOVERN":
            basis = f"Accountable analyst: {case.analyst or 'unassigned'}. {_count(decisions, 'response decision')} recorded in the audit trail."
        elif function == "IDENTIFY":
            basis = "Asset inventory context identifies affected assets and their business criticality." if ids else "Insufficient evidence: no asset inventory observation is attached."
        elif function == "PROTECT":
            basis = "An exposure claim references an identity; access review is warranted." if ids else "No identity exposure is observed for this case."
        elif function == "DETECT":
            basis = f"{_count(len(ids), 'detection observation')} correlated with preserved provenance and integrity hashes." if ids else "Insufficient evidence: no detection observations are attached."
        elif function == "RESPOND":
            done = sum(1 for a in linked if a["status"] == "simulated")
            basis = f"{done} of {_count(len(linked), 'mitigation recommendation')} approved and simulated." if linked else "Insufficient evidence to recommend mitigation."
            ids = sorted({x for r in recs if r["nist"].startswith("RS") for x in r["evidence_ids"]})
        else:
            basis = (f"Recovery validation notes: {note_kinds.count('recovery')}; lessons learned: {note_kinds.count('lesson')}. "
                     "Closure requires both and the simulated recovery action.")
        rows.append({"function": function, "category": category, "title": title, "activity": activity,
                     "status": "documented" if completed[i] else "pending review",
                     "basis": basis, "evidence_ids": ids, "actions": linked})
    return rows
