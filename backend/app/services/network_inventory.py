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
    TopologyEdge,
    TopologyGraph,
    TopologyNode,
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
                            route_table_id=getattr(item, "route_table_id", None),
                            security_list_ids=list(getattr(item, "security_list_ids", None) or []),
                            time_created=_timestamp(item.time_created),
                        )
                    )
        return results

    def get_topology(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_id: str | None = None,
    ) -> TopologyGraph:
        vcns = self.list_vcns(regions=regions, compartment_ids=compartment_ids)
        subnets = self.list_subnets(regions=regions, compartment_ids=compartment_ids, vcn_id=vcn_id)
        gateways = self.list_gateways(regions=regions, compartment_ids=compartment_ids, vcn_id=vcn_id)
        route_tables = self.list_route_tables(regions=regions, compartment_ids=compartment_ids, vcn_id=vcn_id)
        security_lists = self.list_security_lists(regions=regions, compartment_ids=compartment_ids, vcn_id=vcn_id)

        selected_vcn_ids = {vcn_id} if vcn_id else {vcn.id for vcn in vcns}
        nodes: list[TopologyNode] = []
        edges: list[TopologyEdge] = []
        edge_keys: set[tuple[str, str, str]] = set()

        for vcn in vcns:
            if selected_vcn_ids and vcn.id not in selected_vcn_ids:
                continue
            nodes.append(
                TopologyNode(
                    id=vcn.id,
                    name=vcn.name,
                    resource_type="vcn",
                    region=vcn.region,
                    compartment_id=vcn.compartment_id,
                    lifecycle_state=vcn.lifecycle_state,
                    metadata={"cidr_blocks": ", ".join(vcn.cidr_blocks), "dns_label": vcn.dns_label or ""},
                )
            )

        for subnet in subnets:
            if selected_vcn_ids and subnet.vcn_id not in selected_vcn_ids:
                continue
            nodes.append(
                TopologyNode(
                    id=subnet.id,
                    name=subnet.name,
                    resource_type="subnet",
                    region=subnet.region,
                    compartment_id=subnet.compartment_id,
                    vcn_id=subnet.vcn_id,
                    lifecycle_state=subnet.lifecycle_state,
                    metadata={
                        "cidr_block": subnet.cidr_block,
                        "subnet_access": "private"
                        if subnet.prohibit_public_ip_on_vnic is True
                        else "public"
                        if subnet.prohibit_public_ip_on_vnic is False
                        else "unknown",
                    },
                )
            )
            self._add_topology_edge(edges, edge_keys, subnet.vcn_id, subnet.id, "contains_subnet")
            if subnet.route_table_id:
                self._add_topology_edge(edges, edge_keys, subnet.id, subnet.route_table_id, "uses_route_table")
            for security_list_id in subnet.security_list_ids:
                self._add_topology_edge(edges, edge_keys, subnet.id, security_list_id, "uses_security_list")

        for gateway in gateways:
            nodes.append(
                TopologyNode(
                    id=gateway.id,
                    name=gateway.name,
                    resource_type=gateway.gateway_type,
                    region=gateway.region,
                    compartment_id=gateway.compartment_id,
                    vcn_id=gateway.vcn_id,
                    lifecycle_state=gateway.lifecycle_state,
                    metadata={"enabled": str(gateway.is_enabled) if gateway.is_enabled is not None else ""},
                )
            )
            if gateway.vcn_id:
                self._add_topology_edge(edges, edge_keys, gateway.vcn_id, gateway.id, "has_gateway")

        for route_table in route_tables:
            if selected_vcn_ids and route_table.vcn_id not in selected_vcn_ids:
                continue
            nodes.append(
                TopologyNode(
                    id=route_table.id,
                    name=route_table.name,
                    resource_type="route_table",
                    region=route_table.region,
                    compartment_id=route_table.compartment_id,
                    vcn_id=route_table.vcn_id,
                    lifecycle_state=route_table.lifecycle_state,
                    metadata={"route_rules": str(len(route_table.route_rules))},
                )
            )
            self._add_topology_edge(edges, edge_keys, route_table.vcn_id, route_table.id, "has_route_table")
            for index, rule in enumerate(route_table.route_rules):
                if rule.network_entity_id:
                    self._add_topology_edge(
                        edges,
                        edge_keys,
                        route_table.id,
                        rule.network_entity_id,
                        "routes_to",
                        {
                            "destination": rule.destination or "",
                            "destination_type": rule.destination_type or "",
                            "rule_index": str(index),
                        },
                    )

        for security_list in security_lists:
            if selected_vcn_ids and security_list.vcn_id not in selected_vcn_ids:
                continue
            nodes.append(
                TopologyNode(
                    id=security_list.id,
                    name=security_list.name,
                    resource_type="security_list",
                    region=security_list.region,
                    compartment_id=security_list.compartment_id,
                    vcn_id=security_list.vcn_id,
                    lifecycle_state=security_list.lifecycle_state,
                    metadata={
                        "ingress_rules": str(len(security_list.ingress_rules)),
                        "egress_rules": str(len(security_list.egress_rules)),
                    },
                )
            )
            self._add_topology_edge(edges, edge_keys, security_list.vcn_id, security_list.id, "has_security_list")

        node_ids = {node.id for node in nodes}
        return TopologyGraph(
            nodes=nodes,
            edges=[edge for edge in edges if edge.source_id in node_ids and edge.target_id in node_ids],
        )

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

    def _add_topology_edge(
        self,
        edges: list[TopologyEdge],
        edge_keys: set[tuple[str, str, str]],
        source_id: str,
        target_id: str,
        relationship: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        key = (source_id, target_id, relationship)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append(
            TopologyEdge(
                id=f"{relationship}:{source_id}:{target_id}",
                source_id=source_id,
                target_id=target_id,
                relationship=relationship,
                metadata=metadata or {},
            )
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
