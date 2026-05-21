from pydantic import BaseModel, ConfigDict


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


class ErrorEnvelope(BaseModel):
    code: str
    message: str
