from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.preflight import PreflightService


class FakeServiceError(Exception):
    def __init__(self, status=403, code="NotAuthorizedOrNotFound", message="not authorized"):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


class FakeOciObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeOciResponse:
    def __init__(self, data):
        self.data = data


class FakeIdentityClient:
    def list_compartments(self, **kwargs):
        return []


class FakeVirtualNetworkClient:
    def __init__(self, denied_method=None, include_nsg=False):
        self.denied_method = denied_method
        self.include_nsg = include_nsg

    def _response(self, method_name):
        if method_name == self.denied_method:
            raise FakeServiceError()
        return []

    def list_vcns(self, **kwargs):
        return self._response("list_vcns")

    def list_subnets(self, **kwargs):
        return self._response("list_subnets")

    def list_route_tables(self, **kwargs):
        return self._response("list_route_tables")

    def list_security_lists(self, **kwargs):
        return self._response("list_security_lists")

    def list_internet_gateways(self, **kwargs):
        return self._response("list_internet_gateways")

    def list_nat_gateways(self, **kwargs):
        return self._response("list_nat_gateways")

    def list_service_gateways(self, **kwargs):
        return self._response("list_service_gateways")

    def list_drgs(self, **kwargs):
        return self._response("list_drgs")

    def list_network_security_groups(self, **kwargs):
        if self.denied_method == "list_network_security_groups":
            raise FakeServiceError()
        if self.include_nsg:
            return FakeOciResponse([FakeOciObject(id="nsg-1")])
        return self._response("list_network_security_groups")

    def list_network_security_group_security_rules(self, network_security_group_id, **kwargs):
        return self._response("list_network_security_group_security_rules")


class FakeClientFactory:
    def __init__(self, denied_method=None, include_nsg=False):
        self.denied_method = denied_method
        self.include_nsg = include_nsg

    def identity_client(self):
        return FakeIdentityClient()

    def virtual_network_client(self, region=None):
        return FakeVirtualNetworkClient(denied_method=self.denied_method, include_nsg=self.include_nsg)


def test_preflight_endpoint_is_skipped_without_live_oci():
    client = TestClient(create_app())

    response = client.get("/api/preflight")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "skipped"
    assert payload["live_oci_enabled"] is False
    assert payload["checks"][0]["name"] == "Live OCI mode"


def test_preflight_passes_with_required_identity_and_network_reads():
    settings = Settings(
        enable_live_oci=True,
        tenancy_ocid="ocid1.tenancy.oc1..test",
        compartment_ids=["ocid1.compartment.oc1..app"],
        home_region="eu-frankfurt-1",
        active_regions=["eu-madrid-1"],
    )
    service = PreflightService(settings=settings, client_factory=FakeClientFactory())

    summary = service.summarize()

    assert summary.status == "pass"
    assert summary.active_regions == ["eu-frankfurt-1", "eu-madrid-1"]
    assert summary.compartment_ids == ["ocid1.compartment.oc1..app"]
    assert any(check.name == "Compartment discovery permission" for check in summary.checks)
    assert any(check.name == "eu-frankfurt-1 / Subnet inventory" for check in summary.checks)


def test_preflight_validates_nsg_rules_when_an_nsg_exists():
    settings = Settings(
        enable_live_oci=True,
        tenancy_ocid="ocid1.tenancy.oc1..test",
        compartment_ids=["ocid1.compartment.oc1..app"],
    )
    service = PreflightService(settings=settings, client_factory=FakeClientFactory(include_nsg=True))

    summary = service.summarize()
    nsg_rule_check = next(
        check for check in summary.checks if check.name == "eu-frankfurt-1 / Network Security Group rule inventory"
    )

    assert summary.status == "pass"
    assert nsg_rule_check.status == "pass"


def test_preflight_fails_when_network_permission_is_missing():
    settings = Settings(
        enable_live_oci=True,
        tenancy_ocid="ocid1.tenancy.oc1..test",
        compartment_ids=["ocid1.compartment.oc1..app"],
    )
    service = PreflightService(settings=settings, client_factory=FakeClientFactory(denied_method="list_subnets"))

    summary = service.summarize()
    subnet_check = next(check for check in summary.checks if check.name == "eu-frankfurt-1 / Subnet inventory")

    assert summary.status == "fail"
    assert subnet_check.status == "fail"
    assert "OCI authorization failed" in subnet_check.message
    assert subnet_check.action == "Grant read virtual-network-family in the monitored compartment or tenancy."
