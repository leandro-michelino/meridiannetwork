from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    service: str
    version: str
    environment: str
    status: str


class ReadinessResponse(BaseModel):
    service: str
    status: str
    live_oci_enabled: bool
    tenancy_configured: bool
    auth_mode: str


class VersionResponse(BaseModel):
    service: str
    version: str
    environment: str
    revision: str
    built_at: str
    dirty: bool


class PreflightCheck(BaseModel):
    name: str
    status: str
    message: str
    action: str | None = None


class PreflightSummary(BaseModel):
    status: str
    live_oci_enabled: bool
    auth_mode: str
    home_region: str
    active_regions: list[str]
    tenancy_configured: bool
    compartment_ids: list[str] = Field(default_factory=list)
    checks: list[PreflightCheck] = Field(default_factory=list)


class RegionSummary(BaseModel):
    id: str
    geo: str
    is_home_region: bool = False
    is_active: bool = False


class CompartmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    lifecycle_state: str | None = None
    parent_compartment_id: str | None = None
    is_accessible: bool = True
    source: str = "configured"


class VcnSummary(BaseModel):
    id: str
    name: str
    cidr_blocks: list[str]
    region: str
    compartment_id: str
    lifecycle_state: str | None = None
    dns_label: str | None = None
    time_created: str | None = None


class SubnetSummary(BaseModel):
    id: str
    name: str
    cidr_block: str
    region: str
    compartment_id: str
    vcn_id: str
    lifecycle_state: str | None = None
    availability_domain: str | None = None
    dns_label: str | None = None
    prohibit_public_ip_on_vnic: bool | None = None
    route_table_id: str | None = None
    security_list_ids: list[str] = Field(default_factory=list)
    time_created: str | None = None


class GatewaySummary(BaseModel):
    id: str
    name: str
    gateway_type: str
    region: str
    compartment_id: str
    vcn_id: str | None = None
    lifecycle_state: str | None = None
    is_enabled: bool | None = None
    route_table_id: str | None = None
    time_created: str | None = None


class RouteRuleSummary(BaseModel):
    destination: str | None = None
    destination_type: str | None = None
    network_entity_id: str | None = None
    description: str | None = None


class RouteTableSummary(BaseModel):
    id: str
    name: str
    region: str
    compartment_id: str
    vcn_id: str
    lifecycle_state: str | None = None
    route_rules: list[RouteRuleSummary]
    time_created: str | None = None


class RouteIssue(BaseModel):
    severity: str
    issue_type: str
    route_table_id: str
    route_table_name: str
    region: str
    compartment_id: str
    vcn_id: str
    destination: str | None = None
    destination_type: str | None = None
    network_entity_id: str | None = None
    description: str
    recommendation: str


class RouteIssueSummary(BaseModel):
    status: str
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    issues: list[RouteIssue]


class SecurityRuleSummary(BaseModel):
    direction: str
    protocol: str
    source: str | None = None
    destination: str | None = None
    source_type: str | None = None
    destination_type: str | None = None
    min_port: int | None = None
    max_port: int | None = None
    description: str | None = None
    is_stateless: bool | None = None


class SecurityListSummary(BaseModel):
    id: str
    name: str
    region: str
    compartment_id: str
    vcn_id: str
    lifecycle_state: str | None = None
    ingress_rules: list[SecurityRuleSummary]
    egress_rules: list[SecurityRuleSummary]
    time_created: str | None = None


class NetworkSecurityGroupSummary(BaseModel):
    id: str
    name: str
    region: str
    compartment_id: str
    vcn_id: str
    lifecycle_state: str | None = None
    ingress_rules: list[SecurityRuleSummary]
    egress_rules: list[SecurityRuleSummary]
    time_created: str | None = None


class SecurityFinding(BaseModel):
    severity: str
    rule_type: str
    resource_id: str
    resource_name: str
    region: str
    compartment_id: str
    vcn_id: str
    description: str
    recommendation: str


class SecurityPostureSummary(BaseModel):
    status: str
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    findings: list[SecurityFinding]


class TopologyNode(BaseModel):
    id: str
    name: str
    resource_type: str
    region: str | None = None
    compartment_id: str | None = None
    vcn_id: str | None = None
    lifecycle_state: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class TopologyEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    relationship: str
    metadata: dict[str, str] = Field(default_factory=dict)


class TopologyGraph(BaseModel):
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]


class SecurityActionRequest(BaseModel):
    finding_key: str
    action_type: str  # remediate | accept_risk | assign_owner | create_remediation_task | suppress
    user: str
    note: str | None = None
    assignee: str | None = None
    expires_at: str | None = None
    resource_id: str = ""
    resource_name: str = ""
    rule_type: str = ""
    severity: str = ""
    region: str = ""
    compartment_id: str = ""
    vcn_id: str = ""
    description: str = ""


class SecurityAction(SecurityActionRequest):
    id: str
    created_at: str  # ISO-8601


class SecurityActionHistoryResponse(BaseModel):
    total_actions: int
    actions: list[SecurityAction]
    retention_days: int = 365
    storage: str = "object-storage"
    archive_enabled: bool = False
    archive_prefix: str | None = None


class TrafficEndpointSummary(BaseModel):
    ip_address: str
    name: str | None = None
    instance_id: str | None = None
    instance_name: str | None = None
    vnic_id: str | None = None
    subnet_id: str | None = None
    vcn_id: str | None = None
    region: str | None = None
    compartment_id: str | None = None


class TrafficTelemetryStatus(BaseModel):
    status: str
    live_oci_enabled: bool
    enablement_allowed: bool
    log_group_name: str
    capture_filter_name: str
    checked_vcns: int = 0
    enabled_vcns: int = 0
    missing_vcns: int = 0
    message: str


class TrafficEnableRequest(BaseModel):
    regions: list[str] = Field(default_factory=list)
    compartment_ids: list[str] = Field(default_factory=list)
    vcn_ids: list[str] = Field(default_factory=list)


class TrafficEnablementItem(BaseModel):
    vcn_id: str
    vcn_name: str
    region: str
    compartment_id: str
    status: str
    message: str
    log_group_id: str | None = None
    log_id: str | None = None
    capture_filter_id: str | None = None


class TrafficEnablementResponse(BaseModel):
    status: str
    enabled: int
    skipped: int
    failed: int
    items: list[TrafficEnablementItem]


class TrafficFlowRecord(BaseModel):
    time_start: str | None = None
    time_end: str | None = None
    source_ip: str
    destination_ip: str
    source_port: int | None = None
    destination_port: int | None = None
    protocol: str | None = None
    action: str | None = None
    status: str | None = None
    packets: int | None = None
    bytes: int | None = None
    region: str | None = None
    compartment_id: str | None = None
    log_id: str | None = None
    source: TrafficEndpointSummary | None = None
    destination: TrafficEndpointSummary | None = None


class TrafficFlowSummary(BaseModel):
    status: str
    total_flows: int
    time_window_minutes: int
    flows: list[TrafficFlowRecord]
    endpoints: list[TrafficEndpointSummary] = Field(default_factory=list)
    message: str | None = None
    archive_error: str | None = None


class ConnectivityEndpoint(BaseModel):
    type: str = Field(default="ip_address", pattern="^(ip_address|compute_instance|vnic|subnet)$")
    value: str
    address: str | None = None


class ConnectivityCheckRequest(BaseModel):
    source: ConnectivityEndpoint
    destination: ConnectivityEndpoint
    protocol: str = Field(default="TCP", pattern="^(TCP|UDP|ICMP|tcp|udp|icmp|6|17|1)$")
    destination_port: int | None = Field(default=None, ge=1, le=65535)
    source_port: int | None = Field(default=None, ge=1, le=65535)
    region: str | None = None
    compartment_id: str | None = None
    bidirectional: bool = True


class ConnectivityHop(BaseModel):
    index: int
    entity_id: str | None = None
    node_type: str | None = None
    route_action: str | None = None
    egress_action: str | None = None
    ingress_action: str | None = None
    description: str | None = None


class ConnectivityCheckResponse(BaseModel):
    status: str
    reachable: bool | None = None
    provider: str = "oci_network_path_analyzer"
    cost_impact: str = "no_flow_logs_enabled"
    work_request_id: str | None = None
    forward_status: str | None = None
    return_status: str | None = None
    message: str
    findings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    hops: list[ConnectivityHop] = Field(default_factory=list)


class IdentityContext(BaseModel):
    enabled: bool = False
    source: str = "manual"
    domain_name: str = "Default"
    current_user: str | None = None
    required_group: str = "MeridianNetworkUsers"
    groups_header: str = "x-authenticated-groups"
    is_authorized: bool = False
    user_required: bool = True
    message: str = ""


class ErrorEnvelope(BaseModel):
    code: str
    message: str
