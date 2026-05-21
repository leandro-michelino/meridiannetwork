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


class ErrorEnvelope(BaseModel):
    code: str
    message: str
