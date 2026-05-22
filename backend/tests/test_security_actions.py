from fastapi.testclient import TestClient

from app.models import SecurityActionRequest
from app.services.security_actions import SecurityActionsService


class _NoOpSettings:
    security_action_object_storage_enabled = False
    security_action_object_storage_namespace = ""
    security_action_object_storage_bucket = ""
    security_action_object_storage_prefix = "meridian/security-actions/"
    security_action_retention_days = 365


class _NoOpClientFactory:
    pass


def _service() -> SecurityActionsService:
    return SecurityActionsService(settings=_NoOpSettings(), client_factory=_NoOpClientFactory())  # type: ignore[arg-type]


def test_list_actions_returns_empty_without_object_storage():
    svc = _service()
    result = svc.list_actions()
    assert result.total_actions == 0
    assert result.actions == []
    assert result.archive_enabled is False
    assert result.storage == "browser-local"


def test_record_action_returns_action_with_id_and_timestamp():
    svc = _service()
    req = SecurityActionRequest(
        finding_key="public_ssh/admin-nsg",
        action_type="remediate",
        user="Alice",
        resource_name="admin-nsg",
        rule_type="public_ssh",
        severity="high",
        region="me-abudhabi-1",
        compartment_id="ocid1.compartment.oc1..test",
        vcn_id="ocid1.vcn.oc1..test",
        description="SSH open to 0.0.0.0/0",
    )
    action = svc.record_action(req)
    assert action.id
    assert action.created_at
    assert action.action_type == "remediate"
    assert action.user == "Alice"


def test_finding_actions_get_endpoint():
    from app.main import create_app
    client = TestClient(create_app())
    response = client.get("/api/security/finding-actions")
    assert response.status_code == 200
    body = response.json()
    assert "total_actions" in body
    assert "actions" in body
    assert isinstance(body["actions"], list)


def test_finding_actions_post_endpoint():
    from app.main import create_app
    client = TestClient(create_app())
    payload = {
        "finding_key": "public_ssh/admin-nsg",
        "action_type": "remediate",
        "user": "Alice",
        "resource_name": "admin-nsg",
        "rule_type": "public_ssh",
        "severity": "high",
        "region": "me-abudhabi-1",
        "compartment_id": "ocid1.compartment.oc1..test",
        "vcn_id": "ocid1.vcn.oc1..test",
        "description": "SSH open to 0.0.0.0/0",
    }
    response = client.post("/api/security/finding-actions", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["created_at"]
    assert body["action_type"] == "remediate"
