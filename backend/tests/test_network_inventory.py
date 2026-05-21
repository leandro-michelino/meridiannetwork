from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.network_inventory import NetworkInventoryService, split_csv


class OciObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeVirtualNetworkClient:
    def list_route_tables(self, **kwargs):
        return kwargs

    def list_security_lists(self, **kwargs):
        return kwargs

    def list_internet_gateways(self, **kwargs):
        return kwargs

    def list_nat_gateways(self, **kwargs):
        return kwargs

    def list_service_gateways(self, **kwargs):
        return kwargs

    def list_drgs(self, **kwargs):
        return kwargs


class FakeClientFactory:
    def virtual_network_client(self, region=None):
        return FakeVirtualNetworkClient()

    def list_all(self, list_func, **kwargs):
        method_name = list_func.__name__
        if method_name == "list_route_tables":
            return [
                OciObject(
                    id="rt-1",
                    display_name="route-table",
                    compartment_id="compartment-1",
                    vcn_id="vcn-1",
                    lifecycle_state="AVAILABLE",
                    route_rules=[
                        OciObject(
                            destination="0.0.0.0/0",
                            destination_type="CIDR_BLOCK",
                            network_entity_id="igw-1",
                            description="default route",
                        )
                    ],
                    time_created=None,
                )
            ]
        if method_name == "list_security_lists":
            return [
                OciObject(
                    id="sl-1",
                    display_name="security-list",
                    compartment_id="compartment-1",
                    vcn_id="vcn-1",
                    lifecycle_state="AVAILABLE",
                    ingress_security_rules=[
                        OciObject(
                            protocol="6",
                            source="0.0.0.0/0",
                            source_type="CIDR_BLOCK",
                            tcp_options=OciObject(
                                destination_port_range=OciObject(min=22, max=22),
                                source_port_range=None,
                            ),
                            udp_options=None,
                            description="ssh",
                            is_stateless=False,
                        )
                    ],
                    egress_security_rules=[
                        OciObject(
                            protocol="all",
                            destination="0.0.0.0/0",
                            destination_type="CIDR_BLOCK",
                            tcp_options=None,
                            udp_options=None,
                            description="egress",
                            is_stateless=False,
                        )
                    ],
                    time_created=None,
                )
            ]
        if method_name == "list_internet_gateways":
            return [
                OciObject(
                    id="igw-1",
                    display_name="internet-gateway",
                    compartment_id="compartment-1",
                    vcn_id="vcn-1",
                    lifecycle_state="AVAILABLE",
                    is_enabled=True,
                    route_table_id=None,
                    time_created=None,
                )
            ]
        if method_name == "list_nat_gateways":
            return [
                OciObject(
                    id="nat-1",
                    display_name="nat-gateway",
                    compartment_id="compartment-1",
                    vcn_id="vcn-1",
                    lifecycle_state="AVAILABLE",
                    block_traffic=False,
                    route_table_id=None,
                    time_created=None,
                )
            ]
        if method_name == "list_service_gateways":
            return [
                OciObject(
                    id="sgw-1",
                    display_name="service-gateway",
                    compartment_id="compartment-1",
                    vcn_id="vcn-1",
                    lifecycle_state="AVAILABLE",
                    block_traffic=False,
                    route_table_id=None,
                    time_created=None,
                )
            ]
        if method_name == "list_drgs":
            return [
                OciObject(
                    id="drg-1",
                    display_name="drg",
                    compartment_id="compartment-1",
                    lifecycle_state="AVAILABLE",
                    time_created=None,
                )
            ]
        return []


def test_split_csv_trims_and_drops_empty_values():
    assert split_csv("eu-frankfurt-1, eu-madrid-1,,") == ["eu-frankfurt-1", "eu-madrid-1"]


def test_vcns_returns_empty_without_live_oci():
    client = TestClient(create_app())

    response = client.get("/api/vcns")

    assert response.status_code == 200
    assert response.json() == []


def test_subnets_returns_empty_without_live_oci():
    client = TestClient(create_app())

    response = client.get("/api/subnets")

    assert response.status_code == 200
    assert response.json() == []


def test_gateways_returns_empty_without_live_oci():
    client = TestClient(create_app())

    response = client.get("/api/gateways")

    assert response.status_code == 200
    assert response.json() == []


def test_gateway_service_maps_supported_gateway_types():
    settings = Settings(
        enable_live_oci=True,
        tenancy_ocid="compartment-1",
        active_regions=["eu-frankfurt-1"],
    )
    service = NetworkInventoryService(settings=settings, client_factory=FakeClientFactory())

    gateways = service.list_gateways(compartment_ids=["compartment-1"], regions=["eu-frankfurt-1"])

    assert [gateway.gateway_type for gateway in gateways] == [
        "internet_gateway",
        "nat_gateway",
        "service_gateway",
        "dynamic_routing_gateway",
    ]
    assert gateways[0].is_enabled is True
    assert gateways[1].is_enabled is True
    assert gateways[2].is_enabled is True
    assert gateways[3].is_enabled is None


def test_route_table_service_maps_route_rules():
    settings = Settings(
        enable_live_oci=True,
        tenancy_ocid="compartment-1",
        active_regions=["eu-frankfurt-1"],
    )
    service = NetworkInventoryService(settings=settings, client_factory=FakeClientFactory())

    route_tables = service.list_route_tables(compartment_ids=["compartment-1"], regions=["eu-frankfurt-1"])

    assert route_tables[0].id == "rt-1"
    assert route_tables[0].route_rules[0].destination == "0.0.0.0/0"
    assert route_tables[0].route_rules[0].network_entity_id == "igw-1"


def test_security_list_service_maps_security_rules():
    settings = Settings(
        enable_live_oci=True,
        tenancy_ocid="compartment-1",
        active_regions=["eu-frankfurt-1"],
    )
    service = NetworkInventoryService(settings=settings, client_factory=FakeClientFactory())

    security_lists = service.list_security_lists(compartment_ids=["compartment-1"], regions=["eu-frankfurt-1"])

    assert security_lists[0].id == "sl-1"
    assert security_lists[0].ingress_rules[0].source == "0.0.0.0/0"
    assert security_lists[0].ingress_rules[0].min_port == 22
    assert security_lists[0].egress_rules[0].destination == "0.0.0.0/0"
