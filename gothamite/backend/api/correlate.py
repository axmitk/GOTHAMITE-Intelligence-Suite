from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.services.correlation_service import CorrelationService

router = APIRouter(tags=["Correlation"])


@router.post("/correlate", status_code=status.HTTP_200_OK)
def trigger_correlation(db: Session = Depends(get_db)):
    """
    Triggers an idempotent deterministic batch correlation pass over stored observations.
    Computes cross-source persona linkages, applies contradiction-aware scoring, and outputs evidence rows.
    """
    result = CorrelationService.run_correlation(db)
    return result
