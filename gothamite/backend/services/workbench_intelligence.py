"""Evidence-scoped queries and bounded graph traversal."""
from collections import deque
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.models.workbench import IntelEntity, IntelEvidence, EvidenceEntity, IntelRelationship, IncidentCase, DatasetRecord

INDICATOR_KINDS = ("ip", "domain", "hash", "url", "email")


def serialize(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


_PROV_FIELDS = ("provenance_class", "dataset", "dataset_name", "dataset_version", "license", "source_url",
                "doi", "source_record_id", "transformation_version", "imported_at", "details")


def with_provenance(db: Session, rows: list[dict], record_type: str) -> list[dict]:
    """Attach full dataset provenance (``dataset_record``) to serialized rows.
    Synthetic seed rows have none and get ``None``: they are never relabelled."""
    ids = [r["id"] for r in rows]
    found = {}
    if ids:
        for rec in db.query(DatasetRecord).filter(DatasetRecord.record_type == record_type,
                                                  DatasetRecord.record_id.in_(ids)).all():
            found[rec.record_id] = {f: getattr(rec, f) for f in _PROV_FIELDS}
    for r in rows:
        r["dataset_record"] = found.get(r["id"])
    return rows


def require_entity(db: Session, id: str) -> IntelEntity:
    row = db.get(IntelEntity, id)
    if row is None:
        raise HTTPException(404, "Intelligence entity not found")
    return row


def require_case(db: Session, id: str) -> IncidentCase:
    row = db.get(IncidentCase, id)
    if row is None:
        raise HTTPException(404, "Investigation not found")
    return row


def evidence_for(db: Session, id: str):
    return db.query(IntelEvidence).join(EvidenceEntity).filter(EvidenceEntity.entity_id == id).order_by(IntelEvidence.observed_at, IntelEvidence.id).all()


def context_for(db: Session, id: str):
    evidence = evidence_for(db, id)
    ids = [e.id for e in evidence]
    entities = db.query(IntelEntity).join(EvidenceEntity).filter(EvidenceEntity.evidence_id.in_(ids)).distinct().all() if ids else []
    return evidence, entities


def search(db: Session, q: str, kind: str | None, page: int, limit: int):
    query = db.query(IntelEntity)
    if kind == "indicator":
        query = query.filter(IntelEntity.kind.in_(INDICATOR_KINDS))
    elif kind:
        query = query.filter(IntelEntity.kind == kind)
    clean = q.strip().lower()
    if clean:
        # autoescape prevents % and _ from becoming user-controlled SQL wildcards.
        query = query.filter(or_(IntelEntity.label.icontains(clean, autoescape=True), IntelEntity.id.icontains(clean, autoescape=True)))
    total = query.count()
    rows = query.order_by((IntelEntity.label.ilike(clean)).desc(), IntelEntity.id).offset((page-1)*limit).limit(limit).all()
    return {"query": q, "total": total, "page": page, "limit": limit, "results": [serialize(r) for r in rows]}


def _with_edge_provenance(db: Session, edges: list[dict]) -> list[dict]:
    """Label each edge with the provenance of the observation that supports it."""
    ids = {e["evidence_id"] for e in edges}
    found = dict(db.query(IntelEvidence.id, IntelEvidence.provenance).filter(IntelEvidence.id.in_(ids)).all()) if ids else {}
    for e in edges:
        e["provenance"] = found.get(e["evidence_id"])
    return edges


def graph(db: Session, root: str, depth: int = 3, limit: int = 32):
    root_entity = require_entity(db, root)
    evidence, entities = context_for(db, root)
    if root_entity.kind == "incident":
        evidence_ids = [e.id for e in evidence]
        scoped_edges = db.query(IntelRelationship).filter(IntelRelationship.evidence_id.in_(evidence_ids)).order_by(IntelRelationship.id).all()
        node_ids, frontier_ids = {root}, {root}
        for _ in range(depth):
            neighbors = {r.target_id for r in scoped_edges if r.source_id in frontier_ids} | {r.source_id for r in scoped_edges if r.target_id in frontier_ids}
            frontier_ids = neighbors - node_ids
            node_ids |= frontier_ids
        nodes = db.query(IntelEntity).filter(IntelEntity.id.in_(node_ids)).order_by((IntelEntity.id == root).desc(), IntelEntity.kind, IntelEntity.id).limit(limit).all()
        included = {n.id for n in nodes}
        return {"root": root, "nodes": [serialize(n) for n in nodes],
                "edges": _with_edge_provenance(db, [serialize(r) for r in scoped_edges if r.source_id in included and r.target_id in included]),
                "truncated": len(node_ids) > limit, "depth": depth, "limit": limit}
    # Prioritize the connected evidence slice before expanding campaign infrastructure.
    contextual = {e.id for e in entities}
    visited, frontier, edges, seen_edges = {root}, deque([(root, 0)]), [], set()
    truncated = False
    while frontier:
        node, level = frontier.popleft()
        if level >= depth:
            continue
        if node != root and db.get(IntelEntity, node).kind == "organization":
            continue
        rows = db.query(IntelRelationship).filter(or_(IntelRelationship.source_id == node, IntelRelationship.target_id == node)).order_by(IntelRelationship.id).all()
        rows.sort(key=lambda r: (not (r.source_id in contextual and r.target_id in contextual), r.id))
        for rel in rows:
            other = rel.target_id if rel.source_id == node else rel.source_id
            if other not in visited:
                if len(visited) >= limit:
                    truncated = True
                    continue
                visited.add(other)
                frontier.append((other, level + 1))
            if rel.id not in seen_edges:
                seen_edges.add(rel.id)
                edges.append(serialize(rel))
    nodes = db.query(IntelEntity).filter(IntelEntity.id.in_(visited)).order_by(IntelEntity.kind, IntelEntity.id).all()
    return {"root": root, "nodes": [serialize(n) for n in nodes], "edges": _with_edge_provenance(db, edges), "truncated": truncated, "depth": depth, "limit": limit}


def profile(db: Session, id: str):
    entity = require_entity(db, id)
    evidence, entities = context_for(db, id)
    related_cases = [e for e in entities if e.kind == "incident"]
    # A secondary IOC may only have campaign-level context. Follow a typed campaign
    # association without inferring an observation on every case asset.
    campaign_ids = [e.id for e in entities if e.kind == "campaign"]
    if campaign_ids:
        links = db.query(IntelRelationship).filter(IntelRelationship.relation == "INVESTIGATES", IntelRelationship.target_id.in_(campaign_ids)).all()
        known = {e.id for e in related_cases}
        related_cases += [require_entity(db, r.source_id) for r in links if r.source_id not in known]
    direct = db.query(IntelRelationship).filter(or_(IntelRelationship.source_id == id, IntelRelationship.target_id == id)).all()
    neighbor_ids = {r.target_id if r.source_id == id else r.source_id for r in direct}
    neighbors = db.query(IntelEntity).filter(IntelEntity.id.in_(neighbor_ids)).all() if neighbor_ids else []
    return {"entity": with_provenance(db, [serialize(entity)], "entity")[0],
            "evidence": with_provenance(db, [serialize(e) for e in evidence], "evidence"),
            "neighbors": [serialize(n) for n in neighbors], "relationships": [serialize(r) for r in direct],
            "related_cases": [serialize(c) for c in related_cases],
            "next_step": "Inspect the supporting observations, follow the connected campaign, and validate scope in the related investigation." if evidence else "Insufficient evidence. Collect an observation before classifying this entity."}
