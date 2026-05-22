from fastapi.testclient import TestClient


def test_export_security_posture_csv_returns_csv():
    from app.main import create_app
    client = TestClient(create_app())
    response = client.get("/api/export/security-posture.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.splitlines()
    assert lines[0].startswith("severity,rule_type")


def test_export_inventory_csv_returns_csv():
    from app.main import create_app
    client = TestClient(create_app())
    response = client.get("/api/export/inventory.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.splitlines()
    assert lines[0].startswith("resource_type,name")


def test_export_security_posture_csv_accepts_region_filter():
    from app.main import create_app
    client = TestClient(create_app())
    response = client.get("/api/export/security-posture.csv?regions=me-abudhabi-1")
    assert response.status_code == 200
