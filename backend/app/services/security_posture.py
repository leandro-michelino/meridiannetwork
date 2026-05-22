from __future__ import annotations
from dataclasses import dataclass

from app.models import (
    NetworkSecurityGroupSummary,
    SecurityFinding,
    SecurityListSummary,
    SecurityPostureSummary,
    SecurityRuleSummary,
)
from app.services.network_inventory import NetworkInventoryService


PUBLIC_IPV4 = "0.0.0.0/0"
ALL_PROTOCOLS = {"all", "ALL"}
TCP_PROTOCOLS = {"6", "tcp", "TCP"}


@dataclass(frozen=True)
class SecurityPostureService:
    network_inventory: NetworkInventoryService

    def summarize(
        self,
        regions: list[str] | None = None,
        compartment_ids: list[str] | None = None,
        vcn_id: str | None = None,
    ) -> SecurityPostureSummary:
        security_lists = self.network_inventory.list_security_lists(
            regions=regions,
            compartment_ids=compartment_ids,
            vcn_id=vcn_id,
        )
        network_security_groups = self.network_inventory.list_network_security_groups(
            regions=regions,
            compartment_ids=compartment_ids,
            vcn_id=vcn_id,
        )
        findings: list[SecurityFinding] = []
        for security_list in security_lists:
            findings.extend(self._findings_for_security_list(security_list))
        for nsg in network_security_groups:
            findings.extend(self._findings_for_network_security_group(nsg))

        critical = sum(1 for finding in findings if finding.severity == "critical")
        high = sum(1 for finding in findings if finding.severity == "high")
        medium = sum(1 for finding in findings if finding.severity == "medium")
        low = sum(1 for finding in findings if finding.severity == "low")

        if critical:
            status = "critical"
        elif high:
            status = "high"
        elif medium:
            status = "medium"
        elif low:
            status = "low"
        else:
            status = "ok"

        return SecurityPostureSummary(
            status=status,
            total_findings=len(findings),
            critical_findings=critical,
            high_findings=high,
            medium_findings=medium,
            low_findings=low,
            findings=findings,
        )

    def _findings_for_security_list(self, security_list: SecurityListSummary) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        for rule in security_list.ingress_rules:
            if rule.source != PUBLIC_IPV4:
                continue
            if rule.protocol in ALL_PROTOCOLS:
                findings.append(
                    self._security_list_finding(
                        security_list=security_list,
                        severity="critical",
                        rule_type="public_all_protocols",
                        description="Ingress allows all protocols from 0.0.0.0/0.",
                        recommendation="Restrict the source CIDR and protocol to the minimum required access.",
                    )
                )
            elif self._port_in_rule(rule, 22):
                findings.append(
                    self._security_list_finding(
                        security_list=security_list,
                        severity="high",
                        rule_type="public_ssh",
                        description="Ingress allows SSH from 0.0.0.0/0.",
                        recommendation="Restrict SSH to a VPN, Bastion, or administrator source CIDR.",
                    )
                )
            elif self._port_in_rule(rule, 3389):
                findings.append(
                    self._security_list_finding(
                        security_list=security_list,
                        severity="high",
                        rule_type="public_rdp",
                        description="Ingress allows RDP from 0.0.0.0/0.",
                        recommendation="Restrict RDP to a VPN, Bastion, or administrator source CIDR.",
                    )
                )
        return findings

    def _findings_for_network_security_group(self, nsg: NetworkSecurityGroupSummary) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        for rule in nsg.ingress_rules:
            if rule.source != PUBLIC_IPV4:
                continue
            if rule.protocol in ALL_PROTOCOLS:
                findings.append(
                    self._finding(
                        resource_id=nsg.id,
                        resource_name=nsg.name,
                        region=nsg.region,
                        compartment_id=nsg.compartment_id,
                        vcn_id=nsg.vcn_id,
                        severity="critical",
                        rule_type="nsg_public_all_protocols",
                        description="NSG ingress allows all protocols from 0.0.0.0/0.",
                        recommendation="Restrict the NSG source CIDR and protocol to the minimum required access.",
                    )
                )
            elif self._port_in_rule(rule, 22):
                findings.append(
                    self._finding(
                        resource_id=nsg.id,
                        resource_name=nsg.name,
                        region=nsg.region,
                        compartment_id=nsg.compartment_id,
                        vcn_id=nsg.vcn_id,
                        severity="high",
                        rule_type="nsg_public_ssh",
                        description="NSG ingress allows SSH from 0.0.0.0/0.",
                        recommendation="Restrict SSH to a VPN, Bastion, or administrator source CIDR.",
                    )
                )
            elif self._port_in_rule(rule, 3389):
                findings.append(
                    self._finding(
                        resource_id=nsg.id,
                        resource_name=nsg.name,
                        region=nsg.region,
                        compartment_id=nsg.compartment_id,
                        vcn_id=nsg.vcn_id,
                        severity="high",
                        rule_type="nsg_public_rdp",
                        description="NSG ingress allows RDP from 0.0.0.0/0.",
                        recommendation="Restrict RDP to a VPN, Bastion, or administrator source CIDR.",
                    )
                )
        return findings

    def _finding(
        self,
        resource_id: str,
        resource_name: str,
        region: str,
        compartment_id: str,
        vcn_id: str,
        severity: str,
        rule_type: str,
        description: str,
        recommendation: str,
    ) -> SecurityFinding:
        return SecurityFinding(
            severity=severity,
            rule_type=rule_type,
            resource_id=resource_id,
            resource_name=resource_name,
            region=region,
            compartment_id=compartment_id,
            vcn_id=vcn_id,
            description=description,
            recommendation=recommendation,
        )

    def _security_list_finding(
        self,
        security_list: SecurityListSummary,
        severity: str,
        rule_type: str,
        description: str,
        recommendation: str,
    ) -> SecurityFinding:
        return self._finding(
            resource_id=security_list.id,
            resource_name=security_list.name,
            region=security_list.region,
            compartment_id=security_list.compartment_id,
            vcn_id=security_list.vcn_id,
            severity=severity,
            rule_type=rule_type,
            description=description,
            recommendation=recommendation,
        )

    def _port_in_rule(self, rule: SecurityRuleSummary, port: int) -> bool:
        if rule.protocol not in TCP_PROTOCOLS and rule.protocol not in ALL_PROTOCOLS:
            return False
        if rule.min_port is None or rule.max_port is None:
            return True
        return rule.min_port <= port <= rule.max_port
