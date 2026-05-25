from __future__ import annotations
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import HealthResponse, ReadinessResponse, VersionResponse

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


@router.get("/api/version", response_model=VersionResponse)
def version(settings: Settings = Depends(get_settings)) -> VersionResponse:
    return VersionResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        revision=settings.deployment_revision,
        built_at=settings.deployment_built_at,
        dirty=settings.deployment_dirty,
    )
