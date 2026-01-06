"""Health check endpoint."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status."""
    from ... import __version__

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=__version__,
    )
