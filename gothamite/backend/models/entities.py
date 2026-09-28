import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship as orm_relationship
from backend.db import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Source(Base):
    """Dark-web marketplace or forum source (a synthetic fixture in this prototype)."""
    __tablename__ = "sources"

    source_id = Column(String(64), primary_key=True)  # e.g., 'forum-alpha'
    type = Column(String(32), nullable=False)  # 'forum' | 'marketplace'
    reliability = Column(String(32), nullable=False, default="medium")  # 'high' | 'medium' | 'low'
    last_scan = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="up")  # 'up' | 'down'

    artifacts = orm_relationship("Artifact", back_populates="source", cascade="all, delete-orphan")
    personas = orm_relationship("Persona", back_populates="source", cascade="all, delete-orphan")


class Artifact(Base):
    """Raw scraped content stored verbatim with hash verification. Immutable evidence locker."""
    __tablename__ = "artifacts"

    artifact_id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(64), ForeignKey("sources.source_id"), nullable=False)
    url = Column(String(512), nullable=False)
    raw_content = Column(Text, nullable=False)
    content_hash = Column(String(128), nullable=False, index=True)
    collected_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    relay_path = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("source_id", "content_hash", name="uq_artifact_source_hash"),
    )

    source = orm_relationship("Source", back_populates="artifacts")
    identifiers = orm_relationship("Identifier", back_populates="artifact", cascade="all, delete-orphan")
    evidence_items = orm_relationship("Evidence", back_populates="artifact", cascade="all, delete-orphan")


class Persona(Base):
    """A threat persona observed on a specific site (per-site identity)."""
    __tablename__ = "personas"

    persona_id = Column(String(36), primary_key=True, default=generate_uuid)
    handle = Column(String(128), nullable=False)
    source_id = Column(String(64), ForeignKey("sources.source_id"), nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    post_count = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("handle", "source_id", name="uq_persona_handle_source"),
    )

    source = orm_relationship("Source", back_populates="personas")
    identifiers = orm_relationship("Identifier", back_populates="persona", cascade="all, delete-orphan")


class Identifier(Base):
    """Digital identifier extracted from an artifact and tied to a persona."""
    __tablename__ = "identifiers"

    identifier_id = Column(String(36), primary_key=True, default=generate_uuid)
    type = Column(String(32), nullable=False)  # 'pgp_fingerprint' | 'wallet' | 'handle' | 'contact'
    value = Column(String(256), nullable=False, index=True)
    persona_id = Column(String(36), ForeignKey("personas.persona_id"), nullable=False)
    artifact_id = Column(String(36), ForeignKey("artifacts.artifact_id"), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)

    persona = orm_relationship("Persona", back_populates="identifiers")
    artifact = orm_relationship("Artifact", back_populates="identifiers")


class Relationship(Base):
    """Inferred linkage between two personas across sources."""
    __tablename__ = "relationships"

    relationship_id = Column(String(36), primary_key=True, default=generate_uuid)
    from_persona_id = Column(String(36), ForeignKey("personas.persona_id"), nullable=False)
    to_persona_id = Column(String(36), ForeignKey("personas.persona_id"), nullable=False)
    type = Column(String(32), nullable=False, default="same_actor_suspected")  # 'same_actor_suspected' | 'transacted_with' | 'trusts'
    score = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="proposed")  # 'proposed' | 'confirmed' | 'rejected'
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("from_persona_id", "to_persona_id", "type", name="uq_relationship_pair_type"),
    )

    from_persona = orm_relationship("Persona", foreign_keys=[from_persona_id])
    to_persona = orm_relationship("Persona", foreign_keys=[to_persona_id])
    evidence = orm_relationship("Evidence", back_populates="relationship", cascade="all, delete-orphan")


class Evidence(Base):
    """Specific supporting or contradicting signal justifying a relationship."""
    __tablename__ = "evidence"

    evidence_id = Column(String(36), primary_key=True, default=generate_uuid)
    relationship_id = Column(String(36), ForeignKey("relationships.relationship_id"), nullable=False)
    signal_type = Column(String(32), nullable=False)  # 'shared_pgp' | 'shared_wallet' | 'handle_similarity' | 'temporal_succession' | 'activity_overlap_conflict'
    direction = Column(String(32), nullable=False)  # 'supporting' | 'contradicting'
    weight = Column(Float, nullable=False)
    artifact_id = Column(String(36), ForeignKey("artifacts.artifact_id"), nullable=False)
    note = Column(Text, nullable=False)

    relationship = orm_relationship("Relationship", back_populates="evidence")
    artifact = orm_relationship("Artifact", back_populates="evidence_items")


class Actor(Base):
    """Analyst-confirmed cluster of personas representing a unified actor entity."""
    __tablename__ = "actors"

    actor_id = Column(String(36), primary_key=True, default=generate_uuid)
    label = Column(String(128), nullable=False)
    persona_ids = Column(JSON, nullable=False, default=list)
    confidence = Column(String(32), nullable=False, default="medium")  # 'low' | 'medium' | 'high'
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
