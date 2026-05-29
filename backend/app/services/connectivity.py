from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
import time
from typing import Any

from app.config import Settings
from app.models import ConnectivityCheckRequest, ConnectivityCheckResponse, ConnectivityEndpoint, ConnectivityHop
from app.oci_clients import OciClientFactory


_PROTOCOL_NUMBERS = {
    "ICMP": 1,
    "1": 1,
    "TCP": 6,
    "6": 6,
    "UDP": 17,
    "17": 17,
}
_TERMINAL_WORK_REQUEST_STATES = {"SUCCEEDED", "FAILED", "CANCELED", "CANCELING"}
_WORK_REQUEST_WAIT_SECONDS = 20


@dataclass(frozen=True)
class ConnectivityService:
    settings: Settings
    client_factory: OciClientFactory

    def check(self, request: ConnectivityCheckRequest) -> ConnectivityCheckResponse:
        if not self.settings.enable_live_oci:
            return ConnectivityCheckResponse(
                status="disabled",
                reachable=None,
                message="Live OCI mode is disabled; connectivity checks require OCI Network Path Analyzer.",
            )

        compartment_id = self._compartment_id(request)
        if not compartment_id:
            return ConnectivityCheckResponse(
                status="missing_scope",
                reachable=None,
                message="Choose a compartment scope before running Network Path Analyzer.",
            )

        region = request.region or self.settings.home_region
        client = self.client_factory.vn_monitoring_client(region=region)
        details = self.client_factory.vn_monitoring_model(
            "AdhocGetPathAnalysisDetails",
            type="ADHOC_QUERY",
            compartment_id=compartment_id,
            protocol=self._protocol_number(request.protocol),
            source_endpoint=self._endpoint(request.source),
            destination_endpoint=self._endpoint(request.destination),
            protocol_parameters=self._protocol_parameters(request),
            query_options=self.client_factory.vn_monitoring_model(
                "QueryOptions",
                is_bi_directional_analysis=request.bidirectional,
            ),
        )

        try:
            response = client.get_path_analysis(details)
            work_request_id = self._work_request_id(response)
            if not work_request_id:
                return ConnectivityCheckResponse(
                    status="failed",
                    reachable=None,
                    message="OCI Network Path Analyzer did not return a work request ID.",
                )

            work_request = self._wait_for_work_request(client, work_request_id)
            work_status = str(getattr(work_request, "status", "") or "").upper()
            if work_status not in _TERMINAL_WORK_REQUEST_STATES:
                return ConnectivityCheckResponse(
                    status="running",
                    reachable=None,
                    work_request_id=work_request_id,
                    message=(
                        "OCI Network Path Analyzer is still running. "
                        "No Flow Logs were enabled; rerun the check in a moment for the final path result."
                    ),
                    next_actions=["Rerun the connectivity check in a moment to retrieve a completed path analysis result."],
                )
            if work_status != "SUCCEEDED":
                errors = self._work_request_errors(client, work_request_id)
                message = self._primary_message(errors) or f"OCI Network Path Analyzer work request ended with {work_status or 'unknown status'}."
                findings = self._user_findings(errors)
                return ConnectivityCheckResponse(
                    status="failed",
                    reachable=False,
                    work_request_id=work_request_id,
                    message=message,
                    findings=findings,
                    next_actions=self._next_actions(errors or [message], None, None),
                )

            return self._result_response(client, work_request_id)
        except Exception as exc:  # pragma: no cover - specific OCI exceptions vary by SDK/client version
            message = self._error_message(exc)
            user_message = self._primary_message([message]) or f"OCI Network Path Analyzer failed: {message}"
            return ConnectivityCheckResponse(
                status="failed",
                reachable=False,
                message=user_message,
                findings=self._user_findings([message]),
                next_actions=self._next_actions([message], None, None),
            )

    def _compartment_id(self, request: ConnectivityCheckRequest) -> str | None:
        return request.compartment_id or (self.settings.compartment_ids[0] if self.settings.compartment_ids else None) or self.settings.tenancy_ocid

    def _protocol_number(self, protocol: str) -> int:
        return _PROTOCOL_NUMBERS[str(protocol).upper()]

    def _protocol_parameters(self, request: ConnectivityCheckRequest) -> Any | None:
        protocol = str(request.protocol).upper()
        if protocol in {"TCP", "6"}:
            return self.client_factory.vn_monitoring_model(
                "TcpProtocolParameters",
                type="TCP",
                source_port=request.source_port,
                destination_port=request.destination_port,
            )
        if protocol in {"UDP", "17"}:
            return self.client_factory.vn_monitoring_model(
                "UdpProtocolParameters",
                type="UDP",
                source_port=request.source_port,
                destination_port=request.destination_port,
            )
        if protocol in {"ICMP", "1"}:
            return self.client_factory.vn_monitoring_model("IcmpProtocolParameters", type="ICMP")
        return None

    def _endpoint(self, endpoint: ConnectivityEndpoint) -> Any:
        endpoint_type = endpoint.type.lower()
        if endpoint_type == "ip_address":
            ip_address(endpoint.value)
            return self.client_factory.vn_monitoring_model(
                "IpAddressEndpoint",
                type="IP_ADDRESS",
                address=endpoint.value,
            )
        if endpoint_type == "compute_instance":
            return self.client_factory.vn_monitoring_model(
                "ComputeInstanceEndpoint",
                type="COMPUTE_INSTANCE",
                instance_id=endpoint.value,
                address=endpoint.address,
            )
        if endpoint_type == "vnic":
            return self.client_factory.vn_monitoring_model(
                "VnicEndpoint",
                type="VNIC",
                vnic_id=endpoint.value,
                address=endpoint.address,
            )
        if endpoint_type == "subnet":
            return self.client_factory.vn_monitoring_model(
                "SubnetEndpoint",
                type="SUBNET",
                subnet_id=endpoint.value,
                address=endpoint.address,
            )
        raise ValueError(f"Unsupported endpoint type: {endpoint.type}")

    def _work_request_id(self, response: Any) -> str | None:
        headers = getattr(response, "headers", {}) or {}
        return headers.get("opc-work-request-id") or headers.get("Opc-Work-Request-Id") or headers.get("OPC-WORK-REQUEST-ID")

    def _wait_for_work_request(self, client: Any, work_request_id: str) -> Any:
        deadline = time.monotonic() + _WORK_REQUEST_WAIT_SECONDS
        last_response = None
        while time.monotonic() < deadline:
            last_response = client.get_work_request(work_request_id).data
            status = str(getattr(last_response, "status", "") or "").upper()
            if status in _TERMINAL_WORK_REQUEST_STATES:
                return last_response
            time.sleep(1)
        return last_response

    def _work_request_errors(self, client: Any, work_request_id: str) -> list[str]:
        try:
            response = client.list_work_request_errors(work_request_id)
        except Exception:
            return []
        return [
            str(getattr(item, "message", None) or getattr(item, "code", None) or item)
            for item in self._items(response)
        ]

    def _result_response(self, client: Any, work_request_id: str) -> ConnectivityCheckResponse:
        results = self._items(client.list_work_request_results(work_request_id))
        paths = [path for result in results for path in list(getattr(result, "paths", []) or [])]
        if not paths:
            return ConnectivityCheckResponse(
                status="unknown",
                reachable=None,
                work_request_id=work_request_id,
                message="OCI Network Path Analyzer completed without returning a path result.",
            )

        path = paths[0]
        forward = getattr(path, "forward_route", None)
        return_route = getattr(path, "return_route", None)
        forward_status = self._status_value(getattr(forward, "reachability_status", None))
        return_status = self._status_value(getattr(return_route, "reachability_status", None))
        route_statuses = [item for item in [forward_status, return_status] if item]
        reachable = bool(route_statuses) and all(status in {"REACHABLE", "REACHABILITY_STATUS_REACHABLE"} for status in route_statuses)
        findings = self._findings(forward=forward, return_route=return_route)
        next_actions = self._next_actions(findings, forward_status, return_status)
        status = "reachable" if reachable else "blocked"
        return ConnectivityCheckResponse(
            status=status,
            reachable=reachable,
            work_request_id=work_request_id,
            forward_status=forward_status,
            return_status=return_status,
            message=(
                "OCI Network Path Analyzer reports the selected path is reachable."
                if reachable
                else "OCI Network Path Analyzer found a blocked or incomplete path."
            ),
            findings=findings,
            next_actions=next_actions,
            hops=self._hops(forward),
        )

    def _items(self, response: Any) -> list[Any]:
        data = getattr(response, "data", response)
        if isinstance(data, list):
            return data
        for attr in ("items", "results"):
            value = getattr(data, attr, None)
            if isinstance(value, list):
                return value
        return []

    def _findings(self, forward: Any, return_route: Any) -> list[str]:
        findings: list[str] = []
        for label, route in [("forward", forward), ("return", return_route)]:
            if route is None:
                continue
            description = getattr(route, "route_analysis_description", None)
            status = self._status_value(getattr(route, "reachability_status", None))
            if description:
                findings.append(f"{label}: {description}")
            elif status and status not in {"REACHABLE", "REACHABILITY_STATUS_REACHABLE"}:
                findings.append(f"{label}: {status}")
            for node in list(getattr(route, "nodes", []) or []):
                for action_attr in ("next_hop_routing_action", "egress_security_action", "ingress_security_action"):
                    action = getattr(node, action_attr, None)
                    action_value = getattr(action, "action", None)
                    if action_value and str(action_value).upper() not in {"ALLOW", "ALLOWED", "ROUTE", "FORWARD"}:
                        findings.append(f"{label}: {action_attr.replace('_', ' ')} {action_value}")
        return findings[:12]

    def _next_actions(self, findings: list[str], forward_status: str | None, return_status: str | None) -> list[str]:
        text = " ".join(findings).lower()
        actions: list[str] = []
        if "network path analyzer" in text and "more than 100 compartments" in text:
            actions.append("Request an OCI Network Path Analyzer service limit increase for the tenancy compartment count, then rerun the check.")
        elif "limit increase" in text and "compartment" in text:
            actions.append("Review OCI Network Path Analyzer service limits for this tenancy and request the required compartment-count increase.")
        if "security" in text or "ingress" in text or "egress" in text or "deny" in text:
            actions.append("Review source egress and destination ingress rules for the selected protocol and port.")
        if "route" in text or "no_route" in text or "blackhole" in text:
            actions.append("Review subnet route tables, DRG attachments, and return-path routes for both endpoints.")
        if forward_status and return_status and forward_status != return_status:
            actions.append("Compare forward and return paths; asymmetric routing can pass one direction and fail the other.")
        if not actions:
            actions.append("Use the path hops to inspect the first denied security action or missing route target.")
        actions.append("Enable Flow Logs only if packet-level evidence is still needed after this path analysis.")
        return actions[:5]

    def _primary_message(self, findings: list[str]) -> str | None:
        text = " ".join(findings)
        normalized = text.lower()
        if "network path analyzer" in normalized and "more than 100 compartments" in normalized:
            return (
                "Connectivity check could not complete because this tenancy has more compartments than the current "
                "OCI Network Path Analyzer service limit."
            )
        if "limit increase" in normalized and "compartment" in normalized:
            return "Connectivity check could not complete because OCI Network Path Analyzer needs a service limit increase."
        return None

    def _user_findings(self, findings: list[str]) -> list[str]:
        primary = self._primary_message(findings)
        if primary:
            return [primary]
        compact: list[str] = []
        for finding in findings:
            value = " ".join(str(finding).split())
            if value and value not in compact:
                compact.append(value)
        return compact[:6]

    def _hops(self, route: Any) -> list[ConnectivityHop]:
        hops: list[ConnectivityHop] = []
        for index, node in enumerate(list(getattr(route, "nodes", []) or []), start=1):
            hops.append(
                ConnectivityHop(
                    index=index,
                    entity_id=getattr(node, "entity_id", None),
                    node_type=getattr(node, "type", None),
                    route_action=self._action_value(getattr(node, "next_hop_routing_action", None)),
                    egress_action=self._action_value(getattr(node, "egress_security_action", None)),
                    ingress_action=self._action_value(getattr(node, "ingress_security_action", None)),
                    description=getattr(node, "transformation_description", None),
                )
            )
        return hops[:40]

    def _action_value(self, action: Any) -> str | None:
        return self._status_value(getattr(action, "action", None))

    def _status_value(self, value: Any) -> str | None:
        return str(value).upper() if value is not None else None

    def _error_message(self, exc: Exception) -> str:
        message = getattr(exc, "message", None) or str(exc)
        code = getattr(exc, "code", None)
        status = getattr(exc, "status", None)
        parts = [str(part) for part in [status, code, message] if part]
        return " / ".join(parts) if parts else exc.__class__.__name__
