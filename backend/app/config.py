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
        return value or ["eu-frankfurt-1"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
