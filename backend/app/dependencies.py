from fastapi import Depends

from app.config import Settings, get_settings
from app.oci_clients import OciClientFactory
from app.services.compartments import CompartmentService
from app.services.regions import RegionService


def get_region_service(settings: Settings = Depends(get_settings)) -> RegionService:
    return RegionService(settings=settings)


def get_oci_client_factory(settings: Settings = Depends(get_settings)) -> OciClientFactory:
    return OciClientFactory(settings=settings)


def get_compartment_service(
    settings: Settings = Depends(get_settings),
    client_factory: OciClientFactory = Depends(get_oci_client_factory),
) -> CompartmentService:
    return CompartmentService(settings=settings, client_factory=client_factory)
