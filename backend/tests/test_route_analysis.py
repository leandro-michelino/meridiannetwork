from fastapi.testclient import TestClient

from app.models import GatewaySummary, RouteRuleSummary, RouteTableSummary
from app.services.route_analysis import RouteAnalysisService


class EmptyNetworkInventory:
    def list_route_tables(self, regions=None, compartment_ids=None, vcn_id=None):
        return []

    def list_gateways(self, regions=None, compartment_ids=None, vcn_id=None):
        return []


class RiskyRouteInventory:
    def list_route_tables(self, regions=None, compartment_ids=None, vcn_id=None):
        return [
            RouteTableSummary(
                id="rt-empty",
                name="empty-route-table",
                region="eu-frankfurt-1",
                compartment_id="compartment-1",
                vcn_id="vcn-1",
                lifecycle_state="AVAILABLE",
                route_rules=[],
            ),
            RouteTableSummary(
                id="rt-risky",
                name="risky-route-table",
                region="eu-frankfurt-1",
                compartment_id="compartment-1",
                vcn_id="vcn-1",
                lifecycle_state="AVAILABLE",
                route_rules=[
                    RouteRuleSummary(
                        destination="0.0.0.0/0",
                        destination_type="CIDR_BLOCK",
                        network_entity_id="igw-1",
                    ),
                    RouteRuleSummary(
                        destination="0.0.0.0/0",
                        destination_type="CIDR_BLOCK",
                        network_entity_id="nat-disabled",
                    ),
                    RouteRuleSummary(
                        destination="10.10.0.0/16",
                        destination_type="CIDR_BLOCK",
                        network_entity_id=None,
                    ),
                    RouteRuleSummary(
                        destination="10.20.0.0/16",
                        destination_type="CIDR_BLOCK",
                        network_entity_id="missing-target",
                    ),
                ],
            ),
        ]

    def list_gateways(self, regions=None, compartment_ids=None, vcn_id=None):
        return [
            GatewaySummary(
                id="igw-1",
                name="internet-gateway",
                gateway_type="internet_gateway",
                region="eu-frankfurt-1",
                compartment_id="compartment-1",
                vcn_id="vcn-1",
                lifecycle_state="AVAILABLE",
                is_enabled=True,
            ),
            GatewaySummary(
                id="nat-disabled",
                name="disabled-nat",
                gateway_type="nat_gateway",
                region="eu-frankfurt-1",
                compartment_id="compartment-1",
                vcn_id="vcn-1",
                lifecycle_state="AVAILABLE",
                is_enabled=False,
            ),
        ]


def test_route_analysis_returns_ok_without_route_tables():
    service = RouteAnalysisService(network_inventory=EmptyNetworkInventory())

    summary = service.summarize()

    assert summary.status == "ok"
    assert summary.total_issues == 0


def test_route_analysis_flags_route_table_issues():
    service = RouteAnalysisService(network_inventory=RiskyRouteInventory())

    summary = service.summarize()

    assert summary.status == "high"
    assert summary.total_issues == 6
    assert summary.high_issues == 2
    assert summary.medium_issues == 3
    assert summary.low_issues == 1
    assert {issue.issue_type for issue in summary.issues} == {
        "empty_route_table",
        "public_default_route",
        "duplicate_route_destination",
        "disabled_route_target",
        "missing_route_target",
        "unresolved_route_target",
    }


def test_route_issues_endpoint_returns_empty_summary_without_live_oci():
    from app.main import create_app

    client = TestClient(create_app())

    response = client.get("/api/route-issues")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["total_issues"] == 0
