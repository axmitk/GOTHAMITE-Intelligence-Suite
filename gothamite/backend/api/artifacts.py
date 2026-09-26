from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models.entities import Artifact

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


@router.get("/{artifact_id}", status_code=status.HTTP_200_OK)
def get_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """
    Provenance Endpoint: Returns the exact verbatim raw stored artifact.
    This enables investigators to inspect the immutable ground-truth source of any observation.
    """
    artifact = db.query(Artifact).filter_by(artifact_id=artifact_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact with ID '{artifact_id}' not found in evidence locker",
        )

    return {
        "artifact_id": artifact.artifact_id,
        "source_id": artifact.source_id,
        "url": artifact.url,
        "content_hash": artifact.content_hash,
        "collected_at": artifact.collected_at.isoformat() if artifact.collected_at else None,
        "relay_path": artifact.relay_path,
        "raw_content": artifact.raw_content,
    }
