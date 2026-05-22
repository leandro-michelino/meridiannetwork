from __future__ import annotations
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.dependencies import get_network_inventory_service, get_region_service, get_security_posture_service
from app.services.network_inventory import NetworkInventoryService, split_csv
from app.services.regions import RegionService
from app.services.security_posture import SecurityPostureService

router = APIRouter(prefix="/api/export", tags=["export"])


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _csv_response(rows: list[list[str]], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/security-posture.csv")
def export_security_posture_csv(
    regions: str | None = Query(default=None),
    compartment_ids: str | None = Query(default=None),
    vcn_id: str | None = Query(default=None),
    service: SecurityPostureService = Depends(get_security_posture_service),
) -> StreamingResponse:
    summary = service.summarize(
        regions=split_csv(regions),
        compartment_ids=split_csv(compartment_ids),
        vcn_id=vcn_id,
    )
    rows: list[list[str]] = [
        ["severity", "rule_type", "resource_name", "region", "compartment_id", "vcn_id", "description", "recommendation"],
    ]
    for f in summary.findings:
        rows.append([
            f.severity, f.rule_type, f.resource_name,
            f.region, f.compartment_id, f.vcn_id,
            f.description, f.recommendation,
        ])
    return _csv_response(rows, f"meridian-security-posture-{_now()}.csv")


@router.get("/inventory.csv")
def export_inventory_csv(
    regions: str | None = Query(default=None),
    compartment_ids: str | None = Query(default=None),
    vcn_id: str | None = Query(default=None),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
) -> StreamingResponse:
    selected_regions = split_csv(regions)
    selected_compartments = split_csv(compartment_ids)

    vcns = service.list_vcns(regions=selected_regions, compartment_ids=selected_compartments)
    subnets = service.list_subnets(regions=selected_regions, compartment_ids=selected_compartments, vcn_id=vcn_id)
    gateways = service.list_gateways(regions=selected_regions, compartment_ids=selected_compartments, vcn_id=vcn_id)

    rows: list[list[str]] = [["resource_type", "name", "id", "region", "compartment_id", "vcn_id", "lifecycle_state", "detail"]]

    for v in vcns:
        rows.append(["vcn", v.name, v.id, v.region, v.compartment_id, "", v.lifecycle_state or "", ",".join(v.cidr_blocks)])

    for s in subnets:
        rows.append(["subnet", s.name, s.id, s.region, s.compartment_id, s.vcn_id, s.lifecycle_state or "", s.cidr_block])

    for g in gateways:
        rows.append(["gateway", g.name, g.id, g.region, g.compartment_id, g.vcn_id or "", g.lifecycle_state or "", g.gateway_type])

    return _csv_response(rows, f"meridian-inventory-{_now()}.csv")


@router.get("/completeness.csv")
def export_completeness_csv(
    regions: str | None = Query(default=None),
    compartment_ids: str | None = Query(default=None),
    vcn_id: str | None = Query(default=None),
    service: NetworkInventoryService = Depends(get_network_inventory_service),
    region_service: RegionService = Depends(get_region_service),
) -> StreamingResponse:
    selected_regions = split_csv(regions) or [region.id for region in region_service.list_active()]
    selected_compartments = split_csv(compartment_ids)
    service.reset_collection_issues()

    vcns = service.list_vcns(regions=selected_regions, compartment_ids=selected_compartments)
    subnets = service.list_subnets(regions=selected_regions, compartment_ids=selected_compartments, vcn_id=vcn_id)
    gateways = service.list_gateways(regions=selected_regions, compartment_ids=selected_compartments, vcn_id=vcn_id)
    route_tables = service.list_route_tables(regions=selected_regions, compartment_ids=selected_compartments, vcn_id=vcn_id)
    security_lists = service.list_security_lists(regions=selected_regions, compartment_ids=selected_compartments, vcn_id=vcn_id)
    network_security_groups = service.list_network_security_groups(
        regions=selected_regions,
        compartment_ids=selected_compartments,
        vcn_id=vcn_id,
    )
    issues = service.collection_issues()
    subscribed_regions = {region.id for region in region_service.list_active()}

    rows: list[list[str]] = [[
        "region",
        "subscribed",
        "requested",
        "status",
        "completed",
        "pending",
        "failed",
        "vcn_count",
        "subnet_count",
        "gateway_count",
        "route_table_count",
        "security_list_count",
        "network_security_group_count",
        "warning_count",
        "warning_types",
        "zero_resources",
        "last_updated",
    ]]
    for region in selected_regions:
        counts = {
            "vcns": _count_region(vcns, region),
            "subnets": _count_region(subnets, region),
            "gateways": _count_region(gateways, region),
            "route_tables": _count_region(route_tables, region),
            "security_lists": _count_region(security_lists, region),
            "network_security_groups": _count_region(network_security_groups, region),
        }
        region_issues = [issue for issue in issues if issue.get("region") in {region, "*"}]
        warning_types = sorted({issue.get("resource_type", "*") for issue in region_issues})
        has_resources = any(counts.values())
        status = "ready_with_warnings" if region_issues else "ready" if has_resources else "no_resources"
        rows.append([
            region,
            str(region in subscribed_regions).lower(),
            "true",
            status,
            "true",
            "false",
            "false",
            str(counts["vcns"]),
            str(counts["subnets"]),
            str(counts["gateways"]),
            str(counts["route_tables"]),
            str(counts["security_lists"]),
            str(counts["network_security_groups"]),
            str(len(region_issues)),
            ";".join(warning_types),
            str(not has_resources).lower(),
            datetime.now(timezone.utc).isoformat(),
        ])

    return _csv_response(rows, f"meridian-completeness-{_now()}.csv")


def _count_region(items: list[object], region: str) -> int:
    return sum(1 for item in items if getattr(item, "region", None) == region)
