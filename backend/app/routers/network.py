from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from threading import RLock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder

from app.dependencies import (
    get_compartment_service,
    get_network_inventory_service,
    get_region_service,
    get_route_analysis_service,
)
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
from app.services.regions import RegionService
from app.services.route_analysis import RouteAnalysisService
from app.services.security_posture import SecurityPostureService
from app.services.compartments import CompartmentService

router = APIRouter(prefix="/api", tags=["network"])
_dashboard_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="meridian-dashboard-collector")
_dashboard_lock = RLock()

_SnapshotKey = tuple[str, tuple[str, ...], str]
_dashboard_jobs: dict[_SnapshotKey, Future[dict[str, object]]] = {}
_dashboard_snapshots: dict[_SnapshotKey, tuple[float, dict[str, object]]] = {}


# ---------------------------------------------------------------------------
# Snapshot helper functions
# ---------------------------------------------------------------------------

def _snapshot_is_fresh(snapshot: dict[str, object], _now: float, network_inventory: NetworkInventoryService) -> bool:
    ttl = network_inventory.settings.inventory_snapshot_ttl_seconds
    collected_at = snapshot.get("collected_at")
    if not collected_at:
        return False
    try:
        ts = datetime.fromisoformat(str(collected_at))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age <= ttl
    except Exception:
        return False


def _snapshot_cache_file(network_inventory: NetworkInventoryService, key: _SnapshotKey) -> Path | None:
    snapshot_dir = network_inventory.settings.inventory_snapshot_dir
    if not snapshot_dir:
        return None
    region = key[0]
    key_hash = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:24]
    return Path(snapshot_dir) / f"snapshot_{region}_{key_hash}.json"


def _write_persistent_snapshot(
    network_inventory: NetworkInventoryService,
    key: _SnapshotKey,
    snapshot: dict[str, object],
) -> None:
    path = _snapshot_cache_file(network_inventory, key)
    if not path:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, default=str), encoding="utf-8")
    except Exception:
        pass


def _read_persistent_snapshot(
    network_inventory: NetworkInventoryService,
    key: _SnapshotKey,
) -> dict[str, object] | None:
    path = _snapshot_cache_file(network_inventory, key)
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _clear_dashboard_snapshot(network_inventory: NetworkInventoryService, key: _SnapshotKey) -> None:
    _dashboard_snapshots.pop(key, None)
    path = _snapshot_cache_file(network_inventory, key)
    if not path:
        return
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _failed_dashboard_snapshot(region: str, exc: Exception) -> dict[str, object]:
    error_msg = str(exc)[:500]
    now_iso = datetime.now(timezone.utc).isoformat()
    issue = {"region": region, "resource_type": "*", "compartment_id": "*", "message": error_msg}
    return {
        "vcns": [],
        "subnets": [],
        "gateways": [],
        "routeTables": [],
        "routeIssues": {
            "status": "ok",
            "total_issues": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0,
            "issues": [],
        },
        "securityLists": [],
        "networkSecurityGroups": [],
        "topology": {"nodes": [], "edges": []},
        "securityPosture": {
            "status": "ok",
            "risk_score": 0,
            "scanned_security_lists": 0,
            "scanned_network_security_groups": 0,
            "scanned_ingress_rules": 0,
            "scanned_egress_rules": 0,
            "total_findings": 0,
            "critical_findings": 0,
            "high_findings": 0,
            "medium_findings": 0,
            "low_findings": 0,
            "findings": [],
        },
        "collection": {
            "status": "failed",
            "requested_regions": [region],
            "completed_regions": [],
            "pending_regions": [],
            "issues": [issue],
            "regions": [{
                "id": region,
                "status": "failed",
                "issues": [issue],
                "resource_counts": {},
                "error": error_msg,
                "last_updated": now_iso,
                "duration_seconds": None,
            }],
        },
        "collected_at": now_iso,
        "duration_seconds": None,
    }


def _start_region_collection_job(
    key: _SnapshotKey,
    region: str,
    selected_compartments: list[str],
    vcn_id: str | None,
    network_inventory: NetworkInventoryService,
    region_service: RegionService,
    compartment_service: CompartmentService,
) -> "Future[dict[str, object]]":
    def _collect() -> dict[str, object]:
        started = monotonic()
        try:
            snapshot = _build_dashboard_snapshot(
                selected_regions=[region],
                selected_compartments=selected_compartments,
                vcn_id=vcn_id,
                network_inventory=network_inventory,
                region_service=region_service,
                compartment_service=compartment_service,
            )
        except Exception as exc:
            return _failed_dashboard_snapshot(region, exc)
        duration = round(monotonic() - started, 2)
        now_iso = datetime.now(timezone.utc).isoformat()
        snapshot["collected_at"] = now_iso
        snapshot["duration_seconds"] = duration
        collection = snapshot.get("collection")
        if isinstance(collection, dict):
            for region_state in list(collection.get("regions", [])):
                if isinstance(region_state, dict) and region_state.get("id") == region:
                    region_state["last_updated"] = now_iso
                    region_state["duration_seconds"] = duration
        return snapshot

    return _dashboard_executor.submit(_collect)


@router.get("/dashboard")
def dashboard_snapshot(
    regions: str | None = Query(default=None, description="Comma-separated OCI region names."),
    compartment_ids: str | None = Query(default=None, description="Comma-separated compartment OCIDs."),
    vcn_id: str | None = Query(default=None, description="Optional VCN OCID filter."),
    async_collect: bool = Query(default=False, description="Start collection in the background and return cached status."),
    refresh: bool = Query(default=False, description="Force a background refresh for the requested regions."),
    clear_cache: bool = Query(default=False, description="Clear cached dashboard snapshots before collecting."),
    network_inventory: NetworkInventoryService = Depends(get_network_inventory_service),
    region_service: RegionService = Depends(get_region_service),
    compartment_service: CompartmentService = Depends(get_compartment_service),
) -> dict[str, object]:
    try:
        selected_regions = split_csv(regions)
        selected_compartments = split_csv(compartment_ids)
        if async_collect:
            async_regions = selected_regions or [region.id for region in region_service.list_active()]
            if not async_regions:
                async_regions = network_inventory.selected_region_ids(selected_regions)
            return _async_dashboard_snapshot(
                selected_regions=async_regions,
                selected_compartments=selected_compartments,
                vcn_id=vcn_id,
                network_inventory=network_inventory,
                region_service=region_service,
                compartment_service=compartment_service,
                refresh=refresh,
                clear_cache=clear_cache,
            )
        return _build_dashboard_snapshot(
            selected_regions=selected_regions,
            selected_compartments=selected_compartments,
            vcn_id=vcn_id,
            network_inventory=network_inventory,
            region_service=region_service,
            compartment_service=compartment_service,
        )
    except OciClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OCI_CLIENT_ERROR", "message": str(exc)},
        ) from exc


def _async_dashboard_snapshot(
    selected_regions: list[str],
    selected_compartments: list[str],
    vcn_id: str | None,
    network_inventory: NetworkInventoryService,
    region_service: RegionService,
    compartment_service: CompartmentService,
    refresh: bool = False,
    clear_cache: bool = False,
) -> dict[str, object]:
    now = monotonic()
    ready_snapshots: dict[str, dict[str, object]] = {}
    region_states: list[dict[str, object]] = []
    selected_compartment_key = tuple(selected_compartments)
    vcn_key = vcn_id or ""

    with _dashboard_lock:
        for region in selected_regions:
            key = (region, selected_compartment_key, vcn_key)
            if clear_cache:
                _clear_dashboard_snapshot(network_inventory, key)

            job = _dashboard_jobs.get(key)
            if job and job.done():
                _dashboard_jobs.pop(key, None)
                if not clear_cache:
                    try:
                        snapshot = jsonable_encoder(job.result())
                    except Exception as exc:
                        snapshot = _failed_dashboard_snapshot(region, exc)
                    _dashboard_snapshots[key] = (monotonic(), snapshot)
                    _write_persistent_snapshot(network_inventory, key, snapshot)
                    ready_snapshots[region] = snapshot
                    region_states.append(_region_collection_state(region, snapshot))
                    continue
                job = None
            else:
                job = job if job and not job.done() else None

            cached = _dashboard_snapshots.get(key)
            snapshot = cached[1] if cached else None
            if snapshot is None:
                snapshot = _read_persistent_snapshot(network_inventory, key)
                if snapshot is not None:
                    _dashboard_snapshots[key] = (monotonic(), snapshot)

            if snapshot is not None:
                state = _region_collection_state(region, snapshot)
                if _snapshot_is_fresh(snapshot, now, network_inventory) and not refresh:
                    ready_snapshots[region] = snapshot
                    region_states.append(state)
                    continue
                if job is None:
                    job = _start_region_collection_job(
                        key=key,
                        region=region,
                        selected_compartments=selected_compartments,
                        vcn_id=vcn_id,
                        network_inventory=network_inventory,
                        region_service=region_service,
                        compartment_service=compartment_service,
                    )
                    _dashboard_jobs[key] = job
                ready_snapshots[region] = snapshot
                state["status"] = "collecting"
                state["refreshing"] = True
                region_states.append(state)
                continue

            if job is None:
                job = _start_region_collection_job(
                    key=key,
                    region=region,
                    selected_compartments=selected_compartments,
                    vcn_id=vcn_id,
                    network_inventory=network_inventory,
                    region_service=region_service,
                    compartment_service=compartment_service,
                )
                _dashboard_jobs[key] = job

            region_states.append(
                {
                    "id": region,
                    "status": "collecting",
                    "issues": [],
                    "resource_counts": {},
                }
            )

    return _aggregate_dashboard_snapshots(
        active_regions=region_service.list_active(),
        compartments=compartment_service.list_compartments(),
        selected_regions=selected_regions,
        region_snapshots=ready_snapshots,
        region_states=region_states,
    )


def _build_dashboard_snapshot(
    selected_regions: list[str],
    selected_compartments: list[str],
    vcn_id: str | None,
    network_inventory: NetworkInventoryService,
    region_service: RegionService,
    compartment_service: CompartmentService,
) -> dict[str, object]:
    started = monotonic()
    network_inventory.reset_collection_issues()
    effective_regions = network_inventory.selected_region_ids(selected_regions)
    route_analysis = RouteAnalysisService(network_inventory=network_inventory)
    security_posture = SecurityPostureService(network_inventory=network_inventory)
    response = {
        "activeRegions": region_service.list_active(),
        "compartments": compartment_service.list_compartments(),
        "vcns": network_inventory.list_vcns(regions=effective_regions, compartment_ids=selected_compartments),
        "subnets": network_inventory.list_subnets(
            regions=effective_regions,
            compartment_ids=selected_compartments,
            vcn_id=vcn_id,
        ),
        "gateways": network_inventory.list_gateways(
            regions=effective_regions,
            compartment_ids=selected_compartments,
            vcn_id=vcn_id,
        ),
        "routeTables": network_inventory.list_route_tables(
            regions=effective_regions,
            compartment_ids=selected_compartments,
            vcn_id=vcn_id,
        ),
        "routeIssues": route_analysis.summarize(
            regions=effective_regions,
            compartment_ids=selected_compartments,
            vcn_id=vcn_id,
        ),
        "securityLists": network_inventory.list_security_lists(
            regions=effective_regions,
            compartment_ids=selected_compartments,
            vcn_id=vcn_id,
        ),
        "networkSecurityGroups": network_inventory.list_network_security_groups(
            regions=effective_regions,
            compartment_ids=selected_compartments,
            vcn_id=vcn_id,
        ),
        "topology": network_inventory.get_topology(
            regions=effective_regions,
            compartment_ids=selected_compartments,
            vcn_id=vcn_id,
        ),
        "securityPosture": security_posture.summarize(
            regions=effective_regions,
            compartment_ids=selected_compartments,
            vcn_id=vcn_id,
        ),
    }
    response["activeRegions"] = _dashboard_active_regions(
        region_service=region_service,
        network_inventory=network_inventory,
        response=response,
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    duration = round(monotonic() - started, 2)
    response["collected_at"] = now_iso
    response["duration_seconds"] = duration
    all_issues = network_inventory.collection_issues()
    region_rows: list[dict[str, object]] = []
    for region in effective_regions:
        region_issues = [i for i in all_issues if i.get("region") == region]
        resource_counts = {
            "vcns": len([item for item in response["vcns"] if item.region == region]),
            "subnets": len([item for item in response["subnets"] if item.region == region]),
            "gateways": len([item for item in response["gateways"] if item.region == region]),
            "routeTables": len([item for item in response["routeTables"] if item.region == region]),
            "securityLists": len([item for item in response["securityLists"] if item.region == region]),
            "networkSecurityGroups": len(
                [item for item in response["networkSecurityGroups"] if item.region == region]
            ),
        }
        has_resources = any(v > 0 for v in resource_counts.values())
        if region_issues:
            region_status = "ready_with_warnings"
        elif not has_resources:
            region_status = "no_resources"
        else:
            region_status = "ready"
        region_rows.append({
            "id": region,
            "status": region_status,
            "issues": region_issues,
            "resource_counts": resource_counts,
            "last_updated": now_iso,
            "duration_seconds": duration,
            "error": None,
        })
    response["collection"] = {
        "status": "ready_with_warnings" if all_issues else "ready",
        "requested_regions": effective_regions,
        "issues": all_issues,
        "completed_regions": effective_regions,
        "pending_regions": [],
        "regions": region_rows,
    }
    return jsonable_encoder(response)


def _aggregate_dashboard_snapshots(
    active_regions: list[object],
    compartments: list[object],
    selected_regions: list[str],
    region_snapshots: dict[str, dict[str, object]],
    region_states: list[dict[str, object]],
) -> dict[str, object]:
    response = _empty_dashboard_snapshot(
        active_regions=active_regions,
        compartments=compartments,
        selected_regions=selected_regions,
    )
    for field in (
        "vcns",
        "subnets",
        "gateways",
        "routeTables",
        "securityLists",
        "networkSecurityGroups",
    ):
        response[field] = [
            item
            for region in selected_regions
            for item in list(region_snapshots.get(region, {}).get(field, []))
        ]
    response["routeIssues"] = _aggregate_route_issues(region_snapshots, selected_regions)
    response["securityPosture"] = _aggregate_security_posture(region_snapshots, selected_regions)
    response["topology"] = _aggregate_topology(region_snapshots, selected_regions)

    issues = [
        issue
        for region in selected_regions
        for issue in list(region_snapshots.get(region, {}).get("collection", {}).get("issues", []))
    ]
    pending_regions = [str(state["id"]) for state in region_states if state.get("status") == "collecting"]
    completed_regions = [str(state["id"]) for state in region_states if state.get("status") != "collecting"]
    response["collection"] = {
        "status": "collecting" if pending_regions else "ready_with_warnings" if issues else "ready",
        "requested_regions": selected_regions,
        "completed_regions": completed_regions,
        "pending_regions": pending_regions,
        "issues": issues,
        "regions": region_states,
    }
    return response


def _dashboard_active_regions(
    region_service: RegionService,
    network_inventory: NetworkInventoryService,
    response: dict[str, object],
) -> list[dict[str, object]]:
    configured_regions = region_service.list_active()
    available_by_id = {region.id: region for region in region_service.list_available()}
    home_region = network_inventory.settings.home_region
    region_ids = list(
        dict.fromkeys(
            [
                *(region.id for region in configured_regions),
                *network_inventory.discovered_region_ids(),
                *_observed_region_ids(response),
            ]
        )
    )

    def sort_key(region_id: str) -> tuple[int, str]:
        return (0 if region_id == home_region else 1, region_id)

    results: list[dict[str, object]] = []
    for region_id in sorted(region_ids, key=sort_key):
        detail = available_by_id.get(region_id)
        results.append(
            {
                "id": region_id,
                "geo": detail.geo if detail else _region_geo(region_id),
                "is_home_region": region_id == home_region,
                "is_active": True,
            }
        )
    return results


def _observed_region_ids(response: dict[str, object]) -> list[str]:
    region_ids: list[str] = []
    for field in (
        "vcns",
        "subnets",
        "gateways",
        "routeTables",
        "securityLists",
        "networkSecurityGroups",
    ):
        for item in list(response.get(field, [])):
            region = getattr(item, "region", None)
            if region:
                region_ids.append(str(region))
    return region_ids


def _region_geo(region_id: str) -> str:
    if region_id.startswith("eu-"):
        return "Europe"
    if region_id.startswith(("us-", "ca-", "mx-")):
        return "North America"
    if region_id.startswith("af-"):
        return "Africa"
    if region_id.startswith(("me-", "il-")):
        return "Middle East"
    if region_id.startswith("ap-"):
        return "Asia Pacific"
    if region_id.startswith("sa-"):
        return "South America"
    return "Region"


def _region_collection_state(region: str, snapshot: dict[str, object]) -> dict[str, object]:
    collection = snapshot.get("collection", {})
    collection_dict = collection if isinstance(collection, dict) else {}
    issues = list(collection_dict.get("issues", []))
    region_issues = [issue for issue in issues if issue.get("region") == region]
    resource_counts = {
        "vcns": len(snapshot.get("vcns", [])),
        "subnets": len(snapshot.get("subnets", [])),
        "gateways": len(snapshot.get("gateways", [])),
        "routeTables": len(snapshot.get("routeTables", [])),
        "securityLists": len(snapshot.get("securityLists", [])),
        "networkSecurityGroups": len(snapshot.get("networkSecurityGroups", [])),
    }
    collection_status = collection_dict.get("status", "")
    has_resources = any(v > 0 for v in resource_counts.values())
    if collection_status == "failed":
        status = "failed"
    elif region_issues:
        status = "ready_with_warnings"
    elif not has_resources:
        status = "no_resources"
    else:
        status = "ready"
    return {
        "id": region,
        "status": status,
        "issues": region_issues,
        "resource_counts": resource_counts,
        "last_updated": snapshot.get("collected_at"),
        "duration_seconds": snapshot.get("duration_seconds"),
        "error": region_issues[0].get("message") if status == "failed" and region_issues else None,
    }


def _aggregate_route_issues(
    region_snapshots: dict[str, dict[str, object]],
    selected_regions: list[str],
) -> dict[str, object]:
    issues = [
        issue
        for region in selected_regions
        for issue in list(region_snapshots.get(region, {}).get("routeIssues", {}).get("issues", []))
    ]
    critical = sum(1 for issue in issues if issue.get("severity") == "critical")
    high = sum(1 for issue in issues if issue.get("severity") == "high")
    medium = sum(1 for issue in issues if issue.get("severity") == "medium")
    low = sum(1 for issue in issues if issue.get("severity") == "low")
    return {
        "status": "degraded" if critical or high else "warn" if medium or low else "ok",
        "total_issues": len(issues),
        "critical_issues": critical,
        "high_issues": high,
        "medium_issues": medium,
        "low_issues": low,
        "issues": issues,
    }


def _aggregate_security_posture(
    region_snapshots: dict[str, dict[str, object]],
    selected_regions: list[str],
) -> dict[str, object]:
    summaries = [
        region_snapshots[region].get("securityPosture", {})
        for region in selected_regions
        if region in region_snapshots
    ]
    findings = [finding for summary in summaries for finding in list(summary.get("findings", []))]
    critical = sum(1 for finding in findings if finding.get("severity") == "critical")
    high = sum(1 for finding in findings if finding.get("severity") == "high")
    medium = sum(1 for finding in findings if finding.get("severity") == "medium")
    low = sum(1 for finding in findings if finding.get("severity") == "low")
    return {
        "status": "degraded" if critical or high else "warn" if medium or low else "ok",
        "risk_score": min(100, sum(int(finding.get("risk_score", 0) or 0) for finding in findings)),
        "scanned_security_lists": sum(int(summary.get("scanned_security_lists", 0) or 0) for summary in summaries),
        "scanned_network_security_groups": sum(
            int(summary.get("scanned_network_security_groups", 0) or 0) for summary in summaries
        ),
        "scanned_ingress_rules": sum(int(summary.get("scanned_ingress_rules", 0) or 0) for summary in summaries),
        "scanned_egress_rules": sum(int(summary.get("scanned_egress_rules", 0) or 0) for summary in summaries),
        "total_findings": len(findings),
        "critical_findings": critical,
        "high_findings": high,
        "medium_findings": medium,
        "low_findings": low,
        "findings": findings,
    }


def _aggregate_topology(
    region_snapshots: dict[str, dict[str, object]],
    selected_regions: list[str],
) -> dict[str, object]:
    nodes_by_id: dict[str, object] = {}
    edges_by_id: dict[str, object] = {}
    for region in selected_regions:
        topology = region_snapshots.get(region, {}).get("topology", {})
        for node in list(topology.get("nodes", [])):
            node_id = node.get("id")
            if node_id:
                nodes_by_id[str(node_id)] = node
        for edge in list(topology.get("edges", [])):
            edge_id = edge.get("id")
            if edge_id:
                edges_by_id[str(edge_id)] = edge
    return {"nodes": list(nodes_by_id.values()), "edges": list(edges_by_id.values())}


def _empty_dashboard_snapshot(
    active_regions: list[object],
    compartments: list[object],
    selected_regions: list[str],
) -> dict[str, object]:
    return {
        "activeRegions": active_regions,
        "compartments": compartments,
        "vcns": [],
        "subnets": [],
        "gateways": [],
        "routeTables": [],
        "routeIssues": {
            "status": "ok",
            "total_issues": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0,
            "issues": [],
        },
        "securityLists": [],
        "networkSecurityGroups": [],
        "topology": {"nodes": [], "edges": []},
        "securityPosture": {
            "status": "ok",
            "risk_score": 0,
            "scanned_security_lists": 0,
            "scanned_network_security_groups": 0,
            "scanned_ingress_rules": 0,
            "scanned_egress_rules": 0,
            "total_findings": 0,
            "critical_findings": 0,
            "high_findings": 0,
            "medium_findings": 0,
            "low_findings": 0,
            "findings": [],
        },
        "collection": {
            "status": "collecting",
            "requested_regions": selected_regions,
            "issues": [],
        },
    }


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
