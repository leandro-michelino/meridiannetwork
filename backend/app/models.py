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


class ErrorEnvelope(BaseModel):
    code: str
    message: str

