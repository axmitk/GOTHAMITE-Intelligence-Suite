import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from backend.models.entities import Source, Artifact, Persona, Identifier


def ensure_utc(dt: datetime) -> datetime:
    """Ensures datetime is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_sha256(content: str) -> str:
    """Computes canonical sha256:<hex> digest for utf-8 encoded string."""
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def normalize_hash(h: str) -> str:
    """Normalizes content hash to sha256:<hex> lowercase format."""
    clean = h.strip().lower()
    if not clean.startswith("sha256:"):
        return f"sha256:{clean}"
    return clean


def normalize_pgp_fingerprint(pgp: str) -> str:
    """Normalizes PGP fingerprint: uppercase, all whitespace stripped."""
    clean = "".join(pgp.split()).upper()
    if len(clean) != 40 or not all(c in "0123456789ABCDEF" for c in clean):
        raise ValueError(f"invalid pgp fingerprint format: must be 40 hex characters")
    return clean


class IngestService:
    @staticmethod
    def process_ingest(
        db: Session,
        source_id: str,
        source_type: str,
        url: str,
        collected_at: datetime,
        relay_path: List[str],
        raw_content: str,
        content_hash: str,
        persona_handle: str,
        persona_observed_at: datetime,
        identifiers_data: List[dict],
    ) -> Tuple[int, dict]:
        """
        Processes and persists a single raw artifact observation.
        
        Strict rules:
        1. Verifies SHA-256 hash against verbatim raw_content.
        2. Deduplicates on (source_id, content_hash) returning 200 without second artifact.
        3. Persists Artifact first (verbatim raw_content), then upserts Persona, then persists Identifiers.
        4. NEVER creates relationships or runs scoring.
        """
        # 1. Recompute and verify SHA-256 hash
        expected_hash = compute_sha256(raw_content)
        normalized_given_hash = normalize_hash(content_hash)
        if expected_hash != normalized_given_hash:
            raise ValueError(
                f"content_hash mismatch: expected {expected_hash}, received {normalized_given_hash}"
            )

        # 2. Deduplication check on (source_id, content_hash)
        existing_artifact = (
            db.query(Artifact)
            .filter_by(source_id=source_id, content_hash=expected_hash)
            .first()
        )
        if existing_artifact:
            return 200, {
                "accepted": False,
                "reason": "duplicate_content_hash",
                "artifact_id": existing_artifact.artifact_id,
            }

        # 3. Ensure source entry exists
        source = db.query(Source).filter_by(source_id=source_id).first()
        if not source:
            source = Source(
                source_id=source_id,
                type=source_type,
                reliability="medium",
                status="up",
                last_scan=collected_at,
            )
            db.add(source)
            db.flush()
        else:
            source.last_scan = collected_at
            db.flush()

        # 4. Persist Artifact FIRST (verbatim raw_content, immutable)
        artifact_id = str(uuid.uuid4())
        artifact = Artifact(
            artifact_id=artifact_id,
            source_id=source_id,
            url=url,
            raw_content=raw_content,  # verbatim unmodified text
            content_hash=expected_hash,
            collected_at=collected_at,
            relay_path=relay_path,
        )
        db.add(artifact)
        db.flush()

        # 5. Upsert Persona (widen observation window if already exists)
        persona = (
            db.query(Persona)
            .filter_by(handle=persona_handle, source_id=source_id)
            .first()
        )
        obs_utc = ensure_utc(persona_observed_at)

        if not persona:
            persona_id = str(uuid.uuid4())
            persona = Persona(
                persona_id=persona_id,
                handle=persona_handle,
                source_id=source_id,
                first_seen=obs_utc,
                last_seen=obs_utc,
                post_count=1,
            )
            db.add(persona)
            db.flush()
        else:
            curr_first = ensure_utc(persona.first_seen)
            curr_last = ensure_utc(persona.last_seen)
            if obs_utc < curr_first:
                persona.first_seen = obs_utc
            if obs_utc > curr_last:
                persona.last_seen = obs_utc
            persona.post_count += 1
            db.flush()

        # 6. Persist Identifiers (each linked to persona_id AND artifact_id)
        # Note: Same identifier from two artifacts -> two rows, both retained (provenance)
        stored_count = 0
        for ident in identifiers_data:
            itype = ident["type"]
            raw_val = ident["value"]
            iobs = ensure_utc(ident.get("observed_at", persona_observed_at))

            if itype == "pgp_fingerprint":
                val = normalize_pgp_fingerprint(raw_val)
            else:
                val = raw_val.strip()

            identifier_record = Identifier(
                identifier_id=str(uuid.uuid4()),
                type=itype,
                value=val,
                persona_id=persona.persona_id,
                artifact_id=artifact.artifact_id,
                observed_at=iobs,
            )
            db.add(identifier_record)
            stored_count += 1

        # Commit all changes atomically
        db.commit()

        return 202, {
            "accepted": True,
            "artifact_id": artifact.artifact_id,
            "identifiers_stored": stored_count,
        }
