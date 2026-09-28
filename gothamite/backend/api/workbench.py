from typing import Literal
from collections import Counter
from fastapi import APIRouter, Depends, Request, Response, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.workbench import IntelEntity, IntelEvidence, IntelRelationship, IncidentCase
from backend.services.workbench_security import require_session, create_session, origin_check, limit, COOKIE
from backend.services import workbench_intelligence as intel, workbench_cases as cases
from backend.services.workbench_analysis import analyze, NIST
from backend.services.workbench_seed import SNAPSHOT

session_router = APIRouter(prefix="/workbench", tags=["Local demo session"])
router = APIRouter(prefix="/workbench", tags=["Investigation workbench"], dependencies=[Depends(require_session)])


@session_router.post("/session")
def session(request: Request, response: Response):
    limit(request)
    origin_check(request)
    if request.headers.get("x-gothamite-client") != "workbench":
        raise HTTPException(403, "Demo session requires the workbench client header")
    token, csrf = create_session(request.cookies.get(COOKIE, ""))
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=43200, path="/api/v1")
    response.headers["Cache-Control"] = "no-store"
    return {"analyst": "Demo analyst", "role": "analyst", "mode": "synthetic", "csrf": csrf}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    all_cases = [cases.case_payload(db, c.id) for c in db.query(IncidentCase).order_by(IncidentCase.id).all()]
    summaries = [{k: c[k] for k in ("id", "title", "status", "severity", "analyst", "updated_at", "risk")} | {"evidence_count": len(c["evidence"]), "asset_count": sum(e["kind"] == "asset" for e in c["entities"])} for c in all_cases]
    rows = db.query(IntelEvidence).order_by(IntelEvidence.observed_at).all()
    counts = Counter(e.source for e in rows)
    activity = Counter(e.observed_at[11:13] + ":" + ("00" if int(e.observed_at[14:16]) < 30 else "30") for e in rows)
    return {"snapshot": SNAPSHOT, "mode": "synthetic", "indicators": db.query(IntelEntity).filter(IntelEntity.kind.in_(intel.INDICATOR_KINDS)).count(),
            "relationships": db.query(IntelRelationship).count(), "evidence_count": len(rows),
            "active_cases": sum(c["status"] != "CLOSED" for c in summaries),
            "critical_cases": sum(c["severity"] == "critical" and c["status"] != "CLOSED" for c in summaries),
            "cases": summaries, "sources": [{"name": k, "count": v, "mode": "synthetic"} for k,v in counts.items()],
            "activity": [{"time": k, "count": v} for k,v in sorted(activity.items())],
            "recent": [intel.serialize(e) for e in reversed(rows[-5:])]}


@router.get("/search")
def search(q: str = Query("", max_length=256), kind: str | None = Query(None, max_length=32), page: int = Query(1, ge=1, le=10000), limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    return intel.search(db, q, kind, page, limit)


@router.get("/entities/{id}")
def entity(id: str, db: Session = Depends(get_db)):
    return intel.profile(db, id)


@router.get("/evidence/{id}")
def evidence(id: str, db: Session = Depends(get_db)):
    row = db.get(IntelEvidence, id)
    if row is None:
        raise HTTPException(404, "Evidence not found")
    return intel.serialize(row)


@router.get("/graph/{id}")
def graph(id: str, depth: int = Query(3, ge=1, le=5), limit: int = Query(28, ge=4, le=60), db: Session = Depends(get_db)):
    return intel.graph(db, id, depth, limit)


@router.get("/cases/{id}")
def case(id: str, db: Session = Depends(get_db)):
    return cases.case_payload(db, id)


class Versioned(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(ge=1)


class CaseUpdate(Versioned):
    status: Literal["NEW", "TRIAGED", "INVESTIGATING", "CONTAINMENT", "REMEDIATION", "RECOVERY", "CLOSED"] | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    analyst: str | None = Field(None, min_length=1, max_length=80)


class Note(Versioned):
    kind: Literal["note", "hypothesis", "recovery", "lesson"] = "note"
    text: str = Field(min_length=1, max_length=4000)


class Decision(Versioned):
    decision: Literal["approved", "rejected", "simulated"]
    reason: str = Field("", max_length=1000)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_id: str = Field(min_length=1, max_length=80)


@router.patch("/cases/{id}")
def update_case(id: str, body: CaseUpdate, db: Session = Depends(get_db)):
    return cases.change_case(db, id, body)


@router.post("/cases/{id}/notes")
def note(id: str, body: Note, db: Session = Depends(get_db)):
    return cases.add_note(db, id, body)


@router.post("/cases/{id}/actions/{rule}")
def decision(id: str, rule: str, body: Decision, db: Session = Depends(get_db)):
    return cases.review_action(db, id, rule, body)


@router.post("/analysis")
def analysis(body: AnalysisRequest, db: Session = Depends(get_db)):
    intel.require_entity(db, body.entity_id)
    return analyze(db, body.entity_id)


@router.get("/cases/{id}/report", response_class=PlainTextResponse)
def report(id: str, db: Session = Depends(get_db)):
    payload = cases.case_payload(db, id)
    return PlainTextResponse(cases.report_markdown(payload), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="GOTHAMITE-{id}.md"', "X-Content-Type-Options": "nosniff"})


@router.get("/nist")
def nist():
    return {"version": "CSF 2.0", "source": "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf", "categories": [{"function": f, "category": c, "title": t, "activity": a} for f,c,t,a in NIST]}
