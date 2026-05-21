from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
def healthz(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        status="ok",
    )


@router.get("/readyz", response_model=ReadinessResponse)
def readyz(settings: Settings = Depends(get_settings)) -> ReadinessResponse:
    tenancy_configured = bool(settings.tenancy_ocid)
    live_ready = not settings.enable_live_oci or tenancy_configured
    return ReadinessResponse(
        service=settings.app_name,
        status="ready" if live_ready else "degraded",
        live_oci_enabled=settings.enable_live_oci,
        tenancy_configured=tenancy_configured,
        auth_mode=settings.oci_auth,
    )

