from __future__ import annotations

from ipaddress import AddressValueError, NetmaskValueError

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_traffic_telemetry_service
from app.models import TrafficEnableRequest, TrafficEnablementResponse, TrafficFlowSummary, TrafficTelemetryStatus
from app.oci_clients import OciClientError
from app.services.network_inventory import split_csv
from app.services.traffic_telemetry import TrafficTelemetryService

router = APIRouter(prefix="/api/traffic", tags=["traffic"])


@router.get("/telemetry/status", response_model=TrafficTelemetryStatus)
def traffic_telemetry_status(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    check_vcns: bool = Query(default=False, description="Perform the slower VCN Flow Log coverage check."),
    service: TrafficTelemetryService = Depends(get_traffic_telemetry_service),
) -> TrafficTelemetryStatus:
    try:
        return service.status(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            vcn_id=vcn_id,
            check_vcns=check_vcns,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.post("/telemetry/enable", response_model=TrafficEnablementResponse)
def enable_traffic_telemetry(
    request: TrafficEnableRequest,
    service: TrafficTelemetryService = Depends(get_traffic_telemetry_service),
) -> TrafficEnablementResponse:
    try:
        return service.enable(request)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "TRAFFIC_ENABLEMENT_DISABLED", "message": str(exc)},
        ) from exc
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.post("/telemetry/disable", response_model=TrafficEnablementResponse)
def disable_traffic_telemetry(
    request: TrafficEnableRequest,
    service: TrafficTelemetryService = Depends(get_traffic_telemetry_service),
) -> TrafficEnablementResponse:
    try:
        return service.disable(request)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "TRAFFIC_ENABLEMENT_DISABLED", "message": str(exc)},
        ) from exc
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.get("/flows", response_model=TrafficFlowSummary)
def traffic_flows(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    source_ip: str | None = Query(default=None, description="Optional source private IP filter."),
    destination_ip: str | None = Query(default=None, description="Optional destination private IP filter."),
    port: int | None = Query(default=None, ge=1, le=65535, description="Optional destination port filter."),
    action: str | None = Query(default=None, pattern="^(ACCEPT|REJECT|accept|reject)$"),
    lookback_minutes: int | None = Query(default=None, ge=1, le=1440),
    limit: int | None = Query(default=None, ge=1, le=500),
    service: TrafficTelemetryService = Depends(get_traffic_telemetry_service),
) -> TrafficFlowSummary:
    try:
        return service.list_flows(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            source_ip=source_ip,
            destination_ip=destination_ip,
            port=port,
            action=action,
            lookback_minutes=lookback_minutes,
            limit=limit,
        )
    except (AddressValueError, NetmaskValueError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_TRAFFIC_FILTER", "message": str(exc)},
        ) from exc
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc
