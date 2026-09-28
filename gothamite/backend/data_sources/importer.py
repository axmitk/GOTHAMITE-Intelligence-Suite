"""Import bundled dataset snapshots into the existing workbench model.

Dataset records become first-class GOTHAMITE entities, evidence and
relationships (no second data model). Every row gets ``provenance`` =
``dataset_derived`` or ``reference_derived`` and a ``DatasetRecord`` with full
provenance. Import is idempotent: deterministic ids mean a record imported twice
never creates duplicate evidence.

Correlation rules (deterministic, evidence-backed only):
- Infoblox: indicator --OBSERVED_IN--> report, supported by that report's row.
- DarkForums: thread --MENTIONS--> domain / country, supported by the thread record.
- Tor Onionoo: IP --ASSOCIATED_WITH--> Tor relay, supported by the relay's
  directory record. Rule ``tor-exact-ip-v1``: an IP already known to GOTHAMITE
  (from any source) is matched only on the exact normalized IPv4 value; the Tor
  observation is attached to that entity and to any case already investigating
  it. No ASN, hostname or address-range similarity is used.
- Entity ids are derived from the normalized value, so the same domain from two
  datasets resolves to one entity with separate supporting observations.
No edge is created from text similarity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from backend.data_sources.transform import TRANSFORMATION_VERSION, excerpt, normalize_ipv4, safety_reasons
from backend.models.workbench import (
    DatasetRecord, EvidenceEntity, IncidentCase, IntelEntity, IntelEvidence, IntelRelationship)

DATA = Path(__file__).resolve().parent
IMPORTED_AT = "2026-09-28T12:00:00Z"  # fixed so the demo stays deterministic
# Relation confidence annotations (documented in DATA_SOURCES.md). These describe
# how directly the record supports the relationship; they are not reputation scores.
CONF_PUBLISHED_LIST = 0.9   # indicator appears in a publisher's IOC list
CONF_FORUM_CLAIM = 0.6      # entity named in an unverified forum claim
CONF_RECONSTRUCTION = 0.3   # reference-derived reconstruction, not a real record
CONF_TOR_DIRECTORY = 0.95   # relay listed in the Tor Project's own directory data
TOR_RULE = "tor-exact-ip-v1"
DATASET_CASE = "INC-1046"
FORUM_CASE, FORUM_THREAD = "INC-1049", "1289"
IOC_CASE, IOC_CASE_VALUE = "INC-1050", "ads-tm-glb.click"
MALICIOUS_CLASSIFICATIONS = {"malicious", "malware"}
_CASE_REPORTS = {"c2_beacon_20230414_iocs.csv", "decoy_dog_cta_20230420_iocs.csv",
                 "decoy_dog_cta_20230714_iocs.csv"}


def _h(value: str, n: int = 10) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:n]


def entity_id(kind: str, value: str) -> str:
    """Stable id from the normalized value: the cross-source correlation key."""
    return f"DS-{kind.upper()}-{_h(kind + '|' + value.strip().lower())}"


def load_manifest() -> dict:
    return json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))


class _Writer:
    def __init__(self, db: Session, manifest: dict) -> None:
        self.db, self.m = db, manifest
        self.stats = {"entities": 0, "evidence": 0, "relationships": 0, "suppressed": 0, "skipped_existing": 0}

    def _prov(self, rtype, rid, key, source_record_id, details=None):
        d = self.m["datasets"][key]
        if self.db.get(DatasetRecord, (rtype, rid)):
            return
        self.db.add(DatasetRecord(
            record_type=rtype, record_id=rid, provenance_class=d["provenance_class"], dataset=key,
            dataset_name=d["name"], dataset_version=d["dataset_version"], license=d["license"],
            source_url=d["source_url"], doi=d.get("doi"), source_record_id=source_record_id,
            transformation_version=d.get("transformation_version") or self.m.get("transformation_version", TRANSFORMATION_VERSION),
            imported_at=IMPORTED_AT, details=details or {}))

    def entity(self, key, kind, value, label, summary, source, confidence, seen, attrs, src_rec):
        eid = entity_id(kind, value)
        row = self.db.get(IntelEntity, eid)
        if row is None:
            pclass = self.m["datasets"][key]["provenance_class"]
            self.db.add(IntelEntity(id=eid, kind=kind, label=label[:512], summary=summary, source=source[:80],
                                    confidence=confidence, first_seen=seen, last_seen=seen,
                                    attributes=attrs, provenance=pclass))
            self.stats["entities"] += 1
        else:
            # Same entity from another record/dataset: widen the observed window only.
            row.first_seen, row.last_seen = min(row.first_seen, seen), max(row.last_seen, seen)
        self.db.flush()
        self._prov("entity", eid, key, src_rec)
        return eid

    def evidence(self, key, eid, title, kind, content, source, observed_at, confidence, entities, src_rec, details,
                 free_text=None):
        if self.db.get(IntelEvidence, eid):
            self.stats["skipped_existing"] += 1
            return eid
        # Runtime second pass over dataset free text. Constructed indicator
        # descriptions are not free text and were validated during preparation.
        reasons = safety_reasons(free_text) if free_text else []
        if reasons:
            content = f"Content suppressed by safety filter ({', '.join(reasons)})."
            self.stats["suppressed"] += 1
        self.db.add(IntelEvidence(id=eid, title=title[:240], kind=kind, content=content, source=source[:80],
                                  observed_at=observed_at, confidence=confidence,
                                  content_hash=hashlib.sha256(content.encode()).hexdigest(),
                                  provenance=self.m["datasets"][key]["provenance_class"]))
        self.db.flush()
        for ent in sorted(set(entities)):
            self.db.add(EvidenceEntity(evidence_id=eid, entity_id=ent))
        self.db.flush()
        self._prov("evidence", eid, key, src_rec, details)
        self.stats["evidence"] += 1
        return eid

    def relation(self, key, src, rel, tgt, evidence_id, confidence, src_rec):
        rid = f"{src}:{rel}:{tgt}:{evidence_id}"[:160]
        if self.db.get(IntelRelationship, rid):
            return
        self.db.add(IntelRelationship(id=rid, source_id=src, target_id=tgt, relation=rel,
                                      evidence_id=evidence_id, confidence=confidence))
        self.db.flush()
        self._prov("relationship", rid, key, src_rec)
        self.stats["relationships"] += 1


def _report_label(stem: str) -> str:
    base = stem.replace("_iocs", "").replace(".csv", "")
    parts = base.rsplit("_", 1)
    name = parts[0].replace("_cta", "").replace("_", " ").title()
    date = parts[1] if len(parts) == 2 and parts[1].isdigit() else ""
    return f"Infoblox report: {name}" + (f" ({date[:4]}-{date[4:6]}-{date[6:]})" if len(date) == 8 else "")


def _report_date(stem: str) -> str | None:
    tail = stem.replace(".csv", "").split("_")[-1]
    return f"{tail[:4]}-{tail[4:6]}-{tail[6:]}T00:00:00Z" if len(tail) == 8 and tail.isdigit() else None


def import_infoblox(w: _Writer) -> None:
    key = "infoblox_threat_intelligence"
    data = json.loads((DATA / "infoblox" / "ioc_snapshot.json").read_text(encoding="utf-8"))
    linked_reports: set[str] = set()
    for r in data["indicators"]:
        report, value, kind = r["report"], r["indicator"], r["type"]
        if r.get("detected_date"):
            observed, basis = f"{r['detected_date']}T00:00:00Z", "detected_date in source"
        else:
            observed, basis = _report_date(report) or IMPORTED_AT, "report date from filename (detected_date missing)"
        rep_id = w.entity(key, "report", report, _report_label(report),
                          "Published Infoblox indicator list. A report is a source, not an actor attribution.",
                          "Infoblox Threat Intelligence", CONF_PUBLISHED_LIST, _report_date(report) or observed,
                          {"report_file": report, "publisher": "Infoblox"}, report)
        ioc_id = w.entity(key, kind, value, value,
                          f"Indicator listed in published Infoblox threat-intelligence reports (classification as published: {r['classification']}).",
                          "Infoblox Threat Intelligence", CONF_PUBLISHED_LIST, observed,
                          {"classification": r["classification"], "classification_source": "Infoblox"}, f"{report}:{value}")
        ev = f"EV-IB-{_h(report + '|' + value, 12)}"
        # Explicit mapping (DATA_SOURCES.md): only publisher labels that assert
        # maliciousness become a reputation observation, scored by the existing
        # rule. Every other label stays an unscored classification observation.
        ev_kind = "reputation" if r["classification"] in MALICIOUS_CLASSIFICATIONS else "classification"
        w.evidence(key, ev, f"Listed by Infoblox: {value}", ev_kind,
                   f"DATASET: {value} ({kind}) appears in {report} with classification '{r['classification']}'. "
                   "Listing in a published indicator set; GOTHAMITE has no internal telemetry for it.",
                   "Infoblox Threat Intelligence", observed, CONF_PUBLISHED_LIST,
                   [ioc_id, rep_id] + ([DATASET_CASE] if report in _CASE_REPORTS else []), f"{report}:{value}",
                   {"classification": r["classification"], "report": report, "observed_at_basis": basis})
        w.relation(key, ioc_id, "OBSERVED_IN", rep_id, ev, CONF_PUBLISHED_LIST, f"{report}:{value}")
        if report in _CASE_REPORTS and report not in linked_reports:
            linked_reports.add(report)
            w.relation(key, DATASET_CASE, "INVESTIGATES", rep_id, ev, CONF_PUBLISHED_LIST, report)


def import_darkforums(w: _Writer) -> None:
    key = "darkforums_safe_corpus"
    pub = "2026-08-18T00:00:00Z"
    data = json.loads((DATA / "darkforums" / "forum_snapshot.json").read_text(encoding="utf-8"))
    for t in data["threads"]:
        tid = t["thread_id"]
        observed = t["date_posted"] or pub
        basis = "date_posted in source" if t["date_posted"] else "dataset publication date (post date not recorded in source)"
        title, reasons = excerpt(t["title"], 160)
        title = title or "Thread title withheld by safety filter"
        th = w.entity(key, "forum_thread", tid, title,
                      f"Dataset-derived forum thread ({t['forum_name']} / {t['category']}). Claims in it are unverified.",
                      "DarkForums Safe Corpus", CONF_FORUM_CLAIM, observed,
                      {"thread_id": tid, "forum": t["forum_name"], "category": t["category"],
                       "posts": len(t["posts"]), "date_basis": basis}, f"thread:{tid}")
        mentioned = []
        for d in t["entities"]["domain"]:
            mentioned.append(w.entity(key, "domain", d, d,
                                      "Domain named in a dataset-derived forum leak claim (unverified).",
                                      "DarkForums Safe Corpus", CONF_FORUM_CLAIM, observed,
                                      {"role": "organization domain named in claim"}, f"thread:{tid}:domain:{d}"))
        for c in t["entities"]["country"]:
            mentioned.append(w.entity(key, "country", c, c, "Country named in dataset-derived forum threads.",
                                      "DarkForums Safe Corpus", CONF_FORUM_CLAIM, observed, {}, f"thread:{tid}:country:{c}"))
        ev = f"EV-DF-T{tid}"
        w.evidence(key, ev, f"Forum thread: {title}"[:240], "mention",
                   f"DATASET: thread {tid} in {t['forum_name']} ({t['category']}): \"{title}\". "
                   "Unverified claim from a PII-redacted research corpus.",
                   "DarkForums Safe Corpus", observed, CONF_FORUM_CLAIM, [th] + mentioned, f"thread:{tid}",
                   {"thread_id": tid, "observed_at_basis": basis, "entities": t["entities"]}, free_text=title)
        for m in mentioned:
            w.relation(key, th, "MENTIONS", m, ev, CONF_FORUM_CLAIM, f"thread:{tid}")
        for p in t["posts"]:
            pev = f"EV-DF-P{p['post_id']}"
            text = p["excerpt"] if not p["suppressed"] else \
                f"Post content withheld by safety filter ({', '.join(p['suppression_reasons'])})."
            if p["suppressed"] and not w.db.get(IntelEvidence, pev):
                w.stats["suppressed"] += 1
            w.evidence(key, pev, f"Forum post {p['post_number']} in thread {tid}"[:240], "mention",
                       f"DATASET: {text}", "DarkForums Safe Corpus", p["post_date"] or observed, CONF_FORUM_CLAIM,
                       [th], f"thread:{tid}:post:{p['post_id']}",
                       {"thread_id": tid, "post_id": p["post_id"], "suppressed": p["suppressed"],
                        "original_content_sha256": p["content_sha256"],
                        "observed_at_basis": "post_date in source" if p["post_date"] else basis},
                       free_text=p["excerpt"])


def import_tor(w: _Writer) -> None:
    """Tor exit-node intelligence from the bundled Onionoo snapshot (no network)."""
    key = "tor_project_onionoo"
    path = DATA / "tor" / "onionoo_snapshot.json"
    if key not in w.m["datasets"] or not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    snapshot = data.get("relays_published") or "unknown"
    for r in data["relays"]:
        fpr, exit_ = r["fingerprint"], bool(r["exit"])
        seen = r.get("last_seen") or IMPORTED_AT
        role = "exit relay" if exit_ else "relay (no Exit flag)"
        relay = w.entity(key, "tor_relay", fpr, f"{r['nickname']} · {fpr[:8]}",
                         f"Tor {role} listed in the Tor Project Onionoo snapshot of {snapshot} UTC. "
                         "Infrastructure context; a Tor relay is not an attacker attribution.",
                         "Tor Project Onionoo", CONF_TOR_DIRECTORY, r.get("first_seen") or seen,
                         {"fingerprint": fpr, "nickname": r["nickname"], "exit": exit_, "running": r["running"],
                          "flags": ", ".join(r["flags"]), "as_name": r.get("as_name") or "Not published",
                          "snapshot": f"{snapshot} UTC"}, f"relay:{fpr}")
        relay_row = w.db.get(IntelEntity, relay)
        relay_row.last_seen = max(relay_row.last_seen, seen)
        for raw_ip in sorted(set(r["exit_addresses"]) | set(r["or_addresses"])):
            ip = normalize_ipv4(raw_ip)
            if not ip:
                continue
            # Exit relays exit from their listed exit addresses (or OR address when none is listed).
            is_exit_ip = exit_ and ip in (r["exit_addresses"] or r["or_addresses"])
            # tor-exact-ip-v1: reuse any IP entity GOTHAMITE already holds for this exact value.
            known = [e.id for e in w.db.query(IntelEntity).filter(IntelEntity.kind == "ip", IntelEntity.label == ip)
                     .order_by(IntelEntity.id).all()]
            ip_ids = known or [w.entity(key, "ip", ip, ip,
                                        "IP address listed for a Tor relay in the Tor Project Onionoo snapshot.",
                                        "Tor Project Onionoo", CONF_TOR_DIRECTORY, seen,
                                        {"tor_context": "Tor exit node" if is_exit_ip else "Tor relay (non-exit)"},
                                        f"relay:{fpr}:ip:{ip}")]
            # Cases that already cite this IP inherit the Tor observation.
            cited = w.db.query(EvidenceEntity.evidence_id).filter(EvidenceEntity.entity_id.in_(ip_ids))
            cases = sorted({x.entity_id for x in w.db.query(EvidenceEntity).join(
                IntelEntity, IntelEntity.id == EvidenceEntity.entity_id).filter(
                IntelEntity.kind == "incident", EvidenceEntity.evidence_id.in_(cited))})
            ev = f"EV-TOR-{fpr[:10]}-{_h(ip, 6)}"
            title = (f"TOR exit node: {ip} ({r['nickname']})" if is_exit_ip
                     else f"TOR relay (non-exit): {ip} ({r['nickname']})")
            w.evidence(key, ev, title, "tor_context" if is_exit_ip else "tor_relay",
                       f"DATASET: Tor Project Onionoo snapshot ({snapshot} UTC) lists relay {r['nickname']} "
                       f"({fpr}) at {ip}. Exit flag: {'yes' if exit_ else 'no'}. Running at snapshot: {'yes' if r['running'] else 'no'}. "
                       f"First seen {r.get('first_seen') or 'not published'}; last seen {r.get('last_seen') or 'not published'}; "
                       f"AS: {r.get('as_name') or 'not published'}. Tor infrastructure is context, not a malicious verdict.",
                       "Tor Project Onionoo", seen, CONF_TOR_DIRECTORY, ip_ids + [relay] + cases, f"relay:{fpr}:ip:{ip}",
                       {"observation_type": "tor_exit_node" if is_exit_ip else "tor_relay", "exit": exit_,
                        "running": r["running"], "fingerprint": fpr, "nickname": r["nickname"],
                        "first_seen": r.get("first_seen"), "last_seen": r.get("last_seen"), "as": r.get("as"),
                        "as_name": r.get("as_name"), "flags": r["flags"], "or_addresses": r["or_addresses"],
                        "observed_bandwidth": r.get("observed_bandwidth"), "snapshot": f"{snapshot} UTC",
                        "correlation_rule": TOR_RULE, "matched_existing_entities": known})
            for ip_id in ip_ids:
                w.relation(key, ip_id, "ASSOCIATED_WITH", relay, ev, CONF_TOR_DIRECTORY, f"relay:{fpr}:ip:{ip}")


def import_reconstruction(w: _Writer) -> None:
    key = "dwdata"
    data = json.loads((DATA / "dwdata" / "reconstruction.json").read_text(encoding="utf-8"))
    for item in data["listings"]:
        lid = w.entity(key, "market_listing", item["id"], item["title"],
                       "Reference-derived reconstruction following DWData's documented category taxonomy. Not a DWData record.",
                       "DWData reference (reconstruction)", CONF_RECONSTRUCTION, IMPORTED_AT,
                       {"vendor": item["vendor"], "category": item["category"], "price": item["price"],
                        "rating": item["rating"], "market": item["market"]}, item["id"])
        w.evidence(key, f"EV-RC-{item['id']}", f"Reconstructed listing: {item['category']}", "listing",
                   f"RECONSTRUCTION: {item['title']}. Vendor '{item['vendor']}' and price '{item['price']}' are illustrative placeholders, not observed values.",
                   "DWData reference (reconstruction)", IMPORTED_AT, CONF_RECONSTRUCTION, [lid], item["id"],
                   {"category": item["category"]})


def _dataset_case(w: _Writer) -> None:
    if w.db.get(IntelEntity, DATASET_CASE):
        return
    w.db.add(IntelEntity(id=DATASET_CASE, kind="incident", label="Decoy Dog DNS infrastructure review",
                         summary=("Dataset review case: domains Infoblox lists across three reports (C2 beacon, Decoy Dog April and July 2023). "
                                  "No internal telemetry links them to exercise assets."),
                         source="Analyst case", confidence=0.9, first_seen="2023-04-14T00:00:00Z",
                         last_seen="2023-07-14T00:00:00Z", attributes={"basis": "dataset-derived evidence"},
                         provenance="dataset_derived"))
    w.db.flush()
    w.db.add(IncidentCase(id=DATASET_CASE, status="NEW", severity="medium", analyst="Demo analyst",
                          created_at=IMPORTED_AT, updated_at=IMPORTED_AT, version=1))
    w.db.flush()


def _attach_case(w: _Writer, case: str, evidence_ids: list[str]) -> None:
    """Scope existing dataset observations to a case (no new observation is invented)."""
    for ev in evidence_ids:
        if w.db.get(IntelEvidence, ev) and not w.db.get(EvidenceEntity, (ev, case)):
            w.db.add(EvidenceEntity(evidence_id=ev, entity_id=case))
    w.db.flush()


def _library_dataset_cases(w: _Writer) -> None:
    """INC-1049 (forum claim) and INC-1050 (repeated Infoblox IOC): dataset-derived
    cases scoped to records imported above. Skipped when the record is absent."""
    from backend.services.workbench_library import CASE_STATES, create_case
    thread = entity_id("forum_thread", FORUM_THREAD)
    if w.db.get(IntelEntity, thread) and not w.db.get(IntelEntity, FORUM_CASE):
        create_case(w.db, FORUM_CASE, "Forum claim naming a government domain",
                    "Dataset review: a DarkForums Safe Corpus thread claims a leak naming a government domain. "
                    "The claim is unverified and no GOTHAMITE telemetry corroborates it.",
                    "dataset_derived", "2023-08-28T23:12:00Z", "2023-08-29T06:00:00Z")
        evs = [e.evidence_id for e in w.db.query(EvidenceEntity).filter_by(entity_id=thread).order_by(EvidenceEntity.evidence_id)]
        _attach_case(w, FORUM_CASE, evs)
        w.relation("darkforums_safe_corpus", FORUM_CASE, "INVESTIGATES", thread, f"EV-DF-T{FORUM_THREAD}",
                   CONF_FORUM_CLAIM, f"thread:{FORUM_THREAD}")
        CASE_STATES[FORUM_CASE](w.db)
    ioc = entity_id("domain", IOC_CASE_VALUE)
    if w.db.get(IntelEntity, ioc) and not w.db.get(IntelEntity, IOC_CASE):
        create_case(w.db, IOC_CASE, f"Repeated IOC review: {IOC_CASE_VALUE}",
                    f"Dataset review: Infoblox lists {IOC_CASE_VALUE} in three separate reports. Each listing stays its own "
                    "observation; no internal contact with the domain has been observed.",
                    "dataset_derived", "2023-04-14T00:00:00Z", "2023-07-14T00:00:00Z")
        evs = [e.id for e in w.db.query(IntelEvidence).join(EvidenceEntity).filter(EvidenceEntity.entity_id == ioc)
               .order_by(IntelEvidence.observed_at, IntelEvidence.id)]
        _attach_case(w, IOC_CASE, evs)
        w.relation("infoblox_threat_intelligence", IOC_CASE, "INVESTIGATES", ioc, evs[0], CONF_PUBLISHED_LIST, IOC_CASE_VALUE)
        CASE_STATES[IOC_CASE](w.db)


def import_datasets(db: Session) -> dict:
    """Idempotent import of all bundled snapshots. Returns per-run counts."""
    path = DATA / "manifest.json"
    if not path.exists():
        return {"skipped": "no manifest"}
    marker = "manifest-" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    if db.get(DatasetRecord, ("import", marker)):
        return {"skipped": "snapshot already imported"}  # fast restart path
    w = _Writer(db, load_manifest())
    _dataset_case(w)
    import_infoblox(w)
    import_darkforums(w)
    import_reconstruction(w)
    import_tor(w)
    _library_dataset_cases(w)
    db.add(DatasetRecord(record_type="import", record_id=marker, provenance_class="dataset_derived",
                         dataset="manifest", dataset_name="Import marker", dataset_version=marker,
                         license="n/a", source_url="n/a", source_record_id=marker,
                         transformation_version=w.m.get("transformation_version", TRANSFORMATION_VERSION),
                         imported_at=IMPORTED_AT, details=dict(w.stats)))
    db.commit()
    return w.stats
