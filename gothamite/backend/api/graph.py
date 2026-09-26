from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["Graph"])


class UpdateEdgeStatusRequest(BaseModel):
    status: Literal["confirmed", "rejected", "proposed"]


@router.get("", status_code=status.HTTP_200_OK)
def get_graph(db: Session = Depends(get_db)):
    """
    Returns nodes and edges of the current intelligence graph.
    Stateless NetworkX reconstruction. Edges marked 'rejected' are excluded.
    """
    return GraphService.get_graph_payload(db)


@router.get("/edge/{relationship_id}", status_code=status.HTTP_200_OK)
def get_edge(relationship_id: str, db: Session = Depends(get_db)):
    """
    Retrieves complete evidence rows and source artifact IDs for a specific graph edge.
    """
    edge_details = GraphService.get_edge_details(db, relationship_id)
    if not edge_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge with ID '{relationship_id}' not found",
        )
    return edge_details


@router.patch("/edge/{relationship_id}", status_code=status.HTTP_200_OK)
def update_edge(
    relationship_id: str,
    payload: UpdateEdgeStatusRequest,
    db: Session = Depends(get_db),
):
    """
    Analyst review action: updates link status to 'confirmed' or 'rejected'.
    Rejected edges immediately disappear from /graph.
    """
    updated_edge = GraphService.update_edge_status(db, relationship_id, payload.status)
    if not updated_edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge with ID '{relationship_id}' not found",
        )
    return updated_edge
