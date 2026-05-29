from __future__ import annotations

from ipaddress import AddressValueError, NetmaskValueError

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_connectivity_service
from app.models import ConnectivityCheckRequest, ConnectivityCheckResponse
from app.oci_clients import OciClientError
from app.services.connectivity import ConnectivityService

router = APIRouter(prefix="/api/connectivity", tags=["connectivity"])


@router.post("/check", response_model=ConnectivityCheckResponse)
def check_connectivity(
    request: ConnectivityCheckRequest,
    service: ConnectivityService = Depends(get_connectivity_service),
) -> ConnectivityCheckResponse:
    try:
        return service.check(request)
    except (AddressValueError, NetmaskValueError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_CONNECTIVITY_CHECK", "message": str(exc)},
        ) from exc
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc
