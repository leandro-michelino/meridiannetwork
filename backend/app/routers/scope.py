from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_compartment_service, get_region_service
from app.models import CompartmentSummary, RegionSummary
from app.oci_clients import OciClientError
from app.services.compartments import CompartmentService
from app.services.regions import RegionService

router = APIRouter(prefix="/api", tags=["scope"])


@router.get("/regions/available", response_model=list[RegionSummary])
def available_regions(service: RegionService = Depends(get_region_service)) -> list[RegionSummary]:
    return service.list_available()


@router.get("/regions/active", response_model=list[RegionSummary])
def active_regions(service: RegionService = Depends(get_region_service)) -> list[RegionSummary]:
    return [region for region in service.list_available() if region.is_active]


@router.get("/compartments", response_model=list[CompartmentSummary])
def compartments(service: CompartmentService = Depends(get_compartment_service)) -> list[CompartmentSummary]:
    try:
        return service.list_compartments()
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc

