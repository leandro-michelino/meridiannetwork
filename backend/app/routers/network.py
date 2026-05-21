from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_network_inventory_service, get_route_analysis_service
from app.models import (
    GatewaySummary,
    NetworkSecurityGroupSummary,
    RouteIssueSummary,
    RouteTableSummary,
    SecurityListSummary,
    SubnetSummary,
    TopologyGraph,
    VcnSummary,
)
from app.oci_clients import OciClientError
from app.services.network_inventory import NetworkInventoryService, split_csv
from app.services.route_analysis import RouteAnalysisService

router = APIRouter(prefix="/api", tags=["network"])


@router.get("/vcns", response_model=list[VcnSummary])
def vcns(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
) -> list[VcnSummary]:
    try:
        return service.list_vcns(regions=split_csv(regions), compartment_ids=split_csv(compartment_ids))
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.get("/subnets", response_model=list[SubnetSummary])
def subnets(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
) -> list[SubnetSummary]:
    try:
        return service.list_subnets(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            vcn_id=vcn_id,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.get("/gateways", response_model=list[GatewaySummary])
def gateways(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
) -> list[GatewaySummary]:
    try:
        return service.list_gateways(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            vcn_id=vcn_id,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.get("/route-tables", response_model=list[RouteTableSummary])
def route_tables(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
) -> list[RouteTableSummary]:
    try:
        return service.list_route_tables(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            vcn_id=vcn_id,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.get("/route-issues", response_model=RouteIssueSummary)
def route_issues(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    service: RouteAnalysisService = Depends(get_route_analysis_service),
) -> RouteIssueSummary:
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


@router.get("/security-lists", response_model=list[SecurityListSummary])
def security_lists(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
) -> list[SecurityListSummary]:
    try:
        return service.list_security_lists(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            vcn_id=vcn_id,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.get("/network-security-groups", response_model=list[NetworkSecurityGroupSummary])
def network_security_groups(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
) -> list[NetworkSecurityGroupSummary]:
    try:
        return service.list_network_security_groups(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            vcn_id=vcn_id,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


@router.get("/topology", response_model=TopologyGraph)
def topology(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
) -> TopologyGraph:
    try:
        return service.get_topology(
            regions=split_csv(regions),
            compartment_ids=split_csv(compartment_ids),
            vcn_id=vcn_id,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc
