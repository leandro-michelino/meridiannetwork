from __future__ import annotations
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MERIDIAN_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Meridian API"
    app_version: str = "0.1.0"
    deployment_revision: str = "local"
    deployment_built_at: str = ""
    deployment_dirty: bool = False
    environment: str = "dev"
    api_host: str = "127.0.0.1"
    api_port: int = 8080

    home_region: str = "eu-frankfurt-1"
    active_regions: list[str] = Field(default_factory=lambda: ["eu-frankfurt-1"])
    compartment_ids: list[str] = Field(default_factory=list)

    tenancy_ocid: str | None = None
    oci_profile: str = "DEFAULT"
    oci_auth: Literal["config_file", "instance_principal", "resource_principal"] = "config_file"
    enable_live_oci: bool = False
    enable_resource_search_scope: bool = True
    inventory_cache_ttl_seconds: int = 30
    inventory_snapshot_ttl_seconds: int = 900
    inventory_snapshot_dir: str | None = None

    # Security action audit log — OCI Object Storage backend
    security_action_object_storage_enabled: bool = False
    security_action_object_storage_namespace: str = ""
    security_action_object_storage_bucket: str = ""
    security_action_object_storage_prefix: str = "meridian/security-actions/"
    security_action_retention_days: int = 365

    # Traffic telemetry — VCN Flow Logs opt-in
    traffic_flow_logs_enablement_allowed: bool = False
    traffic_flow_logs_log_group_name: str = "meridian-traffic-flow-logs"
    traffic_flow_logs_capture_filter_name: str = "meridian-traffic-capture-filter"
    traffic_flow_logs_log_name_prefix: str = "meridian-flow"
    traffic_flow_logs_default_lookback_minutes: int = 60
    traffic_flow_logs_max_lookback_hours: int = 24
    traffic_flow_logs_search_limit: int = 100

    @field_validator("active_regions", "compartment_ids", mode="before")
    @classmethod
    def parse_csv_list(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return value
        raise TypeError("value must be a comma-separated string or a list")

    @field_validator("active_regions")
    @classmethod
    def default_active_regions(cls, value: list[str]) -> list[str]:
        return value  # empty means "no active regions"; callers must handle this


@lru_cache
def get_settings() -> Settings:
    return Settings()
