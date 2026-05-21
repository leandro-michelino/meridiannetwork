from fastapi import APIRouter, Depends

from app.dependencies import get_preflight_service
from app.models import PreflightSummary
from app.services.preflight import PreflightService

router = APIRouter(prefix="/api", tags=["preflight"])


@router.get("/preflight", response_model=PreflightSummary)
def preflight(service: PreflightService = Depends(get_preflight_service)) -> PreflightSummary:
    return service.summarize()
