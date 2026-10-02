import uuid
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
import Levenshtein
from sqlalchemy.orm import Session

from backend.models.entities import Persona, Identifier, Relationship, Evidence, Artifact

LEXICAL_WEIGHT = 0.0  # was 0.25; see docs/scoring_rationale.md


def ensure_utc(dt: datetime) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class CorrelationService:
    @classmethod
    def run_correlation(cls, db: Session) -> Dict:
        """
        Executes a complete deterministic batch correlation pass over all stored personas and identifiers.
        
        Rules:
        1. Evaluates all cross-source persona pairs (P.source_id != Q.source_id).
        2. Exact-match signals (PGP: +0.70, Wallet: +0.25, Succession: +0.15, Handle: +0.05, Overlap: -0.30)
           A lexical signal exists but is weighted 0 (off) until real stylometry is built.
           Weights are hand-set priors; see docs/scoring_rationale.md.
        3. Clamps scores to [0.00, 0.95]. Emits edge only if score >= 0.30.
        4. Preserves analyst rejections (status == 'rejected' is never overwritten or recreated).
        5. Handles transaction references into separate 'transacted_with' edges (never promoted to identity).
        6. Idempotent: re-running produces identical relationships and evidence rows.
        """
        # Load all personas and group identifiers by persona
        personas = db.query(Persona).all()
        identifiers = db.query(Identifier).all()

        idents_by_persona: Dict[str, List[Identifier]] = {}
        for ident in identifiers:
            idents_by_persona.setdefault(ident.persona_id, []).append(ident)

        # Map wallet addresses to personas that own them
        wallet_to_personas: Dict[str, List[Persona]] = {}
        for ident in identifiers:
            if ident.type == "wallet":
                wallet_to_personas.setdefault(ident.value, []).append(ident.persona)

        evaluated_pairs_count = 0
        relationships_created = 0
        relationships_updated = 0
        rejected_skipped = 0
        active_edges_summary = []

        # 1. Evaluate cross-source persona pairs for 'same_actor_suspected'
        n = len(personas)
        for i in range(n):
            for j in range(i + 1, n):
                p1 = personas[i]
                p2 = personas[j]

                # Strict Rule: same-source persona pairs are NEVER compared
                if p1.source_id == p2.source_id:
                    continue

                evaluated_pairs_count += 1

                # Order direction deterministically (earlier first_seen -> later, or handle name)
                p1_first = ensure_utc(p1.first_seen)
                p2_first = ensure_utc(p2.first_seen)
                if p1_first <= p2_first:
                    source_p, target_p = p1, p2
                else:
                    source_p, target_p = p2, p1

                # Check if relationship already exists
                existing_rel = (
                    db.query(Relationship)
                    .filter(
                        Relationship.type == "same_actor_suspected",
                        (
                            (Relationship.from_persona_id == source_p.persona_id)
                            & (Relationship.to_persona_id == target_p.persona_id)
                        )
                        | (
                            (Relationship.from_persona_id == target_p.persona_id)
                            & (Relationship.to_persona_id == source_p.persona_id)
                        ),
                    )
                    .first()
                )

                # Analyst override check: rejected relationships are preserved and never recreated
                if existing_rel and existing_rel.status == "rejected":
                    rejected_skipped += 1
                    continue

                # Compute signals
                signals = cls._evaluate_signals(db, source_p, target_p, idents_by_persona)

                # Sum weights
                raw_score = sum(s["weight"] for s in signals)
                final_score = round(min(0.95, max(0.0, raw_score)), 2)

                # Edge threshold: create relationship only if score >= 0.30
                if final_score >= 0.30:
                    if existing_rel:
                        existing_rel.score = final_score
                        # Replace evidence rows cleanly
                        db.query(Evidence).filter_by(relationship_id=existing_rel.relationship_id).delete()
                        for s in signals:
                            ev = Evidence(
                                evidence_id=str(uuid.uuid4()),
                                relationship_id=existing_rel.relationship_id,
                                signal_type=s["signal_type"],
                                direction=s["direction"],
                                weight=s["weight"],
                                artifact_id=s["artifact_id"],
                                note=s["note"],
                            )
                            db.add(ev)
                        relationships_updated += 1
                        rel_id = existing_rel.relationship_id
                    else:
                        new_rel = Relationship(
                            relationship_id=str(uuid.uuid4()),
                            from_persona_id=source_p.persona_id,
                            to_persona_id=target_p.persona_id,
                            type="same_actor_suspected",
                            score=final_score,
                            status="proposed",
                        )
                        db.add(new_rel)
                        db.flush()
                        for s in signals:
                            ev = Evidence(
                                evidence_id=str(uuid.uuid4()),
                                relationship_id=new_rel.relationship_id,
                                signal_type=s["signal_type"],
                                direction=s["direction"],
                                weight=s["weight"],
                                artifact_id=s["artifact_id"],
                                note=s["note"],
                            )
                            db.add(ev)
                        relationships_created += 1
                        rel_id = new_rel.relationship_id

                    active_edges_summary.append({
                        "relationship_id": rel_id,
                        "from_handle": source_p.handle,
                        "to_handle": target_p.handle,
                        "type": "same_actor_suspected",
                        "score": final_score,
                        "signals": [s["signal_type"] for s in signals],
                    })
                else:
                    # If score dropped below threshold and was proposed, remove it
                    if existing_rel and existing_rel.status == "proposed":
                        db.delete(existing_rel)

        # 2. Evaluate 'transacted_with' interactions (separate track, never promoted to identity)
        for persona in personas:
            p_idents = idents_by_persona.get(persona.persona_id, [])
            for ident in p_idents:
                if ident.type == "contact" and ident.value.startswith("transacted_with_wallet:"):
                    target_wallet = ident.value.split(":", 1)[1]
                    recipient_personas = wallet_to_personas.get(target_wallet, [])
                    recipient_candidates = [
                        r for r in recipient_personas
                        if r.persona_id != persona.persona_id
                    ]
                    # If multiple personas share the wallet, prioritize the persona on the same source
                    same_source_recipients = [r for r in recipient_candidates if r.source_id == persona.source_id]
                    final_recipients = same_source_recipients if same_source_recipients else recipient_candidates

                    for recipient in final_recipients:

                        # Check if transaction edge already exists
                        existing_tx = (
                            db.query(Relationship)
                            .filter_by(
                                from_persona_id=persona.persona_id,
                                to_persona_id=recipient.persona_id,
                                type="transacted_with",
                            )
                            .first()
                        )

                        if existing_tx and existing_tx.status == "rejected":
                            rejected_skipped += 1
                            continue

                        if not existing_tx:
                            tx_rel = Relationship(
                                relationship_id=str(uuid.uuid4()),
                                from_persona_id=persona.persona_id,
                                to_persona_id=recipient.persona_id,
                                type="transacted_with",
                                score=0.0,
                                status="proposed",
                            )
                            db.add(tx_rel)
                            db.flush()

                            ev = Evidence(
                                evidence_id=str(uuid.uuid4()),
                                relationship_id=tx_rel.relationship_id,
                                signal_type="shared_wallet",
                                direction="supporting",
                                weight=0.0,
                                artifact_id=ident.artifact_id,
                                note=f"Transaction reference to wallet {target_wallet} owned by {recipient.handle}",
                            )
                            db.add(ev)
                            relationships_created += 1
                            rel_id = tx_rel.relationship_id
                        else:
                            rel_id = existing_tx.relationship_id

                        active_edges_summary.append({
                            "relationship_id": rel_id,
                            "from_handle": persona.handle,
                            "to_handle": recipient.handle,
                            "type": "transacted_with",
                            "score": 0.0,
                            "signals": ["transacted_wallet_reference"],
                        })

        db.commit()

        return {
            "status": "success",
            "evaluated_pairs": evaluated_pairs_count,
            "relationships_created": relationships_created,
            "relationships_updated": relationships_updated,
            "rejected_skipped": rejected_skipped,
            "active_relationships": len(active_edges_summary),
            "edges": active_edges_summary,
        }

    @classmethod
    def _evaluate_signals(
        cls,
        db: Session,
        p1: Persona,
        p2: Persona,
        idents_map: Dict[str, List[Identifier]],
    ) -> List[Dict]:
        """
        Evaluates the documented mathematical signal matrix between two personas.
        Returns a list of dicts with: signal_type, direction, weight, artifact_id, note.
        """
        signals = []
        p1_idents = idents_map.get(p1.persona_id, [])
        p2_idents = idents_map.get(p2.persona_id, [])

        p1_pgp = {i.value: i for i in p1_idents if i.type == "pgp_fingerprint"}
        p2_pgp = {i.value: i for i in p2_idents if i.type == "pgp_fingerprint"}

        p1_wallets = {i.value: i for i in p1_idents if i.type == "wallet"}
        p2_wallets = {i.value: i for i in p2_idents if i.type == "wallet"}

        # Signal 1: Shared PGP fingerprint (+0.70)
        shared_pgp_keys = set(p1_pgp.keys()) & set(p2_pgp.keys())
        has_shared_pgp = len(shared_pgp_keys) > 0
        for key in shared_pgp_keys:
            ident = p2_pgp[key]
            signals.append({
                "signal_type": "shared_pgp",
                "direction": "supporting",
                "weight": 0.70,
                "artifact_id": ident.artifact_id,
                "note": f"Identical normalized PGP fingerprint: {key}",
            })

        # Signal 2: Shared Cryptocurrency Wallet (+0.25)
        # Kept below the 0.30 edge threshold on purpose: the extractor records wallet
        # mentions, not ownership (escrow, mixers, scam-warning posts quoting an address),
        # so a shared wallet must be corroborated by at least one other signal.
        shared_wallets = set(p1_wallets.keys()) & set(p2_wallets.keys())
        for wallet in shared_wallets:
            ident = p2_wallets[wallet]
            signals.append({
                "signal_type": "shared_wallet",
                "direction": "supporting",
                "weight": 0.25,
                "artifact_id": ident.artifact_id,
                "note": f"Identical cryptocurrency wallet address: {wallet}",
            })

        # Signal 3: Temporal Succession (+0.15)
        # Condition: P1 last_seen < P2 first_seen, gap < 45 days (or vice versa)
        p1_first = ensure_utc(p1.first_seen)
        p1_last = ensure_utc(p1.last_seen)
        p2_first = ensure_utc(p2.first_seen)
        p2_last = ensure_utc(p2.last_seen)

        successor_artifact_id = p2_idents[0].artifact_id if p2_idents else (p1_idents[0].artifact_id if p1_idents else "")

        if p1_last < p2_first:
            gap_days = (p2_first - p1_last).days
            if gap_days < 45:
                signals.append({
                    "signal_type": "temporal_succession",
                    "direction": "supporting",
                    "weight": 0.15,
                    "artifact_id": successor_artifact_id,
                    "note": f"Temporal succession: {gap_days} days between {p1.handle} last seen and {p2.handle} first seen (< 45 days)",
                })
        elif p2_last < p1_first:
            gap_days = (p1_first - p2_last).days
            if gap_days < 45:
                signals.append({
                    "signal_type": "temporal_succession",
                    "direction": "supporting",
                    "weight": 0.15,
                    "artifact_id": successor_artifact_id,
                    "note": f"Temporal succession: {gap_days} days between {p2.handle} last seen and {p1.handle} first seen (< 45 days)",
                })

        # Signal 4: Handle Similarity (+0.05)
        # Applied when handles are close (distance <= 1, or distance <= 2 without shared PGP)
        dist = Levenshtein.distance(p1.handle.lower(), p2.handle.lower())
        if dist <= 1 or (dist <= 2 and not has_shared_pgp):
            signals.append({
                "signal_type": "handle_similarity",
                "direction": "supporting",
                "weight": 0.05,
                "artifact_id": successor_artifact_id,
                "note": f"Handle edit distance {dist} <= 2 between '{p1.handle}' and '{p2.handle}'",
            })

        # Signal 5: Activity Overlap Conflict (-0.30)
        # Condition: Windows overlap concurrently with no cryptographic identity verification
        overlap_start = max(p1_first, p2_first)
        overlap_end = min(p1_last, p2_last)
        if overlap_start <= overlap_end and not has_shared_pgp:
            signals.append({
                "signal_type": "activity_overlap_conflict",
                "direction": "contradicting",
                "weight": -0.30,
                "artifact_id": successor_artifact_id,
                "note": f"Activity overlap conflict: concurrent activity between {overlap_start.strftime('%Y-%m-%d')} and {overlap_end.strftime('%Y-%m-%d')} with no cryptographic identity verification",
            })

        # Signal 6: Lexical similarity. Bag-of-words term-frequency cosine between the
        # first artifact of each persona. Deterministic; not a trained or AI model.
        # Weight 0 until a real stylometric model exists: on templated pages the cosine
        # is dominated by shared markup and does not separate true pairs from negatives.
        if LEXICAL_WEIGHT == 0:
            return signals
        try:
            from backend.services.stylometry import compute_stylometric_similarity
            from backend.models.entities import Artifact
            
            p1_art_ids = [i.artifact_id for i in p1_idents if i.artifact_id]
            p2_art_ids = [i.artifact_id for i in p2_idents if i.artifact_id]
            
            if p1_art_ids and p2_art_ids:
                a1 = db.query(Artifact).filter(Artifact.artifact_id == p1_art_ids[0]).first()
                a2 = db.query(Artifact).filter(Artifact.artifact_id == p2_art_ids[0]).first()
                
                if a1 and a2 and a1.raw_content and a2.raw_content:
                    similarity = compute_stylometric_similarity(a1.raw_content, a2.raw_content)
                    if similarity >= 0.85:
                        signals.append({
                            "signal_type": "lexical_similarity",
                            "direction": "supporting",
                            "weight": LEXICAL_WEIGHT,
                            "artifact_id": successor_artifact_id,
                            "note": f"Lexical similarity: term-frequency cosine {similarity:.2f} >= 0.85 threshold (bag-of-words; corroborating only).",
                        })
        except Exception as e:
            pass

        return signals
