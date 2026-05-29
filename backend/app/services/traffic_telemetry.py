from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
import json
from pathlib import Path
import threading
from typing import Any

from app.config import Settings
from app.models import (
    TrafficEnableRequest,
    TrafficEnablementItem,
    TrafficEnablementResponse,
    TrafficEndpointSummary,
    TrafficFlowRecord,
    TrafficFlowSummary,
    TrafficTelemetryStatus,
    VcnSummary,
)
from app.oci_clients import OciClientError, OciClientFactory
from app.services.network_inventory import NetworkInventoryService


_LEASE_LOCK = threading.Lock()


@dataclass(frozen=True)
class TrafficTelemetryService:
    settings: Settings
    client_factory: OciClientFactory
    network_inventory: NetworkInventoryService

    def status(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_ids: list[str] | None = None,
        check_vcns: bool = False,
    ) -> TrafficTelemetryStatus:
        base = self._base_status()
        if not self.settings.enable_live_oci:
            return base.model_copy(
                update={
                    "status": "disabled",
                    "message": "Live OCI mode is disabled; VCN Flow Logs cannot be checked from this API process.",
                }
            )
        self.disable_expired_leases()
        if not check_vcns:
            return base.model_copy(
                update={
                    "status": "ready" if self.settings.traffic_flow_logs_enablement_allowed else "blocked",
                    "message": (
                        "Choose one VCN and enable telemetry only for the investigation window."
                        if self.settings.traffic_flow_logs_enablement_allowed
                        else "Traffic telemetry enablement is disabled, so no VCN Flow Logs can be created from the dashboard."
                    ),
                }
            )

        vcns = self._selected_vcns(regions=regions, compartment_ids=compartment_ids, vcn_ids=vcn_ids or [])
        if not vcns:
            return base.model_copy(
                update={
                    "status": "no_vcns",
                    "message": "No VCNs were found in the selected scope.",
                }
            )

        enabled = 0
        expirations: list[str] = []
        failures: list[str] = []
        for vcn in vcns:
            try:
                flow_log = self._flow_log_for_vcn(vcn, require_enabled=True)
                if flow_log:
                    enabled += 1
                    expires_at = self._lease_expiration(vcn_id=vcn.id, log_id=getattr(flow_log, "id", None))
                    if expires_at:
                        expirations.append(expires_at)
            except Exception as exc:  # pragma: no cover - exercised by OCI integration
                failures.append(f"{vcn.name}: {self._error_message(exc)}")

        missing = max(0, len(vcns) - enabled)
        if failures:
            status = "degraded"
            message = f"Checked {len(vcns)} VCNs, but {len(failures)} checks failed. First error: {failures[0]}"
        elif missing:
            status = "partial" if enabled else "not_enabled"
            message = f"{enabled}/{len(vcns)} selected VCNs have Meridian traffic flow logs enabled."
        else:
            status = "enabled"
            message = f"Traffic telemetry is enabled for all {len(vcns)} selected VCNs."

        return base.model_copy(
            update={
                "status": status,
                "checked_vcns": len(vcns),
                "enabled_vcns": enabled,
                "missing_vcns": missing,
                "expires_at": min(expirations) if expirations else None,
                "message": message,
            }
        )

    def enable(self, request: TrafficEnableRequest) -> TrafficEnablementResponse:
        if not self.settings.enable_live_oci:
            raise PermissionError("Live OCI mode is disabled.")
        if not self.settings.traffic_flow_logs_enablement_allowed:
            raise PermissionError(
                "Traffic telemetry enablement is disabled. Set MERIDIAN_TRAFFIC_FLOW_LOGS_ENABLEMENT_ALLOWED=true."
            )
        self.disable_expired_leases()
        expires_at = self._expires_at(getattr(request, "enablement_minutes", None))

        vcns = self._selected_vcns(
            regions=request.regions,
            compartment_ids=request.compartment_ids,
            vcn_ids=request.vcn_ids,
        )
        items: list[TrafficEnablementItem] = []
        for vcn in vcns:
            try:
                items.append(self._enable_vcn(vcn, expires_at=expires_at))
            except Exception as exc:  # pragma: no cover - exercised by OCI integration
                items.append(
                    TrafficEnablementItem(
                        vcn_id=vcn.id,
                        vcn_name=vcn.name,
                        region=vcn.region,
                        compartment_id=vcn.compartment_id,
                        status="failed",
                        message=self._error_message(exc),
                        expires_at=expires_at,
                    )
                )

        enabled = len([item for item in items if item.status == "enabled"])
        skipped = len([item for item in items if item.status == "already_enabled"])
        failed = len([item for item in items if item.status == "failed"])
        status = "failed" if failed and not (enabled or skipped) else "partial" if failed else "enabled"
        return TrafficEnablementResponse(
            status=status,
            enabled=enabled,
            skipped=skipped,
            failed=failed,
            expires_at=expires_at if enabled or skipped else None,
            items=items,
        )

    def disable(self, request: TrafficEnableRequest) -> TrafficEnablementResponse:
        if not self.settings.enable_live_oci:
            raise PermissionError("Live OCI mode is disabled.")
        self.disable_expired_leases()

        vcns = self._selected_vcns(
            regions=request.regions,
            compartment_ids=request.compartment_ids,
            vcn_ids=request.vcn_ids,
        )
        items: list[TrafficEnablementItem] = []
        for vcn in vcns:
            try:
                items.append(self._disable_vcn(vcn))
            except Exception as exc:  # pragma: no cover - exercised by OCI integration
                items.append(
                    TrafficEnablementItem(
                        vcn_id=vcn.id,
                        vcn_name=vcn.name,
                        region=vcn.region,
                        compartment_id=vcn.compartment_id,
                        status="failed",
                        message=self._error_message(exc),
                    )
                )

        disabled = len([item for item in items if item.status == "disabled"])
        skipped = len([item for item in items if item.status == "not_enabled"])
        failed = len([item for item in items if item.status == "failed"])
        status = "failed" if failed and not (disabled or skipped) else "partial" if failed else "disabled"
        return TrafficEnablementResponse(
            status=status,
            enabled=disabled,
            skipped=skipped,
            failed=failed,
            items=items,
        )

    def list_flows(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        source_ip: str | None = None,
        destination_ip: str | None = None,
        port: int | None = None,
        action: str | None = None,
        lookback_minutes: int | None = None,
        limit: int | None = None,
    ) -> TrafficFlowSummary:
        window_minutes = self._bounded_lookback(lookback_minutes)
        if not self.settings.enable_live_oci:
            return TrafficFlowSummary(
                status="disabled",
                total_flows=0,
                time_window_minutes=window_minutes,
                flows=[],
                message="Live OCI mode is disabled.",
            )

        selected_regions = regions or self.network_inventory.selected_region_ids()
        selected_compartments = compartment_ids or self.settings.compartment_ids or [
            self.settings.tenancy_ocid
        ]
        selected_compartments = [item for item in selected_compartments if item]
        if not selected_regions or not selected_compartments:
            return TrafficFlowSummary(
                status="no_scope",
                total_flows=0,
                time_window_minutes=window_minutes,
                flows=[],
                message="No region or compartment scope is configured.",
            )

        source_ip = self._validated_ip(source_ip)
        destination_ip = self._validated_ip(destination_ip)
        selected_limit = self._bounded_limit(limit)
        endpoints = self._endpoint_inventory(selected_regions, selected_compartments)
        endpoint_map = {endpoint.ip_address: endpoint for endpoint in endpoints}
        flows: list[TrafficFlowRecord] = []
        errors: list[str] = []

        for region in selected_regions:
            client = self.client_factory.logging_search_client(region=region)
            for compartment_id in selected_compartments:
                query = self._flow_search_query(
                    compartment_id=compartment_id,
                    source_ip=source_ip,
                    destination_ip=destination_ip,
                    port=port,
                    action=action,
                )
                try:
                    flows.extend(
                        self._search_flow_logs(
                            client=client,
                            query=query,
                            region=region,
                            compartment_id=compartment_id,
                            lookback_minutes=window_minutes,
                            limit=selected_limit,
                            endpoint_map=endpoint_map,
                        )
                    )
                except Exception as exc:  # pragma: no cover - exercised by OCI integration
                    errors.append(f"{region}/{compartment_id}: {self._error_message(exc)}")

        flows = sorted(flows, key=lambda item: item.time_start or item.time_end or "", reverse=True)[:selected_limit]
        status = "degraded" if errors and flows else "failed" if errors else "ok"
        message = errors[0] if errors else None
        return TrafficFlowSummary(
            status=status,
            total_flows=len(flows),
            time_window_minutes=window_minutes,
            flows=flows,
            endpoints=endpoints,
            message=message,
        )

    def disable_expired_leases(self) -> int:
        now = self._now()
        leases = self._load_leases()
        disabled = 0
        pending: list[dict[str, Any]] = []
        for lease in leases:
            expires_at = self._parse_time(str(lease.get("expires_at") or ""))
            if not expires_at or expires_at > now:
                pending.append(lease)
                continue
            try:
                client = self.client_factory.logging_management_client(region=lease.get("region"))
                self._cleanup_log_resource(client=client, log_group_id=lease["log_group_id"], log_id=lease["log_id"])
                disabled += 1
            except Exception as exc:  # pragma: no cover - exercised by OCI integration
                lease["last_error"] = self._error_message(exc)
                pending.append(lease)
        if len(pending) != len(leases):
            self._save_leases(pending)
        return disabled

    def _base_status(self) -> TrafficTelemetryStatus:
        return TrafficTelemetryStatus(
            status="unknown",
            live_oci_enabled=self.settings.enable_live_oci,
            enablement_allowed=self.settings.traffic_flow_logs_enablement_allowed,
            log_group_name=self.settings.traffic_flow_logs_log_group_name,
            capture_filter_name=self.settings.traffic_flow_logs_capture_filter_name,
            max_enablement_minutes=self.settings.traffic_flow_logs_max_enablement_minutes,
            message="Traffic telemetry status has not been checked.",
        )

    def _selected_vcns(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_ids: list[str] | None = None,
    ) -> list[VcnSummary]:
        selected_ids = {item for item in (vcn_ids or []) if item}
        vcns = self.network_inventory.list_vcns(regions=regions or None, compartment_ids=compartment_ids or None)
        if selected_ids:
            vcns = [vcn for vcn in vcns if vcn.id in selected_ids]
        return vcns

    def _enable_vcn(self, vcn: VcnSummary, expires_at: str) -> TrafficEnablementItem:
        existing_log = self._flow_log_for_vcn(vcn, require_enabled=True)
        if existing_log is not None:
            log_group_id = getattr(existing_log, "_meridian_log_group_id", None) or getattr(existing_log, "log_group_id", None)
            self._record_lease(vcn=vcn, log_group_id=log_group_id, log_id=getattr(existing_log, "id", None), expires_at=expires_at)
            return TrafficEnablementItem(
                vcn_id=vcn.id,
                vcn_name=vcn.name,
                region=vcn.region,
                compartment_id=vcn.compartment_id,
                status="already_enabled",
                message=f"A Meridian VCN Flow Log already exists for this VCN and is leased until {expires_at}.",
                log_id=getattr(existing_log, "id", None),
                log_group_id=log_group_id,
                expires_at=expires_at,
            )

        log_client = self.client_factory.logging_management_client(region=vcn.region)
        network_client = self.client_factory.virtual_network_client(region=vcn.region)
        log_group = self._ensure_log_group(log_client, vcn.compartment_id)
        capture_filter = self._ensure_capture_filter(network_client, vcn.compartment_id)
        log = self._create_flow_log(log_client, log_group, vcn, capture_filter, expires_at=expires_at)
        self._record_lease(vcn=vcn, log_group_id=getattr(log_group, "id", None), log_id=getattr(log, "id", None), expires_at=expires_at)
        return TrafficEnablementItem(
            vcn_id=vcn.id,
            vcn_name=vcn.name,
            region=vcn.region,
            compartment_id=vcn.compartment_id,
            status="enabled",
            message=f"VCN Flow Logs were enabled for this VCN until {expires_at}.",
            log_group_id=getattr(log_group, "id", None),
            log_id=getattr(log, "id", None),
            capture_filter_id=getattr(capture_filter, "id", None),
            expires_at=expires_at,
        )

    def _disable_vcn(self, vcn: VcnSummary) -> TrafficEnablementItem:
        existing_log = self._flow_log_for_vcn(vcn, require_enabled=True)
        if existing_log is None:
            return TrafficEnablementItem(
                vcn_id=vcn.id,
                vcn_name=vcn.name,
                region=vcn.region,
                compartment_id=vcn.compartment_id,
                status="not_enabled",
                message="No enabled Meridian VCN Flow Log was found for this VCN.",
            )
        client = self.client_factory.logging_management_client(region=vcn.region)
        details = self.client_factory.logging_model("UpdateLogDetails", is_enabled=False)
        log_group_id = getattr(existing_log, "_meridian_log_group_id", None) or getattr(existing_log, "log_group_id", None)
        client.update_log(
            log_group_id=log_group_id,
            log_id=existing_log.id,
            update_log_details=details,
        )
        self._remove_lease(log_id=getattr(existing_log, "id", None), vcn_id=vcn.id)
        return TrafficEnablementItem(
            vcn_id=vcn.id,
            vcn_name=vcn.name,
            region=vcn.region,
            compartment_id=vcn.compartment_id,
            status="disabled",
            message="VCN Flow Log was disabled for this VCN.",
            log_group_id=log_group_id,
            log_id=getattr(existing_log, "id", None),
        )

    def _ensure_log_group(self, client: Any, compartment_id: str) -> Any:
        existing = self._find_by_display_name(
            self._list_log_groups(client, compartment_id),
            self.settings.traffic_flow_logs_log_group_name,
        )
        if existing is not None:
            return existing
        details = self.client_factory.logging_model(
            "CreateLogGroupDetails",
            compartment_id=compartment_id,
            display_name=self.settings.traffic_flow_logs_log_group_name,
            description="Meridian Network VCN Flow Logs for traffic telemetry.",
            freeform_tags={"project": "meridian-network", "managed": "meridian"},
        )
        return client.create_log_group(details).data

    def _ensure_capture_filter(self, client: Any, compartment_id: str) -> Any:
        existing = self._find_by_display_name(
            self._list_capture_filters(client, compartment_id),
            self.settings.traffic_flow_logs_capture_filter_name,
        )
        if existing is not None:
            return existing
        details = self.client_factory.core_model(
            "CreateCaptureFilterDetails",
            compartment_id=compartment_id,
            display_name=self.settings.traffic_flow_logs_capture_filter_name,
            filter_type="FLOWLOG",
            flow_log_capture_filter_rules=[self._capture_filter_rule()],
            freeform_tags={"project": "meridian-network", "managed": "meridian"},
        )
        return client.create_capture_filter(details).data

    def _capture_filter_rule(self) -> Any:
        return self.client_factory.core_model(
            "FlowLogCaptureFilterRuleDetails",
            is_enabled=True,
            priority=1,
            rule_action="INCLUDE",
            sampling_rate=1,
        )

    def _create_flow_log(self, client: Any, log_group: Any, vcn: VcnSummary, capture_filter: Any, expires_at: str) -> Any:
        source = self.client_factory.logging_model(
            "OciService",
            source_type="OCISERVICE",
            service="flowlogs",
            resource=vcn.id,
            category="vcn",
            parameters={"capture_filter": getattr(capture_filter, "id", "")},
        )
        configuration = self.client_factory.logging_model(
            "Configuration",
            source=source,
            compartment_id=vcn.compartment_id,
        )
        details = self.client_factory.logging_model(
            "CreateLogDetails",
            display_name=self._flow_log_name(vcn),
            log_type="SERVICE",
            is_enabled=True,
            configuration=configuration,
            freeform_tags={
                "project": "meridian-network",
                "managed": "meridian",
                "vcn_id": vcn.id,
                **({"expires_at": expires_at} if expires_at else {}),
            },
        )
        return client.create_log(log_group_id=log_group.id, create_log_details=details).data

    def _flow_log_for_vcn(self, vcn: VcnSummary, require_enabled: bool = False) -> Any | None:
        client = self.client_factory.logging_management_client(region=vcn.region)
        for log_group in self._list_log_groups(client, vcn.compartment_id):
            if getattr(log_group, "display_name", None) != self.settings.traffic_flow_logs_log_group_name:
                continue
            for log in self._list_logs(client, log_group.id):
                source = getattr(getattr(log, "configuration", None), "source", None)
                if getattr(source, "service", None) == "flowlogs" and getattr(source, "resource", None) == vcn.id:
                    if require_enabled and getattr(log, "is_enabled", True) is False:
                        continue
                    try:
                        setattr(log, "_meridian_log_group_id", log_group.id)
                    except Exception:
                        pass
                    return log
        return None

    def _list_log_groups(self, client: Any, compartment_id: str) -> list[Any]:
        return self.client_factory.list_all(client.list_log_groups, compartment_id=compartment_id)

    def _list_logs(self, client: Any, log_group_id: str) -> list[Any]:
        return self.client_factory.list_all(client.list_logs, log_group_id=log_group_id)

    def _list_capture_filters(self, client: Any, compartment_id: str) -> list[Any]:
        method = getattr(client, "list_capture_filters", None)
        if method is None:
            return []
        return self.client_factory.list_all(method, compartment_id=compartment_id)

    def _find_by_display_name(self, items: list[Any], display_name: str) -> Any | None:
        return next((item for item in items if getattr(item, "display_name", None) == display_name), None)

    def _flow_log_name(self, vcn: VcnSummary) -> str:
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in vcn.name.lower()).strip("-")
        return f"{self.settings.traffic_flow_logs_log_name_prefix}-{safe_name or vcn.id[-12:]}"

    def _flow_search_query(
        self,
        compartment_id: str,
        source_ip: str | None,
        destination_ip: str | None,
        port: int | None,
        action: str | None,
    ) -> str:
        clauses = ['data.service = "flowlogs"']
        if source_ip:
            clauses.append(f'data.sourceAddress = "{source_ip}"')
        if destination_ip:
            clauses.append(f'data.destinationAddress = "{destination_ip}"')
        if port:
            clauses.append(f"data.destinationPort = {int(port)}")
        if action:
            clauses.append(f'data.action = "{action.upper()}"')
        where = " and ".join(clauses)
        return f'search "{compartment_id}" | where {where} | sort by datetime desc'

    def _search_flow_logs(
        self,
        client: Any,
        query: str,
        region: str,
        compartment_id: str,
        lookback_minutes: int,
        limit: int,
        endpoint_map: dict[str, TrafficEndpointSummary],
    ) -> list[TrafficFlowRecord]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=lookback_minutes)
        details = self.client_factory.loggingsearch_model(
            "SearchLogsDetails",
            search_query=query,
            time_start=start,
            time_end=end,
        )
        response = client.search_logs(details, limit=limit)
        records = self._search_items(response)
        return [
            record
            for record in (
                self._flow_record(item, region=region, compartment_id=compartment_id, endpoint_map=endpoint_map)
                for item in records
            )
            if record is not None
        ]

    def _search_items(self, response: Any) -> list[Any]:
        data = getattr(response, "data", response)
        for attr in ("results", "items"):
            value = getattr(data, attr, None)
            if isinstance(value, list):
                return value
        if isinstance(data, list):
            return data
        return []

    def _flow_record(
        self,
        item: Any,
        region: str,
        compartment_id: str,
        endpoint_map: dict[str, TrafficEndpointSummary],
    ) -> TrafficFlowRecord | None:
        payload = self._flow_payload(item)
        source_ip = self._get_value(payload, "sourceAddress", "source_ip", "srcaddr", "src_ip")
        destination_ip = self._get_value(payload, "destinationAddress", "destination_ip", "dstaddr", "dst_ip")
        if not source_ip or not destination_ip:
            return None
        source_ip = str(source_ip)
        destination_ip = str(destination_ip)
        return TrafficFlowRecord(
            time_start=self._string_value(self._get_value(payload, "startTime", "timeStart", "start_time", "datetime")),
            time_end=self._string_value(self._get_value(payload, "endTime", "timeEnd", "end_time")),
            source_ip=source_ip,
            destination_ip=destination_ip,
            source_port=self._int_value(self._get_value(payload, "sourcePort", "source_port", "srcport")),
            destination_port=self._int_value(
                self._get_value(payload, "destinationPort", "destination_port", "dstport")
            ),
            protocol=self._string_value(self._get_value(payload, "protocol", "protocolName")),
            action=self._string_value(self._get_value(payload, "action")),
            status=self._string_value(self._get_value(payload, "status")),
            packets=self._int_value(self._get_value(payload, "packets", "packetsOut")),
            bytes=self._int_value(self._get_value(payload, "bytes", "bytesOut")),
            region=self._string_value(self._get_value(payload, "region")) or region,
            compartment_id=self._string_value(self._get_value(payload, "compartmentId", "compartment_id")) or compartment_id,
            log_id=self._string_value(self._get_value(payload, "logId", "log_id")),
            source=endpoint_map.get(source_ip),
            destination=endpoint_map.get(destination_ip),
        )

    def _flow_payload(self, item: Any) -> dict[str, Any]:
        raw = getattr(item, "data", item)
        if not isinstance(raw, dict):
            raw = getattr(raw, "__dict__", {})
        log_content = raw.get("logContent") or raw.get("log_content") or raw
        if not isinstance(log_content, dict):
            return raw
        nested = log_content.get("data")
        if isinstance(nested, dict):
            return {**log_content, **nested}
        return log_content

    def _endpoint_inventory(self, regions: list[str], compartment_ids: list[str]) -> list[TrafficEndpointSummary]:
        endpoints: list[TrafficEndpointSummary] = []
        subnets = self.network_inventory.list_subnets(regions=regions, compartment_ids=compartment_ids)
        subnet_vcn = {subnet.id: subnet.vcn_id for subnet in subnets}
        for region in regions:
            compute = self.client_factory.compute_client(region=region)
            network = self.client_factory.virtual_network_client(region=region)
            for compartment_id in compartment_ids:
                instances = self.client_factory.list_all(compute.list_instances, compartment_id=compartment_id)
                for instance in instances:
                    attachments = self.client_factory.list_all(
                        compute.list_vnic_attachments,
                        compartment_id=compartment_id,
                        instance_id=getattr(instance, "id", None),
                    )
                    for attachment in attachments:
                        vnic_id = getattr(attachment, "vnic_id", None)
                        if not vnic_id:
                            continue
                        try:
                            vnic = network.get_vnic(vnic_id).data
                        except Exception:
                            continue
                        private_ip = getattr(vnic, "private_ip", None)
                        if not private_ip:
                            continue
                        endpoints.append(
                            TrafficEndpointSummary(
                                ip_address=private_ip,
                                name=getattr(vnic, "display_name", None) or getattr(instance, "display_name", None),
                                instance_id=getattr(instance, "id", None),
                                instance_name=getattr(instance, "display_name", None),
                                vnic_id=vnic_id,
                                subnet_id=getattr(vnic, "subnet_id", None),
                                vcn_id=subnet_vcn.get(getattr(vnic, "subnet_id", None)),
                                region=region,
                                compartment_id=compartment_id,
                            )
                        )
        return endpoints

    def _bounded_lookback(self, value: int | None) -> int:
        default = self.settings.traffic_flow_logs_default_lookback_minutes
        max_minutes = max(1, self.settings.traffic_flow_logs_max_lookback_hours) * 60
        return max(1, min(int(value or default), max_minutes))

    def _bounded_limit(self, value: int | None) -> int:
        default = self.settings.traffic_flow_logs_search_limit
        return max(1, min(int(value or default), 500))

    def _expires_at(self, requested_minutes: int | None) -> str:
        max_minutes = max(1, int(self.settings.traffic_flow_logs_max_enablement_minutes))
        minutes = max(1, min(int(requested_minutes or max_minutes), max_minutes))
        return (self._now() + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")

    def _lease_path(self) -> Path:
        return Path(self.settings.traffic_flow_logs_lease_path)

    def _load_leases(self) -> list[dict[str, Any]]:
        path = self._lease_path()
        if not path.exists():
            return []
        with _LEASE_LOCK:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return []
        return data if isinstance(data, list) else []

    def _save_leases(self, leases: list[dict[str, Any]]) -> None:
        path = self._lease_path()
        with _LEASE_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(leases, indent=2, sort_keys=True), encoding="utf-8")

    def _record_lease(self, vcn: VcnSummary, log_group_id: str | None, log_id: str | None, expires_at: str) -> None:
        if not log_group_id or not log_id:
            return
        leases = [
            lease
            for lease in self._load_leases()
            if lease.get("log_id") != log_id and lease.get("vcn_id") != vcn.id
        ]
        leases.append(
            {
                "vcn_id": vcn.id,
                "vcn_name": vcn.name,
                "region": vcn.region,
                "compartment_id": vcn.compartment_id,
                "log_group_id": log_group_id,
                "log_id": log_id,
                "expires_at": expires_at,
                "created_at": self._now().isoformat().replace("+00:00", "Z"),
            }
        )
        self._save_leases(leases)

    def _remove_lease(self, log_id: str | None, vcn_id: str | None) -> None:
        leases = [
            lease
            for lease in self._load_leases()
            if not ((log_id and lease.get("log_id") == log_id) or (vcn_id and lease.get("vcn_id") == vcn_id))
        ]
        self._save_leases(leases)

    def _lease_expiration(self, vcn_id: str | None, log_id: str | None) -> str | None:
        expirations = [
            str(lease.get("expires_at"))
            for lease in self._load_leases()
            if (vcn_id and lease.get("vcn_id") == vcn_id) or (log_id and lease.get("log_id") == log_id)
        ]
        return min(expirations) if expirations else None

    def _cleanup_log_resource(self, client: Any, log_group_id: str, log_id: str) -> None:
        details = self.client_factory.logging_model("UpdateLogDetails", is_enabled=False)
        client.update_log(
            log_group_id=log_group_id,
            log_id=log_id,
            update_log_details=details,
        )
        delete_log = getattr(client, "delete_log", None)
        if delete_log is not None:
            delete_log(log_group_id=log_group_id, log_id=log_id)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _parse_time(self, value: str) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _validated_ip(self, value: str | None) -> str | None:
        if not value:
            return None
        return str(ip_address(value))

    def _get_value(self, data: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in data:
                return data[key]
        return None

    def _string_value(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _int_value(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _error_message(self, exc: Exception) -> str:
        if isinstance(exc, OciClientError):
            return str(exc)
        status = getattr(exc, "status", None)
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", None) or str(exc)
        parts = [str(part) for part in (status, code, message) if part]
        return " / ".join(parts) if parts else exc.__class__.__name__
