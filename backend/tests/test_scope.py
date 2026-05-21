from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.regions import RegionService


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


def test_compartments_returns_empty_without_configured_tenancy():
    client = TestClient(create_app())

    response = client.get("/api/compartments")

    assert response.status_code == 200
    assert response.json() == []
