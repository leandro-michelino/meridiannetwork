from dataclasses import dataclass
from datetime import datetime

from app.config import Settings
from app.models import (
    GatewaySummary,
    RouteRuleSummary,
    RouteTableSummary,
    SecurityListSummary,
    SecurityRuleSummary,
    SubnetSummary,
    VcnSummary,
)
from app.oci_clients import OciClientFactory, OciClientError


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _timestamp(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


@dataclass(frozen=True)
class NetworkInventoryService:
    settings: Settings
    client_factory: OciClientFactory

    def list_vcns(self, regions: list[str] | None = None, compartment_ids: list[str] | None = None) -> list[VcnSummary]:
        if not self.settings.enable_live_oci:
            return []

        selected_compartments = self._compartment_scope(compartment_ids)
        selected_regions = self._region_scope(regions)
        results: list[VcnSummary] = []

        for region in selected_regions:
            client = self.client_factory.virtual_network_client(region=region)
            for compartment_id in selected_compartments:
                vcns = self.client_factory.list_all(client.list_vcns, compartment_id=compartment_id)
                for item in vcns:
                    results.append(
                        VcnSummary(
                            id=item.id,
                            name=item.display_name,
                            cidr_blocks=list(getattr(item, "cidr_blocks", None) or [item.cidr_block]),
                            region=region,
                            compartment_id=item.compartment_id,
                            lifecycle_state=item.lifecycle_state,
                            dns_label=item.dns_label,
                            time_created=_timestamp(item.time_created),
                        )
                    )
        return results

    def list_subnets(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_id: str | None = None,
    ) -> list[SubnetSummary]:
        if not self.settings.enable_live_oci:
            return []

        selected_compartments = self._compartment_scope(compartment_ids)
        selected_regions = self._region_scope(regions)
        results: list[SubnetSummary] = []

        for region in selected_regions:
            client = self.client_factory.virtual_network_client(region=region)
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id
                subnets = self.client_factory.list_all(client.list_subnets, **kwargs)
                for item in subnets:
                    results.append(
                        SubnetSummary(
                            id=item.id,
                            name=item.display_name,
                            cidr_block=item.cidr_block,
                            region=region,
                            compartment_id=item.compartment_id,
                            vcn_id=item.vcn_id,
                            lifecycle_state=item.lifecycle_state,
                            availability_domain=item.availability_domain,
                            dns_label=item.dns_label,
                            prohibit_public_ip_on_vnic=item.prohibit_public_ip_on_vnic,
                            time_created=_timestamp(item.time_created),
                        )
                    )
        return results

    def list_gateways(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_id: str | None = None,
    ) -> list[GatewaySummary]:
        if not self.settings.enable_live_oci:
            return []

        selected_compartments = self._compartment_scope(compartment_ids)
        selected_regions = self._region_scope(regions)
        results: list[GatewaySummary] = []

        for region in selected_regions:
            client = self.client_factory.virtual_network_client(region=region)
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id

                results.extend(self._internet_gateways(client, region, **kwargs))
                results.extend(self._nat_gateways(client, region, **kwargs))
                results.extend(self._service_gateways(client, region, **kwargs))
                if not vcn_id:
                    results.extend(self._drgs(client, region, compartment_id))
        return results

    def list_route_tables(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_id: str | None = None,
    ) -> list[RouteTableSummary]:
        if not self.settings.enable_live_oci:
            return []

        selected_compartments = self._compartment_scope(compartment_ids)
        selected_regions = self._region_scope(regions)
        results: list[RouteTableSummary] = []

        for region in selected_regions:
            client = self.client_factory.virtual_network_client(region=region)
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id
                route_tables = self.client_factory.list_all(client.list_route_tables, **kwargs)
                for item in route_tables:
                    results.append(
                        RouteTableSummary(
                            id=item.id,
                            name=item.display_name,
                            region=region,
                            compartment_id=item.compartment_id,
                            vcn_id=item.vcn_id,
                            lifecycle_state=item.lifecycle_state,
                            route_rules=[
                                RouteRuleSummary(
                                    destination=rule.destination,
                                    destination_type=rule.destination_type,
                                    network_entity_id=rule.network_entity_id,
                                    description=getattr(rule, "description", None),
                                )
                                for rule in item.route_rules
                            ],
                            time_created=_timestamp(item.time_created),
                        )
                    )
        return results

    def list_security_lists(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_id: str | None = None,
    ) -> list[SecurityListSummary]:
        if not self.settings.enable_live_oci:
            return []

        selected_compartments = self._compartment_scope(compartment_ids)
        selected_regions = self._region_scope(regions)
        results: list[SecurityListSummary] = []

        for region in selected_regions:
            client = self.client_factory.virtual_network_client(region=region)
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id
                security_lists = self.client_factory.list_all(client.list_security_lists, **kwargs)
                for item in security_lists:
                    results.append(
                        SecurityListSummary(
                            id=item.id,
                            name=item.display_name,
                            region=region,
                            compartment_id=item.compartment_id,
                            vcn_id=item.vcn_id,
                            lifecycle_state=item.lifecycle_state,
                            ingress_rules=[
                                self._security_rule("ingress", rule) for rule in item.ingress_security_rules
                            ],
                            egress_rules=[self._security_rule("egress", rule) for rule in item.egress_security_rules],
                            time_created=_timestamp(item.time_created),
                        )
                    )
        return results

    def _internet_gateways(self, client: object, region: str, **kwargs: str) -> list[GatewaySummary]:
        items = self.client_factory.list_all(client.list_internet_gateways, **kwargs)
        return [
            GatewaySummary(
                id=item.id,
                name=item.display_name,
                gateway_type="internet_gateway",
                region=region,
                compartment_id=item.compartment_id,
                vcn_id=item.vcn_id,
                lifecycle_state=item.lifecycle_state,
                is_enabled=getattr(item, "is_enabled", None),
                route_table_id=getattr(item, "route_table_id", None),
                time_created=_timestamp(item.time_created),
            )
            for item in items
        ]

    def _nat_gateways(self, client: object, region: str, **kwargs: str) -> list[GatewaySummary]:
        items = self.client_factory.list_all(client.list_nat_gateways, **kwargs)
        return [
            GatewaySummary(
                id=item.id,
                name=item.display_name,
                gateway_type="nat_gateway",
                region=region,
                compartment_id=item.compartment_id,
                vcn_id=item.vcn_id,
                lifecycle_state=item.lifecycle_state,
                is_enabled=not getattr(item, "block_traffic", False),
                route_table_id=getattr(item, "route_table_id", None),
                time_created=_timestamp(item.time_created),
            )
            for item in items
        ]

    def _service_gateways(self, client: object, region: str, **kwargs: str) -> list[GatewaySummary]:
        items = self.client_factory.list_all(client.list_service_gateways, **kwargs)
        return [
            GatewaySummary(
                id=item.id,
                name=item.display_name,
                gateway_type="service_gateway",
                region=region,
                compartment_id=item.compartment_id,
                vcn_id=item.vcn_id,
                lifecycle_state=item.lifecycle_state,
                is_enabled=not getattr(item, "block_traffic", False),
                route_table_id=getattr(item, "route_table_id", None),
                time_created=_timestamp(item.time_created),
            )
            for item in items
        ]

    def _drgs(self, client: object, region: str, compartment_id: str) -> list[GatewaySummary]:
        items = self.client_factory.list_all(client.list_drgs, compartment_id=compartment_id)
        return [
            GatewaySummary(
                id=item.id,
                name=item.display_name,
                gateway_type="dynamic_routing_gateway",
                region=region,
                compartment_id=item.compartment_id,
                vcn_id=None,
                lifecycle_state=item.lifecycle_state,
                is_enabled=None,
                route_table_id=None,
                time_created=_timestamp(item.time_created),
            )
            for item in items
        ]

    def _security_rule(self, direction: str, rule: object) -> SecurityRuleSummary:
        tcp_options = getattr(rule, "tcp_options", None)
        udp_options = getattr(rule, "udp_options", None)
        port_options = tcp_options or udp_options
        destination_port_range = getattr(port_options, "destination_port_range", None)
        source_port_range = getattr(port_options, "source_port_range", None)
        port_range = destination_port_range or source_port_range

        return SecurityRuleSummary(
            direction=direction,
            protocol=rule.protocol,
            source=getattr(rule, "source", None),
            destination=getattr(rule, "destination", None),
            source_type=getattr(rule, "source_type", None),
            destination_type=getattr(rule, "destination_type", None),
            min_port=getattr(port_range, "min", None),
            max_port=getattr(port_range, "max", None),
            description=getattr(rule, "description", None),
            is_stateless=getattr(rule, "is_stateless", None),
        )

    def _region_scope(self, regions: list[str] | None) -> list[str]:
        selected = regions or self.settings.active_regions
        return selected or [self.settings.home_region]

    def _compartment_scope(self, compartment_ids: list[str] | None) -> list[str]:
        selected = compartment_ids or ([self.settings.tenancy_ocid] if self.settings.tenancy_ocid else [])
        if not selected:
            raise OciClientError(
                "At least one compartment_id query value or MERIDIAN_TENANCY_OCID is required for live OCI calls."
            )
        return selected
