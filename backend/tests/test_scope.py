from fastapi.testclient import TestClient

from app.main import create_app


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


def test_compartments_returns_empty_without_configured_tenancy():
    client = TestClient(create_app())

    response = client.get("/api/compartments")

    assert response.status_code == 200
    assert response.json() == []

