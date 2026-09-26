#!/usr/bin/env python3
"""
CLI runner for the GOTHAMITE deterministic correlation pipeline.
Evaluates cross-source personas, computes confidence scores, outputs auditable evidence rows.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import init_db, SessionLocal
from backend.services.correlation_service import CorrelationService
from backend.models.entities import Relationship, Evidence, Persona


def print_correlation_report(db, result):
    print("=" * 70)
    print("           GOTHAMITE CORRELATION PASS REPORT           ")
    print("=" * 70)
    print(f"Evaluated Persona Pairs: {result['evaluated_pairs']}")
    print(f"Relationships Created:   {result['relationships_created']}")
    print(f"Relationships Updated:   {result['relationships_updated']}")
    print(f"Rejected Kept / Skipped: {result['rejected_skipped']}")
    print(f"Active Relationships:    {result['active_relationships']}")
    print("-" * 70)

    rels = db.query(Relationship).all()
    if not rels:
        print("No relationships currently above threshold (score >= 0.30).")
        print("=" * 70)
        return

    for r in rels:
        from_p = db.query(Persona).filter_by(persona_id=r.from_persona_id).first()
        to_p = db.query(Persona).filter_by(persona_id=r.to_persona_id).first()
        from_handle = from_p.handle if from_p else r.from_persona_id
        to_handle = to_p.handle if to_p else r.to_persona_id

        print(f"\n[EDGE] {from_handle} ({from_p.source_id})  ──[{r.type}]──►  {to_handle} ({to_p.source_id})")
        print(f"       Score: {r.score:.2f} | Status: {r.status} | Rel ID: {r.relationship_id}")
        print("       Evidence Trail:")

        evidence_items = db.query(Evidence).filter_by(relationship_id=r.relationship_id).all()
        for ev in evidence_items:
            sign = "+" if ev.direction == "supporting" else "−"
            print(f"         • [{sign}{abs(ev.weight):.2f}] {ev.signal_type.upper()} ({ev.direction}): {ev.note}")
            print(f"           ↳ Artifact Provenance: {ev.artifact_id}")

    print("\n" + "=" * 70)


def main():
    print("[*] Connecting to database and running correlation pass...")
    init_db()
    session = SessionLocal()
    try:
        result = CorrelationService.run_correlation(session)
        print_correlation_report(session, result)
    finally:
        session.close()


if __name__ == "__main__":
    main()
