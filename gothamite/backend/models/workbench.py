"""Additive investigation schema; legacy persona evidence remains untouched."""
from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, JSON, UniqueConstraint
from backend.db import Base


class IntelEntity(Base):
    __tablename__ = "wb_entities"
    id = Column(String(80), primary_key=True)
    kind = Column(String(32), nullable=False, index=True)
    label = Column(String(512), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    source = Column(String(80), nullable=False)
    confidence = Column(Float, nullable=False)
    first_seen = Column(String(32), nullable=False)
    last_seen = Column(String(32), nullable=False)
    attributes = Column(JSON, nullable=False, default=dict)
    provenance = Column(String(24), nullable=False, default="synthetic")


class IntelEvidence(Base):
    __tablename__ = "wb_evidence"
    id = Column(String(80), primary_key=True)
    title = Column(String(240), nullable=False)
    kind = Column(String(32), nullable=False, index=True)
    source = Column(String(80), nullable=False)
    observed_at = Column(String(32), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False)
    provenance = Column(String(24), nullable=False, default="synthetic")


class EvidenceEntity(Base):
    __tablename__ = "wb_evidence_entities"
    evidence_id = Column(String(80), ForeignKey("wb_evidence.id"), primary_key=True)
    entity_id = Column(String(80), ForeignKey("wb_entities.id"), primary_key=True)


class IntelRelationship(Base):
    __tablename__ = "wb_relationships"
    id = Column(String(160), primary_key=True)
    source_id = Column(String(80), ForeignKey("wb_entities.id"), nullable=False, index=True)
    target_id = Column(String(80), ForeignKey("wb_entities.id"), nullable=False, index=True)
    relation = Column(String(32), nullable=False)
    evidence_id = Column(String(80), ForeignKey("wb_evidence.id"), nullable=False)
    confidence = Column(Float, nullable=False)


class IncidentCase(Base):
    __tablename__ = "wb_cases"
    id = Column(String(80), ForeignKey("wb_entities.id"), primary_key=True)
    status = Column(String(32), nullable=False, default="NEW")
    severity = Column(String(24), nullable=False)
    analyst = Column(String(80), nullable=False, default="Demo analyst")
    created_at = Column(String(32), nullable=False)
    updated_at = Column(String(32), nullable=False)
    version = Column(Integer, nullable=False, default=1)


class CaseNote(Base):
    __tablename__ = "wb_notes"
    id = Column(String(36), primary_key=True)
    case_id = Column(String(80), ForeignKey("wb_cases.id"), nullable=False, index=True)
    kind = Column(String(24), nullable=False)
    text = Column(Text, nullable=False)
    author = Column(String(80), nullable=False)
    created_at = Column(String(32), nullable=False)


class ResponseAction(Base):
    __tablename__ = "wb_actions"
    id = Column(String(100), primary_key=True)
    case_id = Column(String(80), ForeignKey("wb_cases.id"), nullable=False, index=True)
    rule = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    decision_note = Column(Text, nullable=False, default="")
    decided_by = Column(String(80), nullable=True)
    decided_at = Column(String(32), nullable=True)
    __table_args__ = (UniqueConstraint("case_id", "rule"),)


class AuditEvent(Base):
    __tablename__ = "wb_audit"
    id = Column(String(36), primary_key=True)
    case_id = Column(String(80), ForeignKey("wb_cases.id"), nullable=False, index=True)
    actor = Column(String(80), nullable=False)
    action = Column(String(64), nullable=False)
    detail = Column(Text, nullable=False)
    created_at = Column(String(32), nullable=False)


class DatasetRecord(Base):
    """Full provenance for a dataset-derived entity, evidence row or relationship.

    Synthetic seed records have no row here. ``provenance`` on the entity or
    evidence row says which class it is; this table says exactly where it came
    from and how it was transformed.
    """
    __tablename__ = "wb_dataset_records"
    record_type = Column(String(16), primary_key=True)  # entity | evidence | relationship
    record_id = Column(String(160), primary_key=True)
    provenance_class = Column(String(24), nullable=False)  # dataset_derived | reference_derived
    dataset = Column(String(64), nullable=False, index=True)
    dataset_name = Column(String(160), nullable=False)
    dataset_version = Column(String(80), nullable=False)
    license = Column(String(80), nullable=False)
    source_url = Column(String(240), nullable=False)
    doi = Column(String(80), nullable=True)
    source_record_id = Column(String(160), nullable=False)
    transformation_version = Column(String(40), nullable=False)
    imported_at = Column(String(32), nullable=False)
    details = Column(JSON, nullable=False, default=dict)
