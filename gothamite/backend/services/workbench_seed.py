"""Reproducible fictional exercises. No external lookups or live intelligence."""
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from backend.models.workbench import IntelEntity, IntelEvidence, EvidenceEntity, IntelRelationship, IncidentCase

SNAPSHOT = "2026-09-28T10:00:00Z"
SCENARIOS = [
    ("Glass Harbor", "Grey Moth", "SableLoader", "Finance gateway beaconing", "critical", "INVESTIGATING"),
    ("Cedar Exchange", "Hollow Cedar", "ReedStealer", "Exposed service account", "high", "TRIAGED"),
    ("Paper Lantern", "Pale Harbor", "LanternDrop", "Suspicious application staging", "medium", "NEW"),
    ("Quiet Current", "Quiet Finch", "FinchProbe", "Unverified perimeter scanning", "low", "NEW"),
]


def seed_workbench(db: Session) -> None:
    # Versioned sentinel: never reset analyst work on restart.
    if db.get(IntelEntity, "ORG-DEMO"):
        return
    base = datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc)

    def stamp(minutes: int) -> str:
        return (base + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")

    def entity(id, kind, label, summary, attributes=None, confidence=.85, source="Exercise intelligence"):
        item = IntelEntity(id=id, kind=kind, label=label, summary=summary, source=source,
                           confidence=confidence, first_seen=stamp(0), last_seen=stamp(100),
                           attributes=attributes or {}, provenance="synthetic")
        db.add(item)
        return item

    def evidence(id, title, kind, content, entities, minute=42, confidence=.9, source="Synthetic EDR"):
        db.add(IntelEvidence(id=id, title=title, kind=kind, content=content, source=source,
                            observed_at=stamp(minute), confidence=confidence,
                            content_hash=hashlib.sha256(content.encode()).hexdigest(), provenance="synthetic"))
        db.flush()
        for eid in set(entities):
            db.add(EvidenceEntity(evidence_id=id, entity_id=eid))
        db.flush()

    def edge(a, relation, b, ev, confidence=.85):
        db.add(IntelRelationship(id=f"{a}:{relation}:{b}", source_id=a, target_id=b,
                                relation=relation, evidence_id=ev, confidence=confidence))

    entity("ORG-DEMO", "organization", "Meridian Research", "Fictional organization used throughout the exercise.",
           {"sector": "Research & financial services", "environment": "Synthetic exercise v1"})
    for s, (campaign, actor, malware, title, severity, state) in enumerate(SCENARIOS):
        n = s + 1
        case = f"INC-{1042+s}"
        camp, act, mal = f"CAM-{n:03}", f"ACT-{n:03}", f"MAL-{n:03}"
        asset, secondary = f"AST-{n:03}", f"AST-{n+4:03}"
        first = s * 30
        ip, dom, sha = f"IP-{first+1:03}", f"DOM-{first+1:03}", f"HASH-{n:03}"
        host = ["FIN-GW-01", "IDENTITY-02", "APP-STAGING-03", "EDGE-PROXY-04"][s]
        domain = f"{campaign.lower().replace(' ', '-')}-sync.example"
        digest = hashlib.sha256(f"gothamite-fictional-{malware}".encode()).hexdigest()
        entity(case, "incident", title, f"{campaign}: an evidence-backed synthetic investigation. No real systems are affected.", {"campaign": campaign})
        entity(camp, "campaign", campaign, f"Fictional {['loader deployment', 'credential exposure', 'staging', 'reconnaissance'][s]} exercise.", {"sector": "Research", "attribution": "Scenario association; not real-world attribution"})
        entity(act, "threat_actor", actor, "Fictional activity cluster. Infrastructure association does not prove identity.", {"aliases": f"{actor.replace(' ', '').lower()}, cluster-{n}", "targeting": "Fictional Meridian Research", "TTPs": "Infrastructure reuse; credential access"}, .7)
        entity(mal, "malware", malware, "Inert fictional sample label; no executable malware is provided.", {"family": malware, "behavior": "Synthetic loader / staged execution"})
        entity(asset, "asset", host, "Internal exercise asset with an accountable service owner.", {"business_criticality": "critical" if s == 0 else "high" if s == 1 else "medium", "owner": "Finance operations" if s == 0 else "Platform team", "address": f"10.24.{n}.12", "platform": "Windows Server" if s == 0 else "Linux", "service": "Payment settlement" if s == 0 else "Identity / application services"})
        entity(secondary, "asset", ["FIN-WS-07", "SSO-NODE-02", "BUILD-AGENT-03", "SENSOR-04"][s], "Related asset requiring a scoped indicator hunt.", {"business_criticality": "medium", "owner": "Platform team", "platform": "Linux", "service": "Supporting infrastructure"})
        entity(sha, "hash", digest, f"SHA-256 identifier for the inert {malware} exercise artifact.", {"algorithm": "SHA-256", "file_name": f"{malware.lower()}.sample.txt", "family": malware})
        entity(f"URL-{n:03}", "url", f"https://{domain}/update", "Synthetic staging URL; displayed as text, never fetched.", {"scheme": "https"})
        entity(f"EMAIL-{n:03}", "email", f"svc-{n}@meridian.example", "Fictional service identity; no passwords or credentials are stored.", {"organization": "Meridian Research"})
        entity(f"VULN-{n:03}", "vulnerability", f"SYN-VULN-2026-{n:04}", "Synthetic vulnerability exercise record, not a real CVE.", {"affected_service": host, "remediation": "Validate configuration and apply vendor-supported updates", "exploitability": "Unverified"}, .55)
        entity(f"DW-{n:03}", "darkweb_mention", f"Meridian mention / {campaign}", "Synthetic exposure bulletin. Source claims require independent validation.", {"category": "Credential exposure" if s < 2 else "Organization mention", "excerpt": f"EXERCISE ONLY: a fictional post references {domain} and Meridian Research. No leaked data is included.", "source_type": "Synthetic dark-web bulletin", "verification": "Unverified source claim"}, .6, "Synthetic exposure bulletin")
        for i in range(first, first + 30):
            iid, did = f"IP-{i+1:03}", f"DOM-{i+1:03}"
            d = domain if i == first else f"relay-{i-first:02}.{domain}"
            entity(iid, "ip", f"203.0.113.{42+i}", f"Documentation-only IP in the {campaign} exercise infrastructure.", {"asn": "AS64500 (documentation)", "geolocation": "Not applicable — reserved documentation range", "reputation": "malicious" if s == 0 else "suspicious" if s < 3 else "unknown", "campaign": campaign, "sightings": 14 if s == 0 else 3, "network": "TEST-NET-3"}, .92 if s == 0 else .65, "Synthetic DNS / network sensor")
            entity(did, "domain", d, f"Reserved .example domain linked to {campaign}.", {"registration": "Synthetic registration fixture", "registrar": "Not registered — reserved .example", "reputation": "malicious" if s == 0 else "suspicious", "campaign": campaign}, .88 if s == 0 else .65)
            db.flush()
            evid = f"OBS-DNS-{i+1:03}"
            evidence(evid, f"DNS resolution: {d}", "dns", f"EXERCISE DNS: {d} resolves to 203.0.113.{42+i}. This is a generated observation, not a network lookup.", [iid, did, camp] + ([case] if i == first else []), minute=35 + i % 60, source="Synthetic DNS")
            edge(did, "RESOLVES_TO", iid, evid)
            edge(camp, "USES", did, evid, .75)
        db.flush()
        context = f"EV-{n}-CONTEXT"
        evidence(context, "Campaign context and asset inventory", "context", f"EXERCISE: {actor} is the fictional cluster assigned to {campaign}; {malware} is its sample label. {host} is owned by the named service team. These associations are scenario context, not proof of actor identity.", [case, camp, act, mal, sha, asset, secondary, "ORG-DEMO", f"VULN-{n:03}"], 38, .7, "Synthetic intelligence / CMDB")
        for a, rel, b in [(act,"ASSOCIATED_WITH",camp),(camp,"USES",mal),(mal,"HAS_SAMPLE",sha),(sha,"CONTACTS",dom),(case,"INVESTIGATES",camp),(case,"AFFECTS",asset),(asset,"CONNECTED_TO",secondary),(asset,"BELONGS_TO","ORG-DEMO"),(f"VULN-{n:03}","AFFECTS",asset),(f"URL-{n:03}","HOSTED_ON",dom)]:
            edge(a, rel, b, context, .7)
        network = f"EV-{n}-NETWORK"
        evidence(network, "Repeated outbound connections" if s == 0 else "Network observation", "network", f"EXERCISE sensor: {host} connected to 203.0.113.{42+first} via {domain}. {'14 connections at 60-second intervals; review potential beaconing.' if s == 0 else 'Limited observations; malicious intent is unconfirmed.'}", [case, asset, ip, dom, f"URL-{n:03}"], 42+s*5, .94 if s == 0 else .65, "Synthetic network sensor")
        edge(ip, "OBSERVED_ON", asset, network)
        if s == 0:
            evidence(f"EV-{n}-MALWARE", "Sample hash matched on finance gateway", "malware_detection", f"EXERCISE EDR: {digest} observed on {host}; the exercise catalog associates this hash with {malware}. A hash match alone does not prove execution or data loss.", [case, asset, mal, sha], 51, .96)
            edge(sha, "OBSERVED_ON", asset, f"EV-{n}-MALWARE", .96)
            evidence(f"EV-{n}-REPUTATION", "Infrastructure flagged by exercise feed", "reputation", f"EXERCISE feed marks {domain} and 203.0.113.42 as malicious based on the synthetic campaign fixture. No external reputation service was queried.", [case, ip, dom], 44, .9, "Synthetic reputation feed")
        if s < 2:
            evidence(f"EV-{n}-EXPOSURE", "Unverified service identity exposure", "credential_exposure", f"EXERCISE bulletin references svc-{n}@meridian.example alongside {domain}. This is a source claim; credential validity and account compromise are not established.", [case, f"DW-{n:03}", f"EMAIL-{n:03}", dom], 56+s*5, .6, "Synthetic exposure bulletin")
            edge(f"DW-{n:03}", "MENTIONS", f"EMAIL-{n:03}", f"EV-{n}-EXPOSURE", .6)
            edge(f"DW-{n:03}", "ASSOCIATED_WITH", camp, f"EV-{n}-EXPOSURE", .6)
        else:
            evidence(f"EV-{n}-MENTION", "Unverified organization reference", "mention", f"EXERCISE source mentions {domain}; no corroborating compromise evidence.", [case, f"DW-{n:03}", dom], 70+s, .4, "Synthetic exposure bulletin")
            edge(f"DW-{n:03}", "MENTIONS", dom, f"EV-{n}-MENTION", .4)
        db.flush()
        db.add(IncidentCase(id=case, status=state, severity=severity, analyst="Demo analyst", created_at=stamp(60+s*5), updated_at=stamp(72+s*5), version=1))
    db.commit()
