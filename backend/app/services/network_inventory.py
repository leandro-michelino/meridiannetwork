from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.config import Settings
from app.models import (
    GatewaySummary,
    NetworkSecurityGroupSummary,
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


NETWORK_RESOURCE_SEARCH_QUERIES: tuple[str, ...] = (
    "query vcn resources",
    "query subnet resources",
)


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
class _NetworkResourceScope:
    compartment_ids: list[str]
    regions: list[str]


@dataclass(frozen=True)
class NetworkInventoryService:
    settings: Settings
    client_factory: OciClientFactory
    _compartment_scope_cache: list[str] | None = field(default=None, init=False, repr=False)
    _network_resource_scope_cache: _NetworkResourceScope | None = field(default=None, init=False, repr=False)
    _region_subscription_cache: list[str] | None = field(default=None, init=False, repr=False)
    _inventory_cache: dict[tuple[str, tuple[str, ...], tuple[str, ...], str], list[Any]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _collection_issues: list[dict[str, str]] = field(default_factory=list, init=False, repr=False)

    def reset_collection_issues(self) -> None:
        self._collection_issues.clear()
        self._inventory_cache.clear()

    def collection_issues(self) -> list[dict[str, str]]:
        return list(self._collection_issues)

    def selected_region_ids(self, regions: list[str] | None = None) -> list[str]:
        return self._region_scope(regions)

    def list_vcns(self, regions: list[str] | None = None, compartment_ids: list[str] | None = None) -> list[VcnSummary]:
        if not self.settings.enable_live_oci:
            return []

        selected_compartments = self._compartment_scope(compartment_ids)
        selected_regions = self._region_scope(regions)
        cached = self._cached_inventory("vcns", selected_regions, selected_compartments)
        if cached is not None:
            return cached
        results: list[VcnSummary] = []

        for region in selected_regions:
            client = self._virtual_network_client(region)
            if client is None:
                continue
            for compartment_id in selected_compartments:
                vcns = self._safe_list_all(
                    region=region,
                    resource_type="vcn",
                    issue_compartment_id=compartment_id,
                    list_func=client.list_vcns,
                    compartment_id=compartment_id,
                )
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
        return self._store_inventory("vcns", selected_regions, selected_compartments, results)

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
        cached = self._cached_inventory("subnets", selected_regions, selected_compartments, vcn_id)
        if cached is not None:
            return cached
        results: list[SubnetSummary] = []

        for region in selected_regions:
            client = self._virtual_network_client(region)
            if client is None:
                continue
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id
                subnets = self._safe_list_all(
                    region=region,
                    resource_type="subnet",
                    issue_compartment_id=compartment_id,
                    list_func=client.list_subnets,
                    **kwargs,
                )
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
        return self._store_inventory("subnets", selected_regions, selected_compartments, results, vcn_id)

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
        network_security_groups = self.list_network_security_groups(
            regions=regions,
            compartment_ids=compartment_ids,
            vcn_id=vcn_id,
        )

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

        for nsg in network_security_groups:
            if selected_vcn_ids and nsg.vcn_id not in selected_vcn_ids:
                continue
            nodes.append(
                TopologyNode(
                    id=nsg.id,
                    name=nsg.name,
                    resource_type="network_security_group",
                    region=nsg.region,
                    compartment_id=nsg.compartment_id,
                    vcn_id=nsg.vcn_id,
                    lifecycle_state=nsg.lifecycle_state,
                    metadata={
                        "ingress_rules": str(len(nsg.ingress_rules)),
                        "egress_rules": str(len(nsg.egress_rules)),
                    },
                )
            )
            self._add_topology_edge(edges, edge_keys, nsg.vcn_id, nsg.id, "has_network_security_group")

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
        cached = self._cached_inventory("gateways", selected_regions, selected_compartments, vcn_id)
        if cached is not None:
            return cached
        results: list[GatewaySummary] = []

        for region in selected_regions:
            client = self._virtual_network_client(region)
            if client is None:
                continue
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id

                results.extend(self._internet_gateways(client, region, **kwargs))
                results.extend(self._nat_gateways(client, region, **kwargs))
                results.extend(self._service_gateways(client, region, **kwargs))
                if not vcn_id:
                    results.extend(self._drgs(client, region, compartment_id))
        return self._store_inventory("gateways", selected_regions, selected_compartments, results, vcn_id)

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
        cached = self._cached_inventory("route_tables", selected_regions, selected_compartments, vcn_id)
        if cached is not None:
            return cached
        results: list[RouteTableSummary] = []

        for region in selected_regions:
            client = self._virtual_network_client(region)
            if client is None:
                continue
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id
                route_tables = self._safe_list_all(
                    region=region,
                    resource_type="route_table",
                    issue_compartment_id=compartment_id,
                    list_func=client.list_route_tables,
                    **kwargs,
                )
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
        return self._store_inventory("route_tables", selected_regions, selected_compartments, results, vcn_id)

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
        cached = self._cached_inventory("security_lists", selected_regions, selected_compartments, vcn_id)
        if cached is not None:
            return cached
        results: list[SecurityListSummary] = []

        for region in selected_regions:
            client = self._virtual_network_client(region)
            if client is None:
                continue
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id
                security_lists = self._safe_list_all(
                    region=region,
                    resource_type="security_list",
                    issue_compartment_id=compartment_id,
                    list_func=client.list_security_lists,
                    **kwargs,
                )
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
        return self._store_inventory("security_lists", selected_regions, selected_compartments, results, vcn_id)

    def list_network_security_groups(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_id: str | None = None,
    ) -> list[NetworkSecurityGroupSummary]:
        if not self.settings.enable_live_oci:
            return []

        selected_compartments = self._compartment_scope(compartment_ids)
        selected_regions = self._region_scope(regions)
        cached = self._cached_inventory("network_security_groups", selected_regions, selected_compartments, vcn_id)
        if cached is not None:
            return cached
        results: list[NetworkSecurityGroupSummary] = []

        for region in selected_regions:
            client = self._virtual_network_client(region)
            if client is None:
                continue
            for compartment_id in selected_compartments:
                kwargs: dict[str, str] = {"compartment_id": compartment_id}
                if vcn_id:
                    kwargs["vcn_id"] = vcn_id
                network_security_groups = self._safe_list_all(
                    region=region,
                    resource_type="network_security_group",
                    issue_compartment_id=compartment_id,
                    list_func=client.list_network_security_groups,
                    **kwargs,
                )
                for item in network_security_groups:
                    security_rules = self._safe_list_all(
                        client.list_network_security_group_security_rules,
                        item.id,
                        region=region,
                        resource_type="network_security_group_rule",
                        issue_compartment_id=item.compartment_id,
                    )
                    results.append(
                        NetworkSecurityGroupSummary(
                            id=item.id,
                            name=item.display_name,
                            region=region,
                            compartment_id=item.compartment_id,
                            vcn_id=item.vcn_id,
                            lifecycle_state=item.lifecycle_state,
                            ingress_rules=[
                                self._security_rule(str(rule.direction).lower(), rule)
                                for rule in security_rules
                                if str(rule.direction).upper() == "INGRESS"
                            ],
                            egress_rules=[
                                self._security_rule(str(rule.direction).lower(), rule)
                                for rule in security_rules
                                if str(rule.direction).upper() == "EGRESS"
                            ],
                            time_created=_timestamp(item.time_created),
                        )
                    )
        return self._store_inventory(
            "network_security_groups",
            selected_regions,
            selected_compartments,
            results,
            vcn_id,
        )

    def _internet_gateways(self, client: object, region: str, **kwargs: str) -> list[GatewaySummary]:
        items = self._safe_list_all(
            region=region,
            resource_type="internet_gateway",
            issue_compartment_id=kwargs["compartment_id"],
            list_func=client.list_internet_gateways,
            **kwargs,
        )
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
        items = self._safe_list_all(
            region=region,
            resource_type="nat_gateway",
            issue_compartment_id=kwargs["compartment_id"],
            list_func=client.list_nat_gateways,
            **kwargs,
        )
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
        items = self._safe_list_all(
            region=region,
            resource_type="service_gateway",
            issue_compartment_id=kwargs["compartment_id"],
            list_func=client.list_service_gateways,
            **kwargs,
        )
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
        items = self._safe_list_all(
            region=region,
            resource_type="dynamic_routing_gateway",
            issue_compartment_id=compartment_id,
            list_func=client.list_drgs,
            compartment_id=compartment_id,
        )
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
        selected = regions or self._default_region_scope()
        return list(dict.fromkeys(selected or [self.settings.home_region]))

    def _compartment_scope(self, compartment_ids: list[str] | None) -> list[str]:
        selected = compartment_ids or self.settings.compartment_ids
        if selected:
            return list(dict.fromkeys(selected))

        if self._compartment_scope_cache is not None:
            return self._compartment_scope_cache

        selected = self._default_compartment_scope()
        if not selected:
            raise OciClientError(
                "At least one compartment_id query value, MERIDIAN_COMPARTMENT_IDS, or MERIDIAN_TENANCY_OCID is "
                "required for live OCI calls."
            )
        object.__setattr__(self, "_compartment_scope_cache", selected)
        return selected

    def _default_compartment_scope(self) -> list[str]:
        if not self.settings.tenancy_ocid:
            return []
        if not self.settings.enable_resource_search_scope:
            return [self.settings.tenancy_ocid]

        search_scope = self._network_resource_search_scope()
        if search_scope.compartment_ids:
            return list(dict.fromkeys([self.settings.tenancy_ocid, *search_scope.compartment_ids]))

        if search_scope.regions:
            return [self.settings.tenancy_ocid]

        client = self.client_factory.identity_client()
        compartments = self.client_factory.list_all(
            client.list_compartments,
            compartment_id=self.settings.tenancy_ocid,
            compartment_id_in_subtree=True,
            access_level="ACCESSIBLE",
        )
        compartment_ids = [
            item.id
            for item in compartments
            if str(getattr(item, "lifecycle_state", "ACTIVE")).upper() == "ACTIVE"
        ]
        return list(dict.fromkeys([self.settings.tenancy_ocid, *compartment_ids]))

    def _default_region_scope(self) -> list[str]:
        if self.settings.enable_live_oci and self.settings.enable_resource_search_scope:
            search_scope = self._network_resource_search_scope()
            if search_scope.regions:
                return search_scope.regions
        return [self.settings.home_region, *self.settings.active_regions]

    def discovered_region_ids(self) -> list[str]:
        if not self.settings.enable_live_oci or not self.settings.enable_resource_search_scope:
            return []
        return self._network_resource_search_scope().regions

    def _network_resource_search_scope(self) -> _NetworkResourceScope:
        if self._network_resource_scope_cache is not None:
            return self._network_resource_scope_cache

        compartment_ids: set[str] = set()
        regions: set[str] = set()
        for search_region in self._subscribed_region_ids():
            try:
                client = self.client_factory.resource_search_client(region=search_region)
            except Exception as exc:
                self._add_collection_issue(
                    region=search_region,
                    resource_type="resource_search",
                    compartment_id=self.settings.tenancy_ocid or "*",
                    exc=exc,
                )
                continue

            for query in NETWORK_RESOURCE_SEARCH_QUERIES:
                try:
                    items = self._resource_search_items(client, query)
                except Exception as exc:
                    self._add_collection_issue(
                        region=search_region,
                        resource_type="resource_search",
                        compartment_id=self.settings.tenancy_ocid or "*",
                        exc=exc,
                    )
                    continue
                for item in items:
                    compartment_id = getattr(item, "compartment_id", None)
                    if compartment_id:
                        compartment_ids.add(str(compartment_id))
                    regions.add(self._region_from_resource_identifier(getattr(item, "identifier", None)) or search_region)

        scope = _NetworkResourceScope(
            compartment_ids=sorted(compartment_ids),
            regions=sorted(regions),
        )
        object.__setattr__(self, "_network_resource_scope_cache", scope)
        return scope

    def _subscribed_region_ids(self) -> list[str]:
        if self._region_subscription_cache is not None:
            return self._region_subscription_cache

        fallback = list(dict.fromkeys([self.settings.home_region, *self.settings.active_regions]))
        if not self.settings.enable_live_oci or not self.settings.tenancy_ocid:
            object.__setattr__(self, "_region_subscription_cache", fallback)
            return fallback

        try:
            client = self.client_factory.identity_client()
            subscriptions = self.client_factory.list_all(
                client.list_region_subscriptions,
                self.settings.tenancy_ocid,
            )
            selected = [
                str(item.region_name)
                for item in subscriptions
                if getattr(item, "region_name", None)
                and str(getattr(item, "status", "READY")).upper() == "READY"
            ]
        except Exception as exc:
            self._add_collection_issue(
                region=self.settings.home_region,
                resource_type="region_subscription",
                compartment_id=self.settings.tenancy_ocid or "*",
                exc=exc,
            )
            selected = fallback

        selected = list(dict.fromkeys(selected or fallback))
        object.__setattr__(self, "_region_subscription_cache", selected)
        return selected

    def _resource_search_items(self, client: object, query: str) -> list[object]:
        details = self.client_factory.structured_search_details(query)
        items: list[object] = []
        page: str | None = None
        while True:
            kwargs: dict[str, object] = {"limit": 500}
            if page:
                kwargs["page"] = page
            response = client.search_resources(details, **kwargs)
            data = getattr(response, "data", None)
            items.extend(list(getattr(data, "items", []) or []))
            headers = getattr(response, "headers", {}) or {}
            page = headers.get("opc-next-page")
            if not page:
                break
        return items

    def _region_from_resource_identifier(self, identifier: object) -> str | None:
        if not identifier:
            return None
        parts = str(identifier).split(".")
        if len(parts) < 4:
            return None
        region = parts[3]
        return region if region and region != "oc1" else None

    def _cached_inventory(
        self,
        resource_type: str,
        regions: list[str],
        compartment_ids: list[str],
        vcn_id: str | None = None,
    ) -> list[Any] | None:
        key = (resource_type, tuple(regions), tuple(compartment_ids), vcn_id or "")
        cached = self._inventory_cache.get(key)
        return list(cached) if cached is not None else None

    def _store_inventory(
        self,
        resource_type: str,
        regions: list[str],
        compartment_ids: list[str],
        results: list[Any],
        vcn_id: str | None = None,
    ) -> list[Any]:
        key = (resource_type, tuple(regions), tuple(compartment_ids), vcn_id or "")
        self._inventory_cache[key] = list(results)
        return results

    def _virtual_network_client(self, region: str) -> object | None:
        try:
            return self.client_factory.virtual_network_client(region=region)
        except Exception as exc:
            self._add_collection_issue(region=region, resource_type="client", compartment_id="*", exc=exc)
            return None

    def _safe_list_all(
        self,
        list_func: object,
        *args: object,
        region: str,
        resource_type: str,
        issue_compartment_id: str,
        **kwargs: object,
    ) -> list[object]:
        try:
            return self.client_factory.list_all(list_func, *args, **kwargs)
        except Exception as exc:
            self._add_collection_issue(
                region=region,
                resource_type=resource_type,
                compartment_id=issue_compartment_id,
                exc=exc,
            )
            return []

    def _add_collection_issue(
        self,
        region: str,
        resource_type: str,
        compartment_id: str,
        exc: Exception,
    ) -> None:
        message = str(exc)[:500] or exc.__class__.__name__
        issue = {
            "region": region,
            "resource_type": resource_type,
            "compartment_id": compartment_id,
            "message": message,
        }
        if issue not in self._collection_issues:
            self._collection_issues.append(issue)
