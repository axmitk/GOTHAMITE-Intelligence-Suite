from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import update
from backend.models.workbench import IncidentCase, CaseNote, ResponseAction, AuditEvent, IntelRelationship
from backend.services.workbench_intelligence import require_case, require_entity, context_for, serialize, with_provenance
from backend.services.workbench_analysis import risk_assessment, EvidenceRuleProvider, recommendations, nist_mapping, STATES


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def audit(db, id, action, detail):
    db.add(AuditEvent(id=str(uuid4()), case_id=id, actor="Demo analyst", action=action, detail=detail, created_at=now()))


def claim_version(db, case, expected):
    changed = db.execute(update(IncidentCase).where(IncidentCase.id == case.id, IncidentCase.version == expected)
                         .values(version=expected+1, updated_at=now()).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Case changed in another session. Refresh before trying again.")
    db.refresh(case)


CONTAINMENT_RULES = {"isolate", "block", "identity", "hunt"}


def advance_requirement(db, case):
    """Return the unmet prerequisite for the next workflow stage, or None when ready."""
    current = STATES.index(case.status)
    if current == len(STATES) - 1:
        return None
    target = STATES[current + 1]
    if target == "CONTAINMENT":
        actions = db.query(ResponseAction).filter_by(case_id=case.id, status="simulated").all()
        if not any(a.rule in CONTAINMENT_RULES for a in actions):
            return "Review, approve and simulate a containment or scoped hunt action before entering containment."
    if target == "CLOSED":
        notes = db.query(CaseNote).filter_by(case_id=case.id).all()
        recovery = db.query(ResponseAction).filter_by(case_id=case.id, rule="recover", status="simulated").first()
        if not {"recovery", "lesson"}.issubset({n.kind for n in notes}) or not recovery:
            return "Closure requires a recovery validation note, a lesson learned, and the simulated recovery action."
    return None


def case_payload(db, id):
    case = require_case(db, id)
    entity = require_entity(db, id)
    evidence, entities = context_for(db, id)
    notes = db.query(CaseNote).filter_by(case_id=id).order_by(CaseNote.created_at).all()
    actions = db.query(ResponseAction).filter_by(case_id=id).all()
    saved = {a.rule: a for a in actions}
    recs = [{**r, "id": f"{id}:{r['rule']}", "status": saved[r['rule']].status if r['rule'] in saved else "pending",
             "decision_note": saved[r['rule']].decision_note if r['rule'] in saved else ""} for r in recommendations(evidence)]
    events = db.query(AuditEvent).filter_by(case_id=id).order_by(AuditEvent.created_at).all()
    evidence_ids = [e.id for e in evidence]
    relationships = db.query(IntelRelationship).filter(IntelRelationship.evidence_id.in_(evidence_ids)).order_by(IntelRelationship.id).all()
    return {**serialize(case), "title": entity.label, "summary": entity.summary,
            "entities": [serialize(e) for e in entities if e.id != id], "evidence": with_provenance(db, [serialize(e) for e in evidence], "evidence"),
            "relationships": [serialize(r) for r in relationships],
            "risk": risk_assessment(evidence, entities), "analysis": EvidenceRuleProvider().analyze(evidence, entities),
            "notes": [serialize(n) for n in notes], "actions": recs,
            "nist": nist_mapping(case, notes, actions, evidence, recs), "audit": [serialize(e) for e in events], "states": STATES,
            "advance": advance_stage(db, case)}


def advance_stage(db, case):
    index = STATES.index(case.status)
    if index == len(STATES) - 1:
        return {"next": None, "ready": False, "requirement": "Case closed. The investigation record is final."}
    requirement = advance_requirement(db, case)
    return {"next": STATES[index + 1], "ready": requirement is None, "requirement": requirement or ""}


def change_case(db, id, body):
    case = require_case(db, id)
    if body.status is not None and body.status != case.status:
        current = STATES.index(case.status)
        if current == len(STATES)-1 or body.status != STATES[current+1]:
            raise HTTPException(409, "Advance one workflow stage at a time.")
        requirement = advance_requirement(db, case)
        if requirement:
            raise HTTPException(409, requirement)
    claim_version(db, case, body.version)
    changes = []
    for field in ("status", "severity", "analyst"):
        value = getattr(body, field)
        if value is not None and value != getattr(case, field):
            changes.append(f"{field}: {getattr(case, field)} → {value}")
            setattr(case, field, value)
    audit(db, id, "case_updated", "; ".join(changes) or "Case reviewed")
    db.commit()
    return case_payload(db, id)


def add_note(db, id, body):
    case = require_case(db, id)
    claim_version(db, case, body.version)
    db.add(CaseNote(id=str(uuid4()), case_id=id, kind=body.kind, text=body.text, author="Demo analyst", created_at=now()))
    audit(db, id, "note_added", f"Added {body.kind} entry")
    db.commit()
    return case_payload(db, id)


def review_action(db, id, rule, body):
    case = require_case(db, id)
    if case.status == "CLOSED":
        raise HTTPException(409, "Closed cases cannot execute response simulations.")
    evidence, _ = context_for(db, id)
    rec = next((r for r in recommendations(evidence) if r["rule"] == rule), None)
    if rec is None:
        raise HTTPException(404, "No evidence-backed recommendation exists for this action")
    action = db.get(ResponseAction, f"{id}:{rule}")
    previous = action.status if action else "pending"
    allowed = {"pending": {"approved", "rejected"}, "approved": {"simulated", "rejected"}, "rejected": {"approved"}, "simulated": set()}
    if body.decision not in allowed[previous]:
        raise HTTPException(409, "Action must be approved before simulation and cannot be simulated twice.")
    if body.decision == "rejected" and not body.reason:
        raise HTTPException(400, "Record a reason for rejecting a recommendation.")
    claim_version(db, case, body.version)
    if action is None:
        action = ResponseAction(id=f"{id}:{rule}", case_id=id, rule=rule)
        db.add(action)
    action.status, action.decision_note = body.decision, body.reason
    action.decided_by, action.decided_at = "Demo analyst", now()
    audit(db, id, f"response_{body.decision}", f"{rec['title']}: {body.reason or 'Analyst reviewed supporting evidence.'} Simulation only; no system command executed.")
    db.commit()
    return case_payload(db, id)


def _provenance_phrase_dicts(evidence) -> str:
    class _E:
        def __init__(self, p): self.provenance = p
    from backend.services.workbench_analysis import _provenance_phrase
    return _provenance_phrase([_E(e.get("provenance", "synthetic")) for e in evidence])


def report_markdown(case):
    def safe(value):
        # Reports are plain Markdown; neutralize HTML and active link syntax in user notes.
        return str(value).replace("<", "&lt;").replace(">", "&gt;").replace("[", "\\[").replace("]", "\\]").replace("#", "\\#")
    prov = {e.get("provenance", "synthetic") for e in case["evidence"]}
    banner = ("SYNTHETIC EXERCISE — no real intelligence or response execution." if prov <= {"synthetic"} else
              "CONTAINS DATASET-DERIVED EVIDENCE from public research datasets (see Evidence sources). "
              "Response actions are simulations; no external system is changed.")
    rows = [f"# GOTHAMITE / {case['id']}", "", banner, "",
            safe(case["title"]), "Generated from the saved investigation trail. Observations, interpretation and approvals are distinct.",
            f"Status: {case['status']} | Analyst: {safe(case['analyst'])} | Severity: {case['severity']}",
            f"Created: {case['created_at']} | Updated: {case['updated_at']} | Version: {case['version']}",
            "", "## Executive summary"]
    actions = case["actions"]
    decided = [a for a in actions if a["status"] != "pending"]
    findings = case["analysis"]["findings"]
    rows += [
        f"{_provenance_phrase_dicts(case['evidence'])} and {len(case['relationships'])} evidence-backed relationships support this case. "
        f"Baseline risk is {case['risk']['score']}/100 ({case['risk']['level']}) from {len(case['risk']['factors'])} evidenced factors.",
        (f"Rule-based findings: {'; '.join(f['title'] + ' (' + f['confidence'] + ' confidence)' for f in findings)}."
         if findings else "Insufficient evidence for a rule-based finding."),
        f"Response: {len(decided)} of {len(actions)} recommendations reviewed "
        f"({sum(a['status'] == 'simulated' for a in actions)} simulated, {sum(a['status'] == 'rejected' for a in actions)} rejected). "
        f"Case stage: {case['status']}." + (f" Next stage requires: {case['advance']['requirement']}" if case["advance"]["requirement"] and case["advance"]["next"] else ""),
        "", "## Observed evidence" + (" (synthetic)" if prov <= {"synthetic"} else "")]
    rows += ["### Evidence sources", "Dataset-derived evidence and synthetic demonstration evidence are listed separately."]
    sources: dict = {}
    for ev in case["evidence"]:
        rec = ev.get("dataset_record")
        k = rec["dataset"] if rec else "synthetic"
        sources.setdefault(k, {"rec": rec, "n": 0})["n"] += 1
    for k, v in sorted(sources.items()):
        rec = v["rec"]
        if rec:
            rows.append(f"- Dataset-derived evidence: {v['n']} observation(s) from {safe(rec['dataset_name'])}, "
                        f"version {safe(rec['dataset_version'])}, licence {safe(rec['license'])}"
                        + (f", DOI {rec['doi']}" if rec.get("doi") else "") + f", {rec['source_url']}. "
                        f"Transformation {rec['transformation_version']}; imported {rec['imported_at']}.")
        else:
            rows.append(f"- Synthetic demonstration evidence: {v['n']} observation(s) from the GOTHAMITE exercise seed.")
    rows.append("")
    for ev in case["evidence"]:
        rec = ev.get("dataset_record")
        label = (f"Dataset-derived | {safe(rec['dataset_name'])} | record {safe(rec['source_record_id'])}" if rec
                 else "Synthetic demonstration evidence")
        rows += [f"### {ev['id']} — {safe(ev['title'])}", f"{ev['observed_at']} | {safe(ev['source'])} | confidence annotation: {ev['confidence']}",
                 f"Provenance: {label}", safe(ev["content"]), f"SHA-256: {ev['content_hash']}", ""]
    rows += ["## Correlated context", "Evidence-backed associations; not proof of actor identity or compromise."]
    labels = {e["id"]: e["label"] for e in case["entities"]}
    labels[case["id"]] = case["title"]
    rows += [f"- {e['kind']}: {safe(e['label'])} ({e['id']})" for e in case["entities"]]
    rows += ["### Supporting relationships"]
    rows += [f"- {safe(labels.get(r['source_id'], r['source_id']))} → {r['relation']} → {safe(labels.get(r['target_id'], r['target_id']))}. Confidence: {r['confidence']}. Evidence: {r['evidence_id']}" for r in case["relationships"]]
    rows += ["", "## Automated interpretation (offline evidence rules)", "Automated interpretation, not observed fact. This exercise uses a deterministic rule provider, not an LLM.", case["analysis"]["provider"], case["analysis"]["summary"]]
    rows += [f"- {f['title']} [{f['confidence']}] — {f['interpretation']} Evidence: {', '.join(f['evidence_ids'])}. Next: {f['next_step']}" for f in case["analysis"]["findings"]]
    rows += ["### Uncertainties"] + case["analysis"]["uncertainties"]
    rows += ["", "## Risk assessment", f"{case['risk']['score']}/100 — {case['risk']['level']}", case["risk"]["method"], case["risk"]["limitation"]]
    rows += [f"- +{f['points']} {f['label']} — {f['reason']} Evidence: {', '.join(f['evidence_ids'])}" for f in case["risk"]["factors"]]
    rows += ["", "## NIST alignment", "NIST CSF 2.0 investigation workflow: function applicability, supporting evidence and linked response status. Not a compliance assessment."]
    rows += [f"- {n['function']} / {n['category']}: {n['activity']} ({n['status']}). Basis: {safe(n['basis'])}"
             + (f" Evidence: {', '.join(n['evidence_ids'])}." if n["evidence_ids"] else "")
             + (f" Response: {'; '.join(a['title'] + ' — ' + a['status'] for a in n['actions'])}." if n["actions"] else "") for n in case["nist"]]
    rows += ["Source: https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf", "", "## Response recommendations", "Recommendation → analyst approval → simulation. No external system is changed."]
    rows += [f"- {a['title']} / {a['status']} / {a['priority']} — {a['reason']} Expected effect: {a['effect']} Evidence: {', '.join(a['evidence_ids'])}. Decision note: {safe(a['decision_note']) or 'No note recorded.'}" for a in case["actions"]]
    rows += ["", "## Analyst decisions", f"Assigned analyst: {safe(case['analyst'])}. Local exercise seat; not verified identity.", "### Response approvals"]
    rows += [f"- {a['title']}: {a['status']}. Note: {safe(a['decision_note']) or 'No note recorded.'}" for a in decided] or ["No response recommendation has been reviewed."]
    rows += ["### Analyst conclusions and hypotheses"]
    rows += [f"- {n['created_at']} / {n['kind']} / {safe(n['author'])}: {safe(n['text'])}" for n in case["notes"]] or ["No analyst conclusions recorded."]
    rows += ["", "## Audit trail", "Every case change, note, approval and simulation, in order. UTC."]
    rows += [f"- {e['created_at']} / {e['actor']} / {e['action']}: {safe(e['detail'])}" for e in case["audit"]] or ["No analyst changes or approvals recorded."]
    return "\n\n".join(rows)
