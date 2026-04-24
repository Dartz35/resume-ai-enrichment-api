"""
Health-check endpoint — no auth, no rate limiting.
Used by load balancers and uptime monitors.
"""

from fastapi import APIRouter

from models.schemas import HealthResponse

router = APIRouter()

API_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse, tags=["Meta"])
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version=API_VERSION)
