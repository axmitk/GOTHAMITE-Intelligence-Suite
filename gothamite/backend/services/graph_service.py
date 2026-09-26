from typing import Dict, List, Optional
import networkx as nx
from sqlalchemy.orm import Session

from backend.models.entities import Persona, Relationship, Evidence, Artifact, Source


class GraphService:
    @staticmethod
    def build_networkx_graph(db: Session, include_rejected: bool = False) -> nx.DiGraph:
        """
        Builds an in-memory NetworkX directed graph from database records on demand.
        Stateless: creates a fresh graph object per request.
        """
        G = nx.DiGraph()

        personas = db.query(Persona).all()
        for p in personas:
            G.add_node(
                p.persona_id,
                handle=p.handle,
                source_id=p.source_id,
                first_seen=p.first_seen.isoformat() if p.first_seen else None,
                last_seen=p.last_seen.isoformat() if p.last_seen else None,
                post_count=p.post_count,
            )

        query = db.query(Relationship)
        if not include_rejected:
            query = query.filter(Relationship.status != "rejected")

        relationships = query.all()
        for r in relationships:
            G.add_edge(
                r.from_persona_id,
                r.to_persona_id,
                relationship_id=r.relationship_id,
                type=r.type,
                score=r.score,
                status=r.status,
            )

        return G

    @staticmethod
    def get_graph_payload(db: Session) -> Dict:
        """
        Returns JSON-serializable graph payload containing active nodes and edges.
        Edges with status == 'rejected' are strictly excluded.
        """
        G = GraphService.build_networkx_graph(db, include_rejected=False)

        # Retrieve personas for metadata
        personas = {p.persona_id: p for p in db.query(Persona).all()}

        nodes = []
        for node_id in G.nodes:
            p = personas.get(node_id)
            if p:
                nodes.append({
                    "id": p.persona_id,
                    "handle": p.handle,
                    "source_id": p.source_id,
                    "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                    "last_seen": p.last_seen.isoformat() if p.last_seen else None,
                    "post_count": p.post_count,
                })

        # Query active relationships and their evidence count
        relationships = (
            db.query(Relationship)
            .filter(Relationship.status != "rejected")
            .all()
        )

        edges = []
        for r in relationships:
            ev_count = db.query(Evidence).filter_by(relationship_id=r.relationship_id).count()
            from_p = personas.get(r.from_persona_id)
            to_p = personas.get(r.to_persona_id)

            edges.append({
                "id": r.relationship_id,
                "from_node": r.from_persona_id,
                "to_node": r.to_persona_id,
                "from_handle": from_p.handle if from_p else r.from_persona_id,
                "to_handle": to_p.handle if to_p else r.to_persona_id,
                "type": r.type,
                "score": r.score,
                "status": r.status,
                "evidence_count": ev_count,
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    @staticmethod
    def get_edge_details(db: Session, relationship_id: str) -> Optional[Dict]:
        """Returns complete edge details with all supporting and contradicting evidence."""
        rel = db.query(Relationship).filter_by(relationship_id=relationship_id).first()
        if not rel:
            return None

        from_p = db.query(Persona).filter_by(persona_id=rel.from_persona_id).first()
        to_p = db.query(Persona).filter_by(persona_id=rel.to_persona_id).first()

        evidence_rows = (
            db.query(Evidence)
            .filter_by(relationship_id=rel.relationship_id)
            .all()
        )

        evidence_payload = [
            {
                "evidence_id": ev.evidence_id,
                "signal_type": ev.signal_type,
                "direction": ev.direction,
                "weight": ev.weight,
                "artifact_id": ev.artifact_id,
                "note": ev.note,
            }
            for ev in evidence_rows
        ]

        return {
            "relationship_id": rel.relationship_id,
            "type": rel.type,
            "score": rel.score,
            "status": rel.status,
            "created_at": rel.created_at.isoformat() if rel.created_at else None,
            "from_persona": {
                "persona_id": from_p.persona_id if from_p else rel.from_persona_id,
                "handle": from_p.handle if from_p else "unknown",
                "source_id": from_p.source_id if from_p else "unknown",
            },
            "to_persona": {
                "persona_id": to_p.persona_id if to_p else rel.to_persona_id,
                "handle": to_p.handle if to_p else "unknown",
                "source_id": to_p.source_id if to_p else "unknown",
            },
            "evidence": evidence_payload,
        }

    @staticmethod
    def update_edge_status(db: Session, relationship_id: str, new_status: str) -> Optional[Dict]:
        """Updates relationship status to 'confirmed' or 'rejected'."""
        rel = db.query(Relationship).filter_by(relationship_id=relationship_id).first()
        if not rel:
            return None

        rel.status = new_status
        db.commit()
        db.refresh(rel)

        return GraphService.get_edge_details(db, relationship_id)
