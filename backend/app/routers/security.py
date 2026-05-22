from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_security_actions_service, get_security_posture_service
from app.models import SecurityAction, SecurityActionHistoryResponse, SecurityActionRequest, SecurityPostureSummary
from app.oci_clients import OciClientError
from app.services.network_inventory import split_csv
from app.services.security_actions import SecurityActionsService
from app.services.security_posture import SecurityPostureService

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/posture", response_model=SecurityPostureSummary)
def security_posture(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    service: SecurityPostureService = Depends(get_security_posture_service),
) -> SecurityPostureSummary:
    try:
        return service.summarize(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            vcn_id=vcn_id,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.get("/finding-actions", response_model=SecurityActionHistoryResponse)
def list_finding_actions(
    service: SecurityActionsService = Depends(get_security_actions_service),
) -> SecurityActionHistoryResponse:
    return service.list_actions()


@router.post("/finding-actions", response_model=SecurityAction, status_code=status.HTTP_201_CREATED)
def record_finding_action(
    request: SecurityActionRequest,
    service: SecurityActionsService = Depends(get_security_actions_service),
) -> SecurityAction:
    return service.record_action(request)

