from __future__ import annotations
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.dependencies import get_network_inventory_service, get_security_posture_service
from app.services.network_inventory import NetworkInventoryService, split_csv
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
