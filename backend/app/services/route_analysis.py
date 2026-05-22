from __future__ import annotations
from dataclasses import dataclass

from app.models import GatewaySummary, RouteIssue, RouteIssueSummary, RouteRuleSummary, RouteTableSummary
from app.services.network_inventory import NetworkInventoryService


DEFAULT_ROUTES = {"0.0.0.0/0", "::/0"}


@dataclass(frozen=True)
class RouteAnalysisService:
    network_inventory: NetworkInventoryService

    def summarize(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_id: str | None = None,
    ) -> RouteIssueSummary:
        route_tables = self.network_inventory.list_route_tables(
            regions=regions,
            compartment_ids=compartment_ids,
            vcn_id=vcn_id,
        )
        gateways = self.network_inventory.list_gateways(
            regions=regions,
            compartment_ids=compartment_ids,
            vcn_id=vcn_id,
        )
        gateway_by_id = {gateway.id: gateway for gateway in gateways}

        issues: list[RouteIssue] = []
        for route_table in route_tables:
            issues.extend(self._issues_for_route_table(route_table, gateway_by_id))

        return RouteIssueSummary(
            status=self._summary_status(issues),
            total_issues=len(issues),
            critical_issues=sum(1 for issue in issues if issue.severity == "critical"),
            high_issues=sum(1 for issue in issues if issue.severity == "high"),
            medium_issues=sum(1 for issue in issues if issue.severity == "medium"),
            low_issues=sum(1 for issue in issues if issue.severity == "low"),
            issues=issues,
        )

    def _issues_for_route_table(
        self,
        route_table: RouteTableSummary,
        gateway_by_id: dict[str, GatewaySummary],
    ) -> list[RouteIssue]:
        if not route_table.route_rules:
            return [
                self._issue(
                    route_table=route_table,
                    route_rule=None,
                    severity="low",
                    issue_type="empty_route_table",
                    description="Route table has no route rules.",
                    recommendation="Confirm this route table is intentionally isolated or add required routes.",
                )
            ]

        issues: list[RouteIssue] = []
        seen_destinations: set[tuple[str | None, str | None]] = set()
        for route_rule in route_table.route_rules:
            destination_key = (route_rule.destination, route_rule.destination_type)
            if destination_key in seen_destinations:
                issues.append(
                    self._issue(
                        route_table=route_table,
                        route_rule=route_rule,
                        severity="medium",
                        issue_type="duplicate_route_destination",
                        description="Route table has multiple rules for the same destination.",
                        recommendation="Keep a single authoritative route for each destination prefix.",
                    )
                )
            seen_destinations.add(destination_key)

            if not route_rule.network_entity_id:
                issues.append(
                    self._issue(
                        route_table=route_table,
                        route_rule=route_rule,
                        severity="high",
                        issue_type="missing_route_target",
                        description="Route rule has no network target.",
                        recommendation="Attach the route to a valid gateway or remove the incomplete rule.",
                    )
                )
                continue

            gateway = gateway_by_id.get(route_rule.network_entity_id)
            if gateway is None:
                issues.append(
                    self._issue(
                        route_table=route_table,
                        route_rule=route_rule,
                        severity="medium",
                        issue_type="unresolved_route_target",
                        description="Route target was not found in the current gateway inventory.",
                        recommendation="Confirm the target exists, is in scope, and is a supported network target type.",
                    )
                )
                continue

            if gateway.is_enabled is False:
                issues.append(
                    self._issue(
                        route_table=route_table,
                        route_rule=route_rule,
                        severity="high",
                        issue_type="disabled_route_target",
                        description=f"Route points to disabled {gateway.gateway_type}.",
                        recommendation="Enable the gateway or route traffic to an active target.",
                    )
                )

            if self._is_public_default_route(route_rule, gateway):
                issues.append(
                    self._issue(
                        route_table=route_table,
                        route_rule=route_rule,
                        severity="medium",
                        issue_type="public_default_route",
                        description="Route table sends default traffic to an Internet Gateway.",
                        recommendation="Confirm this route table is only associated with public subnets.",
                    )
                )
        return issues

    def _issue(
        self,
        route_table: RouteTableSummary,
        route_rule: RouteRuleSummary | None,
        severity: str,
        issue_type: str,
        description: str,
        recommendation: str,
    ) -> RouteIssue:
        return RouteIssue(
            severity=severity,
            issue_type=issue_type,
            route_table_id=route_table.id,
            route_table_name=route_table.name,
            region=route_table.region,
            compartment_id=route_table.compartment_id,
            vcn_id=route_table.vcn_id,
            destination=route_rule.destination if route_rule else None,
            destination_type=route_rule.destination_type if route_rule else None,
            network_entity_id=route_rule.network_entity_id if route_rule else None,
            description=description,
            recommendation=recommendation,
        )

    def _is_public_default_route(self, route_rule: RouteRuleSummary, gateway: GatewaySummary) -> bool:
        return route_rule.destination in DEFAULT_ROUTES and gateway.gateway_type == "internet_gateway"

    def _summary_status(self, issues: list[RouteIssue]) -> str:
        if any(issue.severity == "critical" for issue in issues):
            return "critical"
        if any(issue.severity == "high" for issue in issues):
            return "high"
        if any(issue.severity == "medium" for issue in issues):
            return "medium"
        if any(issue.severity == "low" for issue in issues):
            return "low"
        return "ok"
