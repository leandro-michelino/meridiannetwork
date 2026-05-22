from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.regions import RegionService


class OciObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeIdentityClient:
    def list_region_subscriptions(self, tenancy_id):
        return tenancy_id


class FakeClientFactory:
    def identity_client(self):
        return FakeIdentityClient()

    def list_all(self, list_func, *args, **kwargs):
        if list_func.__name__ == "list_region_subscriptions":
            return [
                OciObject(region_name="me-abudhabi-1", status="READY", is_home_region=True),
                OciObject(region_name="uk-london-1", status="READY", is_home_region=False),
                OciObject(region_name="eu-test-1", status="IN_PROGRESS", is_home_region=False),
            ]
        return []


def test_available_regions_includes_home_region():
    client = TestClient(create_app())

    response = client.get("/api/regions/available")

    assert response.status_code == 200
    regions = response.json()
    assert any(region["id"] == "eu-frankfurt-1" and region["is_home_region"] for region in regions)


def test_active_regions_defaults_to_home_region():
    client = TestClient(create_app())

    response = client.get("/api/regions/active")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "eu-frankfurt-1",
            "geo": "Europe",
            "is_home_region": True,
            "is_active": True,
        }
    ]


def test_home_region_is_always_active_even_when_not_configured_as_active_region():
    service = RegionService(
        settings=Settings(
            home_region="eu-madrid-1",
            active_regions=["eu-frankfurt-1"],
        )
    )

    regions = service.list_available()

    assert any(region.id == "eu-madrid-1" and region.is_home_region and region.is_active for region in regions)


def test_live_available_regions_uses_region_subscriptions():
    service = RegionService(
        settings=Settings(
            enable_live_oci=True,
            tenancy_ocid="tenancy-1",
            home_region="me-abudhabi-1",
            active_regions=["me-abudhabi-1"],
        ),
        client_factory=FakeClientFactory(),
    )

    regions = service.list_available()

    assert [region.id for region in regions] == ["me-abudhabi-1", "eu-test-1", "uk-london-1"]
    assert regions[0].is_home_region is True
    assert regions[1].is_active is False
    assert regions[2].geo == "Europe"


def test_compartments_returns_empty_without_configured_tenancy():
    client = TestClient(create_app())

    response = client.get("/api/compartments")

    assert response.status_code == 200
    assert response.json() == []
