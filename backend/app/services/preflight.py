from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.models import PreflightCheck, PreflightSummary
from app.oci_clients import OciClientError, OciClientFactory


NETWORK_READ_CHECKS: tuple[tuple[str, str, str], ...] = (
    (
        "VCN inventory",
        "list_vcns",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
    (
        "Subnet inventory",
        "list_subnets",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
    (
        "Route table inventory",
        "list_route_tables",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
    (
        "Security list inventory",
        "list_security_lists",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
    (
        "Internet Gateway inventory",
        "list_internet_gateways",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
    (
        "NAT Gateway inventory",
        "list_nat_gateways",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
    (
        "Service Gateway inventory",
        "list_service_gateways",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
    (
        "DRG inventory",
        "list_drgs",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
    (
        "Network Security Group inventory",
        "list_network_security_groups",
        "Grant read virtual-network-family in the monitored compartment or tenancy.",
    ),
)


@dataclass(frozen=True)
class PreflightService:
    settings: Settings
    client_factory: OciClientFactory

    def summarize(self) -> PreflightSummary:
        checks = self._configuration_checks()
        if self.settings.enable_live_oci and self.settings.tenancy_ocid:
            checks.extend(self._oci_checks())

        return PreflightSummary(
            status=self._summary_status(checks),
            live_oci_enabled=self.settings.enable_live_oci,
            auth_mode=self.settings.oci_auth,
            home_region=self.settings.home_region,
            active_regions=self._target_regions(),
            tenancy_configured=bool(self.settings.tenancy_ocid),
            compartment_ids=self._target_compartments(),
            checks=checks,
        )

    def _configuration_checks(self) -> list[PreflightCheck]:
        checks = [
            PreflightCheck(
                name="Live OCI mode",
                status="pass" if self.settings.enable_live_oci else "skipped",
                message="Live OCI calls are enabled."
                if self.settings.enable_live_oci
                else "Live OCI calls are disabled; the dashboard can run with demo or empty API data.",
                action=None if self.settings.enable_live_oci else "Set MERIDIAN_ENABLE_LIVE_OCI=true for production.",
            ),
            PreflightCheck(
                name="Tenancy OCID",
                status="pass" if self.settings.tenancy_ocid else "fail",
                message="Tenancy OCID is configured."
                if self.settings.tenancy_ocid
                else "MERIDIAN_TENANCY_OCID is missing.",
                action=None if self.settings.tenancy_ocid else "Set MERIDIAN_TENANCY_OCID to the customer tenancy OCID.",
            ),
            PreflightCheck(
                name="Authentication mode",
                status="pass",
                message=f"Runtime auth mode is {self.settings.oci_auth}.",
                action=None,
            ),
            PreflightCheck(
                name="Region scope",
                status="pass",
                message=f"Home region {self.settings.home_region} plus {len(self._other_regions())} additional region(s).",
                action=None,
            ),
            PreflightCheck(
                name="Compartment scope",
                status="pass" if self._target_compartments() else "fail",
                message=f"{len(self._target_compartments())} compartment scope value(s) configured."
                if self._target_compartments()
                else "No monitored compartment scope can be derived.",
                action=None
                if self._target_compartments()
                else "Set MERIDIAN_COMPARTMENT_IDS or MERIDIAN_TENANCY_OCID.",
            ),
        ]
        if not self.settings.enable_live_oci:
            checks[1].status = "skipped" if not self.settings.tenancy_ocid else checks[1].status
            checks[4].status = "skipped" if not self._target_compartments() else checks[4].status
        return checks

    def _oci_checks(self) -> list[PreflightCheck]:
        checks: list[PreflightCheck] = []
        identity_client = self._checked_call(
            name="OCI SDK and signer",
            action="Install the OCI SDK and verify the selected auth mode can create a signer.",
            call=self.client_factory.identity_client,
        )
        checks.append(identity_client.check)
        if identity_client.result is None:
            return checks

        checks.append(
            self._checked_call(
                name="Compartment discovery permission",
                action="Grant inspect compartments in tenancy to the Meridian dynamic group or user.",
                call=identity_client.result.list_compartments,
                compartment_id=self.settings.tenancy_ocid,
                compartment_id_in_subtree=True,
                access_level="ACCESSIBLE",
                limit=1,
            ).check
        )

        for region in self._target_regions():
            client_result = self._checked_call(
                name=f"{region} network client",
                action=f"Verify the tenancy is subscribed to {region} and the auth mode can create a network client.",
                call=self.client_factory.virtual_network_client,
                region=region,
            )
            checks.append(client_result.check)
            if client_result.result is None:
                continue
            checks.extend(self._network_permission_checks(region=region, client=client_result.result))
        return checks

    def _network_permission_checks(self, region: str, client: object) -> list[PreflightCheck]:
        checks: list[PreflightCheck] = []
        for compartment_id in self._target_compartments():
            for label, method_name, action in NETWORK_READ_CHECKS:
                method = getattr(client, method_name, None)
                if method is None:
                    checks.append(
                        PreflightCheck(
                            name=f"{region} / {label}",
                            status="skipped",
                            message=f"The OCI SDK client does not expose {method_name}.",
                            action="Upgrade the OCI SDK package if this resource type is needed.",
                        )
                    )
                    continue
                result = self._checked_call(
                    name=f"{region} / {label}",
                    action=action,
                    call=method,
                    compartment_id=compartment_id,
                    limit=1,
                )
                checks.append(result.check)
                if method_name == "list_network_security_groups":
                    checks.extend(self._network_security_group_rule_check(region, client, result.result, action))
        return checks

    def _network_security_group_rule_check(
        self,
        region: str,
        client: object,
        result: object | None,
        action: str,
    ) -> list[PreflightCheck]:
        nsg_id = self._first_resource_id(result)
        if not nsg_id:
            return []

        method = getattr(client, "list_network_security_group_security_rules", None)
        if method is None:
            return [
                PreflightCheck(
                    name=f"{region} / Network Security Group rule inventory",
                    status="skipped",
                    message="The OCI SDK client does not expose list_network_security_group_security_rules.",
                    action="Upgrade the OCI SDK package if NSG rule inventory is needed.",
                )
            ]
        return [
            self._checked_call(
                f"{region} / Network Security Group rule inventory",
                action,
                method,
                nsg_id,
                limit=1,
            ).check
        ]

    def _checked_call(
        self,
        name: str,
        action: str,
        call: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> "_CheckedCall":
        try:
            result = call(*args, **kwargs)
        except Exception as exc:
            return _CheckedCall(
                check=PreflightCheck(
                    name=name,
                    status="fail",
                    message=self._exception_message(exc),
                    action=action,
                ),
                result=None,
            )
        return _CheckedCall(
            check=PreflightCheck(
                name=name,
                status="pass",
                message="Validated successfully.",
                action=None,
            ),
            result=result,
        )

    def _target_regions(self) -> list[str]:
        return list(dict.fromkeys([self.settings.home_region, *self.settings.active_regions]))

    def _other_regions(self) -> list[str]:
        return [region for region in self._target_regions() if region != self.settings.home_region]

    def _target_compartments(self) -> list[str]:
        selected = self.settings.compartment_ids or ([self.settings.tenancy_ocid] if self.settings.tenancy_ocid else [])
        return list(dict.fromkeys(selected))

    def _first_resource_id(self, result: object | None) -> str | None:
        data = getattr(result, "data", result)
        if not data:
            return None
        if isinstance(data, list) and data:
            return getattr(data[0], "id", None)
        return None

    def _summary_status(self, checks: list[PreflightCheck]) -> str:
        if not self.settings.enable_live_oci:
            return "skipped"
        active_statuses = [check.status for check in checks if check.status != "skipped"]
        if not active_statuses:
            return "skipped"
        if any(status == "fail" for status in active_statuses):
            return "fail"
        if any(status == "warn" for status in active_statuses):
            return "warn"
        return "pass"

    def _exception_message(self, exc: Exception) -> str:
        if isinstance(exc, OciClientError):
            return str(exc)

        status = getattr(exc, "status", None)
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", None) or str(exc)
        if status in (401, 403) or code == "NotAuthorizedOrNotFound":
            return f"OCI authorization failed ({code or status}): {message}"
        if status == 404:
            return f"OCI resource or service was not found ({code or status}): {message}"
        return f"{type(exc).__name__}: {message}"


@dataclass(frozen=True)
class _CheckedCall:
    check: PreflightCheck
    result: Any | None
