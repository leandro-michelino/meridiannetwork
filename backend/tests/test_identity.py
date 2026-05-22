from fastapi.testclient import TestClient


def test_identity_context_returns_disabled_state():
    from app.main import create_app
    client = TestClient(create_app())
    response = client.get("/api/identity/context")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["user_required"] is True
    assert body["is_authorized"] is False
    assert "message" in body
