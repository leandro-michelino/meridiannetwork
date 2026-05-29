from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import VcnSummary
from app.services.traffic_telemetry import TrafficTelemetryService


class OciObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class OciResponse:
    def __init__(self, data):
        self.data = data


class FakeNetworkInventory:
    def __init__(self):
        self.vcns = [
            VcnSummary(
                id="vcn-1",
                name="app-vcn",
                cidr_blocks=["10.0.0.0/16"],
                region="eu-frankfurt-1",
                compartment_id="compartment-1",
            )
        ]

    def selected_region_ids(self):
        return ["eu-frankfurt-1"]

    def list_vcns(self, regions=None, compartment_ids=None):
        return self.vcns

    def list_subnets(self, regions=None, compartment_ids=None):
        return []


class FakeLoggingManagementClient:
    def __init__(self):
        self.log_groups = []
        self.logs = []

    def list_log_groups(self, **kwargs):
        return self.log_groups

    def list_logs(self, **kwargs):
        return self.logs

    def create_log_group(self, details):
        group = OciObject(id="log-group-1", display_name=details.display_name)
        self.log_groups.append(group)
        return OciResponse(group)

    def create_log(self, log_group_id, create_log_details):
        log = OciObject(
            id="log-1",
            log_group_id=log_group_id,
            display_name=create_log_details.display_name,
            configuration=create_log_details.configuration,
            is_enabled=True,
        )
        self.logs.append(log)
        return OciResponse(log)

    def update_log(self, log_group_id, log_id, update_log_details):
        log = next(item for item in self.logs if item.id == log_id)
        log.is_enabled = update_log_details.is_enabled
        return OciResponse(log)


class FakeVirtualNetworkClient:
    def __init__(self):
        self.capture_filters = []

    def list_capture_filters(self, **kwargs):
        return self.capture_filters

    def create_capture_filter(self, details):
        capture_filter = OciObject(id="capture-filter-1", display_name=details.display_name)
        self.capture_filters.append(capture_filter)
        return OciResponse(capture_filter)


class FakeSearchClient:
    def search_logs(self, details, limit=100):
        return OciResponse(
            OciObject(
                results=[
                    OciObject(
                        data={
                            "logContent": {
                                "data": {
                                    "sourceAddress": "10.0.0.10",
                                    "destinationAddress": "10.0.1.20",
                                    "destinationPort": 443,
                                    "protocol": "6",
                                    "action": "ACCEPT",
                                    "packets": 7,
                                    "bytes": 3200,
                                    "startTime": "2026-05-29T10:00:00Z",
                                }
                            }
                        }
                    )
                ]
            )
        )


class FakeComputeClient:
    def list_instances(self, **kwargs):
        return []

    def list_vnic_attachments(self, **kwargs):
        return []


class FakeFactory:
    def __init__(self):
        self.logging_client = FakeLoggingManagementClient()
        self.network_client = FakeVirtualNetworkClient()

    def logging_management_client(self, region=None):
        return self.logging_client

    def virtual_network_client(self, region=None):
        return self.network_client

    def logging_search_client(self, region=None):
        return FakeSearchClient()

    def compute_client(self, region=None):
        return FakeComputeClient()

    def list_all(self, list_func, *args, **kwargs):
        value = list_func(*args, **kwargs)
        return getattr(value, "data", value)

    def logging_model(self, name, **kwargs):
        return OciObject(**kwargs)

    def core_model(self, name, **kwargs):
        return OciObject(**kwargs)

    def loggingsearch_model(self, name, **kwargs):
        return OciObject(**kwargs)


def test_traffic_status_endpoint_is_disabled_without_live_oci():
    client = TestClient(create_app())

    response = client.get("/api/traffic/telemetry/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disabled"
    assert body["live_oci_enabled"] is False


def test_traffic_enable_endpoint_requires_explicit_enablement():
    client = TestClient(create_app())

    response = client.post("/api/traffic/telemetry/enable", json={})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "TRAFFIC_ENABLEMENT_DISABLED"


def test_traffic_flows_endpoint_returns_disabled_without_live_oci():
    client = TestClient(create_app())

    response = client.get("/api/traffic/flows")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disabled"
    assert body["flows"] == []


def test_traffic_status_skips_vcn_scan_by_default():
    settings = Settings(
        enable_live_oci=True,
        traffic_flow_logs_enablement_allowed=False,
        tenancy_ocid="tenancy-1",
        compartment_ids=["compartment-1"],
        active_regions=["eu-frankfurt-1"],
    )
    service = TrafficTelemetryService(
        settings=settings,
        client_factory=FakeFactory(),
        network_inventory=FakeNetworkInventory(),
    )

    result = service.status()

    assert result.status == "blocked"
    assert result.checked_vcns == 0
    assert result.enablement_allowed is False


def test_traffic_status_can_check_vcn_coverage_when_requested():
    settings = Settings(
        enable_live_oci=True,
        traffic_flow_logs_enablement_allowed=True,
        tenancy_ocid="tenancy-1",
        compartment_ids=["compartment-1"],
        active_regions=["eu-frankfurt-1"],
    )
    factory = FakeFactory()
    service = TrafficTelemetryService(
        settings=settings,
        client_factory=factory,
        network_inventory=FakeNetworkInventory(),
    )

    service.enable(request=OciObject(regions=["eu-frankfurt-1"], compartment_ids=[], vcn_ids=[]))
    result = service.status(check_vcns=True)

    assert result.status == "enabled"
    assert result.checked_vcns == 1
    assert result.enabled_vcns == 1


def test_enablement_creates_log_group_capture_filter_and_flow_log():
    settings = Settings(
        enable_live_oci=True,
        traffic_flow_logs_enablement_allowed=True,
        tenancy_ocid="tenancy-1",
        compartment_ids=["compartment-1"],
        active_regions=["eu-frankfurt-1"],
    )
    factory = FakeFactory()
    service = TrafficTelemetryService(
        settings=settings,
        client_factory=factory,
        network_inventory=FakeNetworkInventory(),
    )

    result = service.enable(request=OciObject(regions=["eu-frankfurt-1"], compartment_ids=[], vcn_ids=[]))

    assert result.status == "enabled"
    assert result.enabled == 1
    assert factory.logging_client.log_groups[0].display_name == "meridian-traffic-flow-logs"
    assert factory.network_client.capture_filters[0].display_name == "meridian-traffic-capture-filter"
    assert factory.logging_client.logs[0].configuration.source.resource == "vcn-1"


def test_flow_query_maps_search_results_to_records():
    settings = Settings(
        enable_live_oci=True,
        tenancy_ocid="tenancy-1",
        compartment_ids=["compartment-1"],
        active_regions=["eu-frankfurt-1"],
    )
    service = TrafficTelemetryService(
        settings=settings,
        client_factory=FakeFactory(),
        network_inventory=FakeNetworkInventory(),
    )

    result = service.list_flows()

    assert result.status == "ok"
    assert result.total_flows == 1
    assert result.flows[0].source_ip == "10.0.0.10"
    assert result.flows[0].destination_ip == "10.0.1.20"
    assert result.flows[0].destination_port == 443


def test_disable_turns_existing_flow_log_off():
    settings = Settings(
        enable_live_oci=True,
        traffic_flow_logs_enablement_allowed=True,
        tenancy_ocid="tenancy-1",
        compartment_ids=["compartment-1"],
        active_regions=["eu-frankfurt-1"],
    )
    factory = FakeFactory()
    service = TrafficTelemetryService(
        settings=settings,
        client_factory=factory,
        network_inventory=FakeNetworkInventory(),
    )

    service.enable(request=OciObject(regions=["eu-frankfurt-1"], compartment_ids=[], vcn_ids=[]))
    result = service.disable(request=OciObject(regions=["eu-frankfurt-1"], compartment_ids=[], vcn_ids=[]))

    assert result.status == "disabled"
    assert result.enabled == 1
    assert factory.logging_client.logs[0].is_enabled is False
