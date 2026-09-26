from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models.entities import Persona, Identifier, Relationship, Artifact, Source

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("/search", status_code=status.HTTP_200_OK)
def search_entities(
    q: str = Query(..., min_length=1, description="Search query: handle, PGP fingerprint, or wallet address"),
    db: Session = Depends(get_db),
):
    """
    Searches across personas by handle, normalized PGP fingerprint, or cryptocurrency wallet.
    """
    clean_q = q.strip()
    clean_pgp_q = "".join(clean_q.split()).upper()

    results = []
    seen_personas = set()

    # 1. Match on handle (case-insensitive substring)
    personas_by_handle = (
        db.query(Persona)
        .filter(Persona.handle.ilike(f"%{clean_q}%"))
        .all()
    )
    for p in personas_by_handle:
        seen_personas.add(p.persona_id)
        results.append({
            "persona_id": p.persona_id,
            "handle": p.handle,
            "source_id": p.source_id,
            "match_reason": "handle_match",
            "matched_term": p.handle,
            "first_seen": p.first_seen.isoformat() if p.first_seen else None,
            "last_seen": p.last_seen.isoformat() if p.last_seen else None,
        })

    # 2. Match on PGP fingerprint or wallet address
    idents = (
        db.query(Identifier)
        .filter(
            (Identifier.value.ilike(f"%{clean_q}%"))
            | (Identifier.value.ilike(f"%{clean_pgp_q}%"))
        )
        .all()
    )
    for ident in idents:
        if ident.persona_id not in seen_personas:
            seen_personas.add(ident.persona_id)
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

    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.get("/persona/{persona_id}", status_code=status.HTTP_200_OK)
def get_persona_dossier(persona_id: str, db: Session = Depends(get_db)):
    """
    Retrieves complete actor dossier for a specific persona:
    Identifiers, cross-source correlated links, activity timeline, and source information.
    """
    persona = db.query(Persona).filter_by(persona_id=persona_id).first()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona with ID '{persona_id}' not found",
        )

    # 1. Identifiers
    identifiers = (
        db.query(Identifier)
        .filter_by(persona_id=persona.persona_id)
        .all()
    )
    ident_payload = [
        {
            "identifier_id": i.identifier_id,
            "type": i.type,
            "value": i.value,
            "observed_at": i.observed_at.isoformat() if i.observed_at else None,
            "artifact_id": i.artifact_id,
        }
        for i in identifiers
    ]

    # 2. Correlated Links (both outgoing and incoming)
    rels_out = db.query(Relationship).filter_by(from_persona_id=persona.persona_id).all()
    rels_in = db.query(Relationship).filter_by(to_persona_id=persona.persona_id).all()

    links_payload = []
    for r in rels_out:
        other = db.query(Persona).filter_by(persona_id=r.to_persona_id).first()
        links_payload.append({
            "relationship_id": r.relationship_id,
            "direction": "outgoing",
            "target_persona_id": r.to_persona_id,
            "target_handle": other.handle if other else "unknown",
            "target_source": other.source_id if other else "unknown",
            "type": r.type,
            "score": r.score,
            "status": r.status,
        })

    for r in rels_in:
        other = db.query(Persona).filter_by(persona_id=r.from_persona_id).first()
        links_payload.append({
            "relationship_id": r.relationship_id,
            "direction": "incoming",
            "target_persona_id": r.from_persona_id,
            "target_handle": other.handle if other else "unknown",
            "target_source": other.source_id if other else "unknown",
            "type": r.type,
            "score": r.score,
            "status": r.status,
        })

    # 3. Timeline / Artifacts
    artifact_ids = {i.artifact_id for i in identifiers}
    artifacts = (
        db.query(Artifact)
        .filter(Artifact.artifact_id.in_(artifact_ids))
        .order_by(Artifact.collected_at.asc())
        .all()
    ) if artifact_ids else []

    timeline_payload = [
        {
            "artifact_id": a.artifact_id,
            "url": a.url,
            "collected_at": a.collected_at.isoformat() if a.collected_at else None,
            "snippet": a.raw_content[:200] + ("..." if len(a.raw_content) > 200 else ""),
        }
        for a in artifacts
    ]

    source = db.query(Source).filter_by(source_id=persona.source_id).first()

    return {
        "persona_id": persona.persona_id,
        "handle": persona.handle,
        "source_id": persona.source_id,
        "source_type": source.type if source else "unknown",
        "first_seen": persona.first_seen.isoformat() if persona.first_seen else None,
        "last_seen": persona.last_seen.isoformat() if persona.last_seen else None,
        "post_count": persona.post_count,
        "identifiers": ident_payload,
        "correlated_links": links_payload,
        "timeline": timeline_payload,
    }
