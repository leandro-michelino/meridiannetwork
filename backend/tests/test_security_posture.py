from fastapi.testclient import TestClient

from app.models import SecurityListSummary, SecurityRuleSummary
from app.services.security_posture import SecurityPostureService


class EmptyNetworkInventory:
    def list_security_lists(self, regions=None, compartment_ids=None, vcn_id=None):
        return []


class RiskyNetworkInventory:
    def list_security_lists(self, regions=None, compartment_ids=None, vcn_id=None):
        return [
            SecurityListSummary(
                id="sl-1",
                name="public-security-list",
                region="eu-frankfurt-1",
                compartment_id="compartment-1",
                vcn_id="vcn-1",
                lifecycle_state="AVAILABLE",
                ingress_rules=[
                    SecurityRuleSummary(
                        direction="ingress",
                        protocol="6",
                        source="0.0.0.0/0",
                        min_port=22,
                        max_port=22,
                    ),
                    SecurityRuleSummary(
                        direction="ingress",
                        protocol="all",
                        source="0.0.0.0/0",
                    ),
                ],
                egress_rules=[],
            )
        ]


def test_security_posture_returns_ok_without_findings():
    service = SecurityPostureService(network_inventory=EmptyNetworkInventory())

    summary = service.summarize()

    assert summary.status == "ok"
    assert summary.total_findings == 0


def test_security_posture_flags_public_ssh_and_all_protocols():
    service = SecurityPostureService(network_inventory=RiskyNetworkInventory())

    summary = service.summarize()

    assert summary.status == "critical"
    assert summary.total_findings == 2
    assert summary.critical_findings == 1
    assert summary.high_findings == 1
    assert {finding.rule_type for finding in summary.findings} == {"public_ssh", "public_all_protocols"}


def test_security_posture_endpoint_returns_empty_summary_without_live_oci():
    from app.main import create_app

    client = TestClient(create_app())

    response = client.get("/api/security/posture")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["total_findings"] == 0
