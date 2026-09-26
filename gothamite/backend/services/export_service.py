import csv
import io
from typing import Dict
from sqlalchemy.orm import Session

from backend.models.entities import Persona, Relationship, Evidence, Artifact, Source


class ExportService:
    @staticmethod
    def export_json(db: Session) -> Dict:
        """
        Exports the intelligence graph as a structured JSON bundle.
        Mandatory rule: Every evidence item includes its artifact_id for provenance.
        """
        personas = {p.persona_id: p for p in db.query(Persona).all()}
        relationships = (
            db.query(Relationship)
            .filter(Relationship.status != "rejected")
            .all()
        )

        nodes = []
        for p in personas.values():
            nodes.append({
                "persona_id": p.persona_id,
                "handle": p.handle,
                "source_id": p.source_id,
                "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                "last_seen": p.last_seen.isoformat() if p.last_seen else None,
                "post_count": p.post_count,
            })

        edges = []
        for r in relationships:
            evidence_rows = db.query(Evidence).filter_by(relationship_id=r.relationship_id).all()
            from_p = personas.get(r.from_persona_id)
            to_p = personas.get(r.to_persona_id)

            edges.append({
                "relationship_id": r.relationship_id,
                "from_persona": {
                    "persona_id": r.from_persona_id,
                    "handle": from_p.handle if from_p else "unknown",
                    "source_id": from_p.source_id if from_p else "unknown",
                },
                "to_persona": {
                    "persona_id": r.to_persona_id,
                    "handle": to_p.handle if to_p else "unknown",
                    "source_id": to_p.source_id if to_p else "unknown",
                },
                "type": r.type,
                "score": r.score,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "evidence": [
                    {
                        "evidence_id": ev.evidence_id,
                        "signal_type": ev.signal_type,
                        "direction": ev.direction,
                        "weight": ev.weight,
                        "artifact_id": ev.artifact_id,  # Mandatory provenance
                        "note": ev.note,
                    }
                    for ev in evidence_rows
                ],
            })

        return {
            "platform": "GOTHAMITE Intelligence Platform",
            "version": "1.0.0",
            "exported_nodes": len(nodes),
            "exported_relationships": len(edges),
            "nodes": nodes,
            "relationships": edges,
        }

    @staticmethod
    def export_csv(db: Session) -> str:
        """
        Exports the intelligence graph and evidence as CSV.
        Mandatory rule: Every evidence row includes artifact_id.
        """
        personas = {p.persona_id: p for p in db.query(Persona).all()}
        relationships = (
            db.query(Relationship)
            .filter(Relationship.status != "rejected")
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)

        # Header with explicit artifact_id column
        writer.writerow([
            "relationship_id",
            "from_handle",
            "from_source",
            "to_handle",
            "to_source",
            "type",
            "score",
            "status",
            "signal_type",
            "direction",
            "weight",
            "artifact_id",
            "note",
        ])

        for r in relationships:
            from_p = personas.get(r.from_persona_id)
            to_p = personas.get(r.to_persona_id)
            evidence_rows = db.query(Evidence).filter_by(relationship_id=r.relationship_id).all()

            if not evidence_rows:
                writer.writerow([
                    r.relationship_id,
                    from_p.handle if from_p else r.from_persona_id,
                    from_p.source_id if from_p else "",
                    to_p.handle if to_p else r.to_persona_id,
                    to_p.source_id if to_p else "",
                    r.type,
                    f"{r.score:.2f}",
                    r.status,
                    "",
                    "",
                    "",
                    "",
                    "",
                ])
            else:
                for ev in evidence_rows:
                    writer.writerow([
                        r.relationship_id,
                        from_p.handle if from_p else r.from_persona_id,
                        from_p.source_id if from_p else "",
                        to_p.handle if to_p else r.to_persona_id,
                        to_p.source_id if to_p else "",
                        r.type,
                        f"{r.score:.2f}",
                        r.status,
                        ev.signal_type,
                        ev.direction,
                        f"{ev.weight:.2f}",
                        ev.artifact_id,  # Mandatory provenance
                        ev.note,
                    ])

        return output.getvalue()
