import re
from datetime import datetime
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.services.ingest_service import IngestService

router = APIRouter(tags=["Ingest"])

BASE58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
KNOWN_SOURCES = {"forum-alpha", "marketplace-beta", "forum-gamma", "forum-delta", "marketplace-epsilon", "forum-zeta", "marketplace-omega", "mock_leaky_service"}
MAX_CONTENT_BYTES = 1024 * 1024  # 1 MB ceiling


class PersonaPayload(BaseModel):
    handle: str = Field(..., min_length=1, max_length=128)
    observed_at: datetime

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("handle cannot be empty")
        for char in v:
            if ord(char) < 32:
                raise ValueError("handle contains invalid control characters")
        return v.strip()


class IdentifierPayload(BaseModel):
    type: Literal["pgp_fingerprint", "wallet", "handle", "contact"]
    value: str = Field(..., min_length=1, max_length=256)
    observed_at: datetime

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str, info) -> str:
        itype = info.data.get("type")
        if itype == "pgp_fingerprint":
            clean = "".join(v.split()).upper()
            if len(clean) != 40 or not all(c in "0123456789ABCDEF" for c in clean):
                raise ValueError("invalid pgp fingerprint format: must be 40 hex characters")
            return clean
        elif itype == "wallet":
            stripped = v.strip()
            if len(stripped) < 26 or len(stripped) > 95:
                raise ValueError(f"invalid wallet address length: {len(stripped)}")
            if not set(stripped).issubset(BASE58_ALPHABET):
                raise ValueError("invalid cryptocurrency wallet address: not base58 encoded")
            return stripped
        return v.strip()


class IngestRequest(BaseModel):
    source_id: str
    source_type: Literal["forum", "marketplace"]
    url: str = Field(..., min_length=1, max_length=512)
    collected_at: datetime
    relay_path: List[str] = Field(..., min_length=1)
    raw_content: str
    content_hash: str
    persona: PersonaPayload
    identifiers: List[IdentifierPayload] = Field(default_factory=list)

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        if v not in KNOWN_SOURCES:
            raise ValueError(f"unknown source_id '{v}': must be one of {sorted(KNOWN_SOURCES)}")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if ".onion.mock" not in v:
            raise ValueError("url must target a valid .onion.mock host")
        return v

    @field_validator("raw_content")
    @classmethod
    def validate_content_size(cls, v: str) -> str:
        byte_len = len(v.encode("utf-8"))
        if byte_len > MAX_CONTENT_BYTES:
            raise ValueError(f"raw_content exceeds 1 MB ceiling ({byte_len} bytes)")
        return v


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_artifact(
    payload: IngestRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Ingests a raw scraped page artifact, upserts its persona, and persists extracted identifiers.
    Idempotent and strictly creates NO relationships.
    """
    try:
        identifiers_dicts = [i.model_dump() for i in payload.identifiers]
        status_code, result = IngestService.process_ingest(
            db=db,
            source_id=payload.source_id,
            source_type=payload.source_type,
            url=payload.url,
            collected_at=payload.collected_at,
            relay_path=payload.relay_path,
            raw_content=payload.raw_content,
            content_hash=payload.content_hash,
            persona_handle=payload.persona.handle,
            persona_observed_at=payload.persona.observed_at,
            identifiers_data=identifiers_dicts,
        )
        response.status_code = status_code
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"accepted": False, "errors": [str(e)]},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"accepted": False, "errors": [str(e)]},
        )
