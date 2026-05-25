from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_returns_ok():
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_is_ready_without_live_oci():
    client = TestClient(create_app())

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["live_oci_enabled"] is False


def test_version_returns_deployment_metadata():
    client = TestClient(create_app())

    response = client.get("/api/version")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "Meridian API"
    assert body["version"] == "0.1.0"
    assert body["revision"]
    assert "built_at" in body
    assert body["dirty"] is False
