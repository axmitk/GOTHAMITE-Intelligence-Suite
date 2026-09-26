from typing import Literal
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("", status_code=status.HTTP_200_OK)
def export_intelligence(
    format: Literal["json", "csv"] = Query("json", description="Export format: json or csv"),
    db: Session = Depends(get_db),
):
    """
    Exports the active intelligence graph and evidence rows.
    Mandatory rule: Every evidence row includes artifact_id for complete audit provenance.
    """
    if format == "csv":
        csv_content = ExportService.export_csv(db)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gothamite_intel_export.csv"},
        )
    else:
        return ExportService.export_json(db)
