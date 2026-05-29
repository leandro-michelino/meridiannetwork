from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import ConnectivityCheckRequest, ConnectivityEndpoint
from app.services import connectivity as connectivity_module
from app.services.connectivity import ConnectivityService


class OciObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class OciResponse:
    def __init__(self, data=None, headers=None):
        self.data = data
        self.headers = headers or {}


class FakeVnMonitoringClient:
    def __init__(self, reachable=True, fail=False, work_status="SUCCEEDED"):
        self.reachable = reachable
        self.fail = fail
        self.work_status = work_status
        self.path_analysis_details = None

    def get_path_analysis(self, get_path_analysis_details):
        if self.fail:
            raise RuntimeError("missing Network Path Analyzer permission")
        self.path_analysis_details = get_path_analysis_details
        return OciResponse(headers={"opc-work-request-id": "wr-1"})

    def get_work_request(self, work_request_id):
        return OciResponse(OciObject(status=self.work_status))

    def list_work_request_results(self, work_request_id):
        reachability = "REACHABLE" if self.reachable else "NOT_REACHABLE"
        path = OciObject(
            forward_route=OciObject(
                reachability_status=reachability,
                route_analysis_description="Security rules allow the path." if self.reachable else "Ingress security rule blocks the path.",
                nodes=[
                    OciObject(
                        type="VISIBLE",
                        entity_id="subnet-1",
                        next_hop_routing_action=OciObject(action="ALLOW"),
                        egress_security_action=OciObject(action="ALLOW"),
                        ingress_security_action=OciObject(action="ALLOW" if self.reachable else "DENY"),
                    )
                ],
            ),
            return_route=OciObject(
                reachability_status=reachability,
                route_analysis_description=None,
                nodes=[],
            ),
        )
        return OciResponse([OciObject(paths=[path])])

    def list_work_request_errors(self, work_request_id):
        return OciResponse([])


class FakeFactory:
    def __init__(self, reachable=True, fail=False, work_status="SUCCEEDED"):
        self.client = FakeVnMonitoringClient(reachable=reachable, fail=fail, work_status=work_status)

    def vn_monitoring_client(self, region=None):
        return self.client

    def vn_monitoring_model(self, name, **kwargs):
        return OciObject(**kwargs)


def test_connectivity_endpoint_returns_disabled_without_live_oci():
    client = TestClient(create_app())

    response = client.post(
        "/api/connectivity/check",
        json={
            "source": {"type": "ip_address", "value": "10.0.0.10"},
            "destination": {"type": "ip_address", "value": "10.0.1.20"},
            "protocol": "TCP",
            "destination_port": 443,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "disabled"


def test_connectivity_service_uses_oci_network_path_analyzer():
    factory = FakeFactory(reachable=True)
    service = ConnectivityService(
        settings=Settings(
            enable_live_oci=True,
            tenancy_ocid="tenancy-1",
            active_regions=["eu-frankfurt-1"],
            compartment_ids=["compartment-1"],
        ),
        client_factory=factory,
    )

    result = service.check(
        ConnectivityCheckRequest(
            source=ConnectivityEndpoint(type="ip_address", value="10.0.0.10"),
            destination=ConnectivityEndpoint(type="ip_address", value="10.0.1.20"),
            protocol="TCP",
            destination_port=443,
            bidirectional=True,
        )
    )

    assert result.status == "reachable"
    assert result.reachable is True
    assert result.work_request_id == "wr-1"
    assert factory.client.path_analysis_details.protocol == 6
    assert factory.client.path_analysis_details.protocol_parameters.destination_port == 443
    assert factory.client.path_analysis_details.query_options.is_bi_directional_analysis is True


def test_connectivity_service_reports_blocked_path_findings():
    service = ConnectivityService(
        settings=Settings(
            enable_live_oci=True,
            tenancy_ocid="tenancy-1",
            active_regions=["eu-frankfurt-1"],
            compartment_ids=["compartment-1"],
        ),
        client_factory=FakeFactory(reachable=False),
    )

    result = service.check(
        ConnectivityCheckRequest(
            source=ConnectivityEndpoint(type="ip_address", value="10.0.0.10"),
            destination=ConnectivityEndpoint(type="ip_address", value="10.0.1.20"),
            protocol="TCP",
            destination_port=443,
        )
    )

    assert result.status == "blocked"
    assert result.reachable is False
    assert any("Ingress security rule blocks" in finding for finding in result.findings)
    assert any("ingress rules" in action for action in result.next_actions)
    assert any("Flow Logs only" in action for action in result.next_actions)
    assert any(hop.ingress_action == "DENY" for hop in result.hops)


def test_connectivity_service_returns_actionable_failure_for_oci_errors():
    service = ConnectivityService(
        settings=Settings(
            enable_live_oci=True,
            tenancy_ocid="tenancy-1",
            active_regions=["eu-frankfurt-1"],
            compartment_ids=["compartment-1"],
        ),
        client_factory=FakeFactory(fail=True),
    )

    result = service.check(
        ConnectivityCheckRequest(
            source=ConnectivityEndpoint(type="ip_address", value="10.0.0.10"),
            destination=ConnectivityEndpoint(type="ip_address", value="10.0.1.20"),
            protocol="TCP",
            destination_port=443,
        )
    )

    assert result.status == "failed"
    assert result.reachable is False
    assert "Network Path Analyzer failed" in result.message
    assert any("Flow Logs only" in action for action in result.next_actions)


def test_connectivity_service_suggests_limit_increase_for_large_tenancy():
    service = ConnectivityService(
        settings=Settings(enable_live_oci=True, tenancy_ocid="tenancy-1", compartment_ids=["compartment-1"]),
        client_factory=FakeFactory(),
    )

    actions = service._next_actions(
        [
            "The tenancy has more than 100 compartments. Network Path Analyzer default limits does not support tenancies that have more than 100 compartments. Submit a limit increase request."
        ],
        None,
        None,
    )

    assert any("service limit increase" in action for action in actions)


def test_connectivity_service_returns_running_before_proxy_timeout(monkeypatch):
    monkeypatch.setattr(connectivity_module, "_WORK_REQUEST_WAIT_SECONDS", 0.01)
    service = ConnectivityService(
        settings=Settings(enable_live_oci=True, tenancy_ocid="tenancy-1", compartment_ids=["compartment-1"]),
        client_factory=FakeFactory(work_status="IN_PROGRESS"),
    )

    result = service.check(
        ConnectivityCheckRequest(
            source=ConnectivityEndpoint(type="ip_address", value="10.0.0.10"),
            destination=ConnectivityEndpoint(type="ip_address", value="10.0.1.20"),
            protocol="TCP",
            destination_port=443,
        )
    )

    assert result.status == "running"
    assert result.reachable is None
    assert result.work_request_id == "wr-1"
    assert "still running" in result.message
