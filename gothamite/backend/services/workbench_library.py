"""Synthetic case library: deliberately fictional investigations that exercise the
same model, rules and workflow as the canonical INC-1042 exercise.

Each case combines the shared primitives differently (IOC + Tor context,
multi-source corroboration, credential exposure, domain + DNS) and starts in a
different workflow and response state. Nothing here is a real incident. IPs are
documentation ranges (198.51.100.0/24) except INC-1047's address, which is a real
Tor exit relay from the bundled Onionoo snapshot: the connection log that names it
is synthetic, and the Tor context is attached only by the importer's exact-IP rule.

INC-1049 and INC-1050 are dataset-derived and are created by the dataset importer
from imported records; their preset workflow state is defined here.
"""
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.models.workbench import (
    AuditEvent, CaseNote, EvidenceEntity, IncidentCase, IntelEntity, IntelEvidence, IntelRelationship, ResponseAction)

LIBRARY_SENTINEL = "INC-1047"
TOR_CASE_IP = "185.220.100.242"  # Onionoo snapshot relay F3Netze (exit); see DATA_SOURCES.md
ANALYST = "Demo analyst"


def _ts(base: str, minutes: int) -> str:
    start = datetime.fromisoformat(base.replace("Z", "+00:00"))
    return (start + timedelta(minutes=minutes)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def create_case(db: Session, id: str, title: str, summary: str, provenance: str, first: str, last: str) -> None:
    """Incident entity + case row. Workflow state is applied separately."""
    db.add(IntelEntity(id=id, kind="incident", label=title, summary=summary, source="Analyst case", confidence=0.9,
                       first_seen=first, last_seen=last, attributes={"library": "GOTHAMITE case library"},
                       provenance=provenance))
    db.flush()
    db.add(IncidentCase(id=id, status="NEW", severity="medium", analyst=ANALYST, created_at=last,
                        updated_at=last, version=1))
    db.flush()


def _apply_state(db: Session, case_id: str, status: str, severity: str, actions=(), notes=()) -> None:
    """Record a preset workflow position with the audit events that produce it.

    ``actions`` are (rule, final_status, note); approvals precede simulations in the
    audit trail exactly as the live workflow requires. Timestamps are fixed."""
    case = db.get(IncidentCase, case_id)
    from backend.services.workbench_analysis import STATES
    clock = [0]

    def at():
        clock[0] += 7
        return _ts(case.created_at, clock[0])

    def audit(action, detail):
        clock_ts = at()
        db.add(AuditEvent(id=f"AUD-{case_id}-{clock[0]:04}", case_id=case_id, actor=ANALYST, action=action,
                          detail=detail, created_at=clock_ts))
        return clock_ts

    if severity != case.severity:
        audit("case_updated", f"severity: {case.severity} → {severity}")
        case.severity = severity
    steps = {rule: final for rule, final, _ in actions}
    notes_by_state = {}
    for kind, text, state in notes:
        notes_by_state.setdefault(state, []).append((kind, text))

    def add_notes(state):
        for kind, text in notes_by_state.get(state, []):
            stamp = audit("note_added", f"Added {kind} entry")
            db.add(CaseNote(id=f"NOTE-{case_id}-{clock[0]:04}", case_id=case_id, kind=kind, text=text,
                            author=ANALYST, created_at=stamp))

    def decide(rule, final, note):
        from backend.services.workbench_analysis import recommendations
        from backend.services.workbench_intelligence import context_for
        evidence, _ = context_for(db, case_id)
        rec = next(r for r in recommendations(evidence) if r["rule"] == rule)  # must be evidence-backed
        path = {"approved": ["approved"], "simulated": ["approved", "simulated"], "rejected": ["rejected"]}[final]
        stamp = None
        for step in path:
            stamp = audit(f"response_{step}", f"{rec['title']}: {note or 'Analyst reviewed supporting evidence.'} "
                                              "Simulation only; no system command executed.")
        db.add(ResponseAction(id=f"{case_id}:{rule}", case_id=case_id, rule=rule, status=final,
                              decision_note=note, decided_by=ANALYST, decided_at=stamp))
        db.flush()

    target = STATES.index(status)
    add_notes("NEW")
    for i in range(1, target + 1):
        # Containment needs a simulated containment action; closure needs recovery.
        if STATES[i] == "CONTAINMENT" or (STATES[i] == "CLOSED"):
            for rule, final, note in actions:
                if (STATES[i] == "CONTAINMENT" and rule in {"isolate", "block", "identity", "hunt", "preserve"}) or \
                   (STATES[i] == "CLOSED" and rule not in {"isolate", "block", "identity", "hunt", "preserve"}):
                    if not db.get(ResponseAction, f"{case_id}:{rule}"):
                        decide(rule, final, note)
        audit("case_updated", f"status: {STATES[i-1]} → {STATES[i]}")
        add_notes(STATES[i])
    for rule, final, note in actions:
        if not db.get(ResponseAction, f"{case_id}:{rule}"):
            decide(rule, final, note)
    case.status = status
    case.version = 1 + clock[0] // 7
    case.updated_at = _ts(case.created_at, clock[0])
    db.flush()


# Preset workflow positions. Response states differ on purpose.
CASE_STATES = {
    "INC-1047": lambda db: _apply_state(db, "INC-1047", "INVESTIGATING", "medium",
        actions=[("preserve", "simulated", "Gateway logs exported before any change."),
                 ("hunt", "approved", "Scope other remote-access services for the same source; awaiting simulation.")],
        notes=[("hypothesis", "Source is a Tor exit relay: traffic may come from any Tor user. Treat as unattributed "
                              "password guessing until authentication logs show otherwise.", "INVESTIGATING")]),
    "INC-1048": lambda db: _apply_state(db, "INC-1048", "CONTAINMENT", "high",
        actions=[("preserve", "simulated", "Firewall, proxy and DNS records preserved."),
                 ("block", "simulated", "Three independent internal sources agree; block reviewed for dependencies."),
                 ("hunt", "approved", "Hunt other workstations for the domain; awaiting simulation.")],
        notes=[("conclusion", "Firewall, proxy and DNS observations are independent sensors and agree on one IP "
                              "and one domain. Reputation listing is supporting, not decisive.", "INVESTIGATING")]),
    "INC-1049": lambda db: _apply_state(db, "INC-1049", "TRIAGED", "low",
        notes=[("hypothesis", "Unverified forum claim. Notify the named organization's CERT contact only after "
                              "independent validation; no GOTHAMITE telemetry involves the domain.", "TRIAGED")]),
    "INC-1050": lambda db: _apply_state(db, "INC-1050", "NEW", "medium",
        actions=[("preserve", "approved", "Keep the three report listings as separate observations."),
                 ("block", "rejected", "Published listing only; no internal resolution or contact observed. "
                                       "Revisit if DNS telemetry shows a lookup.")]),
    "INC-1051": lambda db: _apply_state(db, "INC-1051", "INVESTIGATING", "high",
        actions=[("preserve", "approved", "Identity-provider logs retained."),
                 ("hunt", "rejected", "Sign-in failures came from one source; hunt deferred until identity review completes.")],
        notes=[("hypothesis", "Exposure claim is unverified. Failed sign-ins suggest testing of the listed account; "
                              "credential rotation awaits approval.", "INVESTIGATING")]),
    "INC-1052": lambda db: _apply_state(db, "INC-1052", "CLOSED", "low",
        actions=[("preserve", "simulated", "Quarantined messages and DNS records preserved."),
                 ("block", "simulated", "Lookalike domain blocked at resolver and mail gateway (simulated)."),
                 ("hunt", "simulated", "No other mailbox clicked the link in the exercise data."),
                 ("recover", "simulated", "Quarantine released only for unrelated messages.")],
        notes=[("recovery", "Resolver and mail-gateway blocks validated in the exercise; no user interaction recorded.", "RECOVERY"),
               ("lesson", "Register close lookalikes of the organization domain for monitoring.", "RECOVERY")]),
}


def seed_library(db: Session) -> None:
    """Idempotent: never resets analyst work on restart."""
    if db.get(IntelEntity, LIBRARY_SENTINEL) or not db.get(IntelEntity, "ORG-DEMO"):
        return

    def entity(id, kind, label, summary, attributes, confidence=0.8, source="Exercise intelligence", seen="2026-09-20T09:00:00Z"):
        db.add(IntelEntity(id=id, kind=kind, label=label, summary=summary, source=source, confidence=confidence,
                           first_seen=seen, last_seen=seen, attributes=attributes, provenance="synthetic"))

    def evidence(id, title, kind, content, entities, observed, confidence, source):
        db.add(IntelEvidence(id=id, title=title, kind=kind, content=content, source=source, observed_at=observed,
                             confidence=confidence, content_hash=hashlib.sha256(content.encode()).hexdigest(),
                             provenance="synthetic"))
        db.flush()
        for e in sorted(set(entities)):
            db.add(EvidenceEntity(evidence_id=id, entity_id=e))
        db.flush()

    def edge(a, rel, b, ev, confidence=0.8):
        db.add(IntelRelationship(id=f"{a}:{rel}:{b}", source_id=a, target_id=b, relation=rel,
                                 evidence_id=ev, confidence=confidence))

    def asset(id, host, criticality, owner, service, seen):
        entity(id, "asset", host, "Internal exercise asset with an accountable service owner.",
               {"business_criticality": criticality, "owner": owner, "service": service, "platform": "Linux"},
               0.9, "Synthetic CMDB", seen)

    # INC-1047 · IOC + Tor context -------------------------------------------------
    t = "2026-09-21T09:00:00Z"
    create_case(db, "INC-1047", "TOR exit-node infrastructure review",
                "Synthetic VPN telemetry names a source IP that the bundled Tor Project snapshot lists as an exit relay. "
                "Tor association is context, not a verdict.", "synthetic", t, _ts(t, 50))
    asset("AST-L47", "VPN-GW-05", "high", "Network operations", "Remote-access VPN", t)
    entity("IP-L47", "ip", TOR_CASE_IP, "Source address in synthetic VPN telemetry. Real public address; the log naming it is fictional.",
           {"reputation": "unknown", "network": "Public IPv4", "sightings": 38}, 0.7, "Synthetic VPN gateway log", _ts(t, 12))
    db.flush()
    evidence("EV-L47-NETWORK", "Repeated VPN authentication failures", "network",
             f"EXERCISE VPN log: VPN-GW-05 rejected 38 sign-in attempts from {TOR_CASE_IP} in 20 minutes across 11 usernames. "
             "No successful authentication was recorded.", ["INC-1047", "AST-L47", "IP-L47"], _ts(t, 12), 0.85,
             "Synthetic VPN gateway log")
    edge("IP-L47", "OBSERVED_ON", "AST-L47", "EV-L47-NETWORK", 0.85)
    evidence("EV-L47-CONTEXT", "Remote-access gateway inventory", "context",
             "EXERCISE CMDB: VPN-GW-05 terminates remote access for Meridian Research staff; owned by Network operations.",
             ["INC-1047", "AST-L47", "ORG-DEMO"], _ts(t, 5), 0.9, "Synthetic CMDB")
    edge("INC-1047", "AFFECTS", "AST-L47", "EV-L47-CONTEXT", 0.9)
    edge("AST-L47", "BELONGS_TO", "ORG-DEMO", "EV-L47-CONTEXT", 0.9)

    # INC-1048 · one IOC, several independent sources -------------------------------
    t = "2026-09-17T14:00:00Z"
    create_case(db, "INC-1048", "Multi-source corroboration: 198.51.100.23",
                "Three independent synthetic sensors and one exercise reputation feed observe the same IP and domain. "
                "Each observation is kept separately.", "synthetic", t, _ts(t, 60))
    asset("AST-L48", "HR-WS-14", "medium", "People operations", "HR workstation", t)
    entity("IP-L48", "ip", "198.51.100.23", "Documentation-range IP (TEST-NET-2) in the corroboration exercise.",
           {"reputation": "malicious", "network": "TEST-NET-2", "asn": "AS64501 (documentation)", "sightings": 4}, 0.85,
           "Synthetic network sensors", _ts(t, 10))
    entity("DOM-L48", "domain", "cdn-sync-mirror.example", "Reserved .example domain in the corroboration exercise.",
           {"registration": "Synthetic registration fixture", "reputation": "suspicious"}, 0.8, "Synthetic DNS resolver", _ts(t, 9))
    db.flush()
    evidence("EV-L48-DNS", "DNS resolution: cdn-sync-mirror.example", "dns",
             "EXERCISE resolver: HR-WS-14 resolved cdn-sync-mirror.example to 198.51.100.23.",
             ["INC-1048", "DOM-L48", "IP-L48", "AST-L48"], _ts(t, 9), 0.9, "Synthetic DNS resolver")
    edge("DOM-L48", "RESOLVES_TO", "IP-L48", "EV-L48-DNS", 0.9)
    evidence("EV-L48-FIREWALL", "Outbound TLS session to 198.51.100.23", "network",
             "EXERCISE firewall: HR-WS-14 opened 6 outbound TLS sessions to 198.51.100.23:443 over 40 minutes.",
             ["INC-1048", "IP-L48", "AST-L48"], _ts(t, 10), 0.9, "Synthetic perimeter firewall")
    edge("IP-L48", "OBSERVED_ON", "AST-L48", "EV-L48-FIREWALL", 0.9)
    evidence("EV-L48-PROXY", "Web proxy request to cdn-sync-mirror.example", "network",
             "EXERCISE proxy: HR-WS-14 requested https://cdn-sync-mirror.example/sync (text only, never fetched); category uncategorized.",
             ["INC-1048", "DOM-L48", "AST-L48"], _ts(t, 11), 0.85, "Synthetic web proxy")
    edge("DOM-L48", "OBSERVED_ON", "AST-L48", "EV-L48-PROXY", 0.85)
    evidence("EV-L48-REPUTATION", "Exercise feed lists 198.51.100.23", "reputation",
             "EXERCISE feed marks 198.51.100.23 as malicious. No external reputation service was queried.",
             ["INC-1048", "IP-L48"], _ts(t, 20), 0.7, "Synthetic reputation feed")
    evidence("EV-L48-CONTEXT", "Workstation inventory", "context",
             "EXERCISE CMDB: HR-WS-14 is a People-operations workstation; business criticality medium.",
             ["INC-1048", "AST-L48", "ORG-DEMO"], _ts(t, 2), 0.9, "Synthetic CMDB")
    edge("INC-1048", "AFFECTS", "AST-L48", "EV-L48-CONTEXT", 0.9)
    edge("AST-L48", "BELONGS_TO", "ORG-DEMO", "EV-L48-CONTEXT", 0.9)

    # INC-1051 · credential exposure (placeholders only) -----------------------------
    t = "2026-09-24T07:30:00Z"
    create_case(db, "INC-1051", "Synthetic credential exposure: payroll service account",
                "A fictional paste lists a service account. No credential value is stored anywhere in GOTHAMITE.",
                "synthetic", t, _ts(t, 45))
    asset("AST-L51", "SSO-IDP-06", "critical", "Identity team", "Single sign-on identity provider", t)
    entity("EMAIL-L51", "email", "svc-payroll@meridian.example", "Fictional service identity; no password is stored.",
           {"organization": "Meridian Research", "account_type": "Service account"}, 0.8, "Synthetic exposure bulletin", _ts(t, 3))
    entity("DW-L51", "darkweb_mention", "Synthetic paste / payroll service account",
           "Synthetic exposure bulletin. Source claims require independent validation.",
           {"category": "Credential exposure", "source_type": "Synthetic paste site", "verification": "Unverified source claim",
            "excerpt": "EXERCISE ONLY: svc-payroll@meridian.example : [placeholder]"}, 0.55, "Synthetic exposure bulletin", _ts(t, 3))
    entity("IP-L51", "ip", "198.51.100.77", "Documentation-range IP (TEST-NET-2) seen in failed sign-ins.",
           {"reputation": "unknown", "network": "TEST-NET-2"}, 0.6, "Synthetic identity provider", _ts(t, 20))
    db.flush()
    evidence("EV-L51-EXPOSURE", "Service account named in a paste", "credential_exposure",
             "EXERCISE bulletin: a paste lists svc-payroll@meridian.example with a password field. GOTHAMITE records only "
             "the placeholder [placeholder]; no credential value exists in this exercise.",
             ["INC-1051", "DW-L51", "EMAIL-L51"], _ts(t, 3), 0.55, "Synthetic exposure bulletin")
    edge("DW-L51", "MENTIONS", "EMAIL-L51", "EV-L51-EXPOSURE", 0.55)
    evidence("EV-L51-SIGNIN", "Failed sign-ins for the listed account", "network",
             "EXERCISE identity provider: 3 failed sign-ins for svc-payroll from 198.51.100.77 within 4 minutes; "
             "no successful sign-in and no MFA prompt approved.", ["INC-1051", "EMAIL-L51", "IP-L51", "AST-L51"],
             _ts(t, 20), 0.8, "Synthetic identity provider")
    edge("IP-L51", "OBSERVED_ON", "AST-L51", "EV-L51-SIGNIN", 0.8)
    evidence("EV-L51-CONTEXT", "Identity provider inventory", "context",
             "EXERCISE CMDB: SSO-IDP-06 authenticates Meridian Research staff and service accounts; business criticality critical.",
             ["INC-1051", "AST-L51", "EMAIL-L51", "ORG-DEMO"], _ts(t, 1), 0.9, "Synthetic CMDB")
    edge("EMAIL-L51", "BELONGS_TO", "ORG-DEMO", "EV-L51-CONTEXT", 0.9)
    edge("INC-1051", "AFFECTS", "AST-L51", "EV-L51-CONTEXT", 0.9)

    # INC-1052 · suspicious domain + DNS ---------------------------------------------
    t = "2026-09-12T10:00:00Z"
    create_case(db, "INC-1052", "Lookalike domain: meridian-payroll-verify.example",
                "Synthetic mail and DNS telemetry show a lookalike domain used in quarantined messages.",
                "synthetic", t, _ts(t, 90))
    asset("AST-L52", "MAIL-GW-02", "high", "Messaging team", "Inbound mail gateway", t)
    entity("DOM-L52", "domain", "meridian-payroll-verify.example", "Reserved .example lookalike of the fictional meridian.example.",
           {"registration": "Synthetic registration fixture: created 2 days before first message", "reputation": "malicious"},
           0.8, "Synthetic DNS resolver", _ts(t, 4))
    entity("IP-L52", "ip", "198.51.100.140", "Documentation-range IP (TEST-NET-2) hosting the lookalike domain.",
           {"reputation": "suspicious", "network": "TEST-NET-2"}, 0.7, "Synthetic DNS resolver", _ts(t, 4))
    db.flush()
    evidence("EV-L52-DNS", "DNS resolution: meridian-payroll-verify.example", "dns",
             "EXERCISE resolver: meridian-payroll-verify.example resolved to 198.51.100.140 (A record, TTL 300).",
             ["INC-1052", "DOM-L52", "IP-L52"], _ts(t, 4), 0.9, "Synthetic DNS resolver")
    edge("DOM-L52", "RESOLVES_TO", "IP-L52", "EV-L52-DNS", 0.9)
    evidence("EV-L52-MAIL", "Quarantined messages link to the lookalike", "network",
             "EXERCISE mail gateway: 12 inbound messages linking to meridian-payroll-verify.example were quarantined; no click recorded.",
             ["INC-1052", "DOM-L52", "AST-L52"], _ts(t, 6), 0.9, "Synthetic mail gateway")
    edge("DOM-L52", "OBSERVED_ON", "AST-L52", "EV-L52-MAIL", 0.9)
    evidence("EV-L52-REPUTATION", "Exercise feed lists the lookalike domain", "reputation",
             "EXERCISE feed marks meridian-payroll-verify.example as phishing infrastructure. No external service was queried.",
             ["INC-1052", "DOM-L52"], _ts(t, 15), 0.75, "Synthetic reputation feed")
    evidence("EV-L52-CONTEXT", "Mail gateway inventory", "context",
             "EXERCISE CMDB: MAIL-GW-02 filters inbound mail for Meridian Research; owned by the Messaging team.",
             ["INC-1052", "AST-L52", "ORG-DEMO"], _ts(t, 1), 0.9, "Synthetic CMDB")
    edge("INC-1052", "AFFECTS", "AST-L52", "EV-L52-CONTEXT", 0.9)
    edge("AST-L52", "BELONGS_TO", "ORG-DEMO", "EV-L52-CONTEXT", 0.9)
    db.flush()

    for case in ("INC-1047", "INC-1048", "INC-1051", "INC-1052"):
        CASE_STATES[case](db)
    db.commit()
