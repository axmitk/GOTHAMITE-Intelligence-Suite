import os
import sys
from pathlib import Path
import requests
from typing import Dict, List, Optional

# Ensure repository root is on sys.path for standalone imports
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# API base URL (configurable via env)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def check_api_online() -> bool:
    try:
        r = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False


def get_graph() -> Dict:
    if check_api_online():
        try:
            r = requests.get(f"{API_BASE_URL}/graph", timeout=5.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

    # Direct database fallback if API server is not running
    from backend.db import SessionLocal, init_db
    from backend.services.graph_service import GraphService
    init_db()
    db = SessionLocal()
    try:
        return GraphService.get_graph_payload(db)
    finally:
        db.close()


def get_edge_details(relationship_id: str) -> Optional[Dict]:
    if check_api_online():
        try:
            r = requests.get(f"{API_BASE_URL}/graph/edge/{relationship_id}", timeout=5.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

    from backend.db import SessionLocal
    from backend.services.graph_service import GraphService
    db = SessionLocal()
    try:
        return GraphService.get_edge_details(db, relationship_id)
    finally:
        db.close()


def update_edge_status(relationship_id: str, new_status: str) -> Optional[Dict]:
    if check_api_online():
        try:
            r = requests.patch(
                f"{API_BASE_URL}/graph/edge/{relationship_id}",
                json={"status": new_status},
                timeout=5.0,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

    from backend.db import SessionLocal
    from backend.services.graph_service import GraphService
    db = SessionLocal()
    try:
        return GraphService.update_edge_status(db, relationship_id, new_status)
    finally:
        db.close()


def trigger_correlation() -> Dict:
    if check_api_online():
        try:
            r = requests.post(f"{API_BASE_URL}/correlate", timeout=10.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

    from backend.db import SessionLocal
    from backend.services.correlation_service import CorrelationService
    db = SessionLocal()
    try:
        return CorrelationService.run_correlation(db)
    finally:
        db.close()


def search_entities(q: str) -> Dict:
    if check_api_online():
        try:
            r = requests.get(f"{API_BASE_URL}/entities/search", params={"q": q}, timeout=5.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

    from backend.db import SessionLocal
    from backend.models.entities import Persona, Identifier
    db = SessionLocal()
    try:
        clean_q = q.strip()
        results = []
        seen = set()
        for p in db.query(Persona).filter(Persona.handle.ilike(f"%{clean_q}%")).all():
            seen.add(p.persona_id)
            results.append({
                "persona_id": p.persona_id,
                "handle": p.handle,
                "source_id": p.source_id,
                "match_reason": "handle_match",
                "matched_term": p.handle,
                "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                "last_seen": p.last_seen.isoformat() if p.last_seen else None,
            })
        for ident in db.query(Identifier).filter(Identifier.value.ilike(f"%{clean_q}%")).all():
            if ident.persona_id not in seen:
                seen.add(ident.persona_id)
                p = db.query(Persona).filter_by(persona_id=ident.persona_id).first()
                if p:
                    results.append({
                        "persona_id": p.persona_id,
                        "handle": p.handle,
                        "source_id": p.source_id,
                        "match_reason": f"{ident.type}_match",
                        "matched_term": ident.value,
                        "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                        "last_seen": p.last_seen.isoformat() if p.last_seen else None,
                    })
        return {"query": q, "count": len(results), "results": results}
    finally:
        db.close()


def get_persona_dossier(persona_id: str) -> Optional[Dict]:
    if check_api_online():
        try:
            r = requests.get(f"{API_BASE_URL}/entities/persona/{persona_id}", timeout=5.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

    from backend.db import SessionLocal
    from backend.models.entities import Persona, Identifier, Relationship, Artifact, Source
    db = SessionLocal()
    try:
        p = db.query(Persona).filter_by(persona_id=persona_id).first()
        if not p:
            return None
        idents = db.query(Identifier).filter_by(persona_id=p.persona_id).all()
        ident_payload = [
            {
                "identifier_id": i.identifier_id,
                "type": i.type,
                "value": i.value,
                "observed_at": i.observed_at.isoformat() if i.observed_at else None,
                "artifact_id": i.artifact_id,
            }
            for i in idents
        ]
        rels_out = db.query(Relationship).filter_by(from_persona_id=p.persona_id).all()
        rels_in = db.query(Relationship).filter_by(to_persona_id=p.persona_id).all()
        links = []
        for r in rels_out:
            o = db.query(Persona).filter_by(persona_id=r.to_persona_id).first()
            links.append({
                "relationship_id": r.relationship_id,
                "direction": "outgoing",
                "target_persona_id": r.to_persona_id,
                "target_handle": o.handle if o else "unknown",
                "target_source": o.source_id if o else "unknown",
                "type": r.type,
                "score": r.score,
                "status": r.status,
            })
        for r in rels_in:
            o = db.query(Persona).filter_by(persona_id=r.from_persona_id).first()
            links.append({
                "relationship_id": r.relationship_id,
                "direction": "incoming",
                "target_persona_id": r.from_persona_id,
                "target_handle": o.handle if o else "unknown",
                "target_source": o.source_id if o else "unknown",
                "type": r.type,
                "score": r.score,
                "status": r.status,
            })
        art_ids = {i.artifact_id for i in idents}
        artifacts = db.query(Artifact).filter(Artifact.artifact_id.in_(art_ids)).order_by(Artifact.collected_at.asc()).all() if art_ids else []
        timeline = [
            {
                "artifact_id": a.artifact_id,
                "url": a.url,
                "collected_at": a.collected_at.isoformat() if a.collected_at else None,
                "snippet": a.raw_content[:200] + ("..." if len(a.raw_content) > 200 else ""),
            }
            for a in artifacts
        ]
        source = db.query(Source).filter_by(source_id=p.source_id).first()
        return {
            "persona_id": p.persona_id,
            "handle": p.handle,
            "source_id": p.source_id,
            "source_type": source.type if source else "unknown",
            "first_seen": p.first_seen.isoformat() if p.first_seen else None,
            "last_seen": p.last_seen.isoformat() if p.last_seen else None,
            "post_count": p.post_count,
            "identifiers": ident_payload,
            "correlated_links": links,
            "timeline": timeline,
        }
    finally:
        db.close()


def get_artifact(artifact_id: str) -> Optional[Dict]:
    if check_api_online():
        try:
            r = requests.get(f"{API_BASE_URL}/artifacts/{artifact_id}", timeout=5.0)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass

    from backend.db import SessionLocal
    from backend.models.entities import Artifact
    db = SessionLocal()
    try:
        a = db.query(Artifact).filter_by(artifact_id=artifact_id).first()
        if not a:
            return None
        return {
            "artifact_id": a.artifact_id,
            "source_id": a.source_id,
            "url": a.url,
            "content_hash": a.content_hash,
            "collected_at": a.collected_at.isoformat() if a.collected_at else None,
            "relay_path": a.relay_path,
            "raw_content": a.raw_content,
        }
    finally:
        db.close()


def get_all_personas() -> List[Dict]:
    from backend.db import SessionLocal, init_db
    from backend.models.entities import Persona
    init_db()
    db = SessionLocal()
    try:
        personas = db.query(Persona).all()
        return [
            {
                "persona_id": p.persona_id,
                "handle": p.handle,
                "source_id": p.source_id,
                "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                "last_seen": p.last_seen.isoformat() if p.last_seen else None,
                "post_count": p.post_count,
            }
            for p in personas
        ]
    finally:
        db.close()


def get_sources_metrics() -> List[Dict]:
    from backend.db import SessionLocal, init_db
    from backend.models.entities import Source, Persona, Artifact
    init_db()
    db = SessionLocal()
    try:
        sources = db.query(Source).all()
        res = []
        for s in sources:
            p_count = db.query(Persona).filter_by(source_id=s.source_id).count()
            a_count = db.query(Artifact).filter_by(source_id=s.source_id).count()
            res.append({
                "source_id": s.source_id,
                "type": s.type,
                "reliability": s.reliability,
                "status": s.status,
                "last_scan": s.last_scan.isoformat() if s.last_scan else "Never",
                "personas_count": p_count,
                "artifacts_count": a_count,
            })
        return res
    finally:
        db.close()


def get_timeline_all_events() -> List[Dict]:
    """Retrieves all observation events ordered by time for the timeline page."""
    from backend.db import SessionLocal, init_db
    from backend.models.entities import Persona, Artifact, Identifier
    init_db()
    db = SessionLocal()
    try:
        events = []
        personas = {p.persona_id: p for p in db.query(Persona).all()}
        identifiers = db.query(Identifier).order_by(Identifier.observed_at.asc()).all()
        artifacts = {a.artifact_id: a for a in db.query(Artifact).all()}

        for ident in identifiers:
            p = personas.get(ident.persona_id)
            a = artifacts.get(ident.artifact_id)
            if p:
                events.append({
                    "observed_at": ident.observed_at.isoformat() if ident.observed_at else None,
                    "handle": p.handle,
                    "source_id": p.source_id,
                    "identifier_type": ident.type,
                    "identifier_value": ident.value,
                    "artifact_id": ident.artifact_id,
                    "url": a.url if a else "unknown",
                })
        return events
    finally:
        db.close()


def format_score_badge(score: float) -> str:
    """Formats confidence score with official band labels per DATA_MODEL.md §3."""
    if score >= 0.80:
        return f"{score:.2f} [Very Strong Link]"
    elif score >= 0.60:
        return f"{score:.2f} [Strong Link]"
    elif score >= 0.30:
        return f"{score:.2f} [Moderate Link]"
    else:
        return f"{score:.2f} [Weak / Below Threshold]"
