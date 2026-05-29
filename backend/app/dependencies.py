from __future__ import annotations
from fastapi import Depends

from app.config import Settings, get_settings
from app.oci_clients import OciClientFactory
from app.services.compartments import CompartmentService
from app.services.connectivity import ConnectivityService
from app.services.network_inventory import NetworkInventoryService
from app.services.preflight import PreflightService
from app.services.regions import RegionService
from app.services.route_analysis import RouteAnalysisService
from app.services.security_actions import SecurityActionsService
from app.services.security_posture import SecurityPostureService
from app.services.traffic_telemetry import TrafficTelemetryService


def get_oci_client_factory(settings: Settings = Depends(get_settings)) -> OciClientFactory:
    return OciClientFactory(settings=settings)


def get_region_service(
    settings: Settings = Depends(get_settings),
    client_factory: OciClientFactory = Depends(get_oci_client_factory),
) -> RegionService:
    return RegionService(settings=settings, client_factory=client_factory)


def get_compartment_service(
    settings: Settings = Depends(get_settings),
    client_factory: OciClientFactory = Depends(get_oci_client_factory),
) -> CompartmentService:
    return CompartmentService(settings=settings, client_factory=client_factory)


def get_network_inventory_service(
    settings: Settings = Depends(get_settings),
    client_factory: OciClientFactory = Depends(get_oci_client_factory),
) -> NetworkInventoryService:
    return NetworkInventoryService(settings=settings, client_factory=client_factory)


def get_security_posture_service(
    network_inventory: NetworkInventoryService = Depends(get_network_inventory_service),
) -> SecurityPostureService:
    return SecurityPostureService(network_inventory=network_inventory)


def get_route_analysis_service(
    network_inventory: NetworkInventoryService = Depends(get_network_inventory_service),
) -> RouteAnalysisService:
    return RouteAnalysisService(network_inventory=network_inventory)


def get_security_actions_service(
    settings: Settings = Depends(get_settings),
    client_factory: OciClientFactory = Depends(get_oci_client_factory),
) -> SecurityActionsService:
    return SecurityActionsService(settings=settings, client_factory=client_factory)


def get_traffic_telemetry_service(
    settings: Settings = Depends(get_settings),
    client_factory: OciClientFactory = Depends(get_oci_client_factory),
    network_inventory: NetworkInventoryService = Depends(get_network_inventory_service),
) -> TrafficTelemetryService:
    return TrafficTelemetryService(
        settings=settings,
        client_factory=client_factory,
        network_inventory=network_inventory,
    )


def get_connectivity_service(
    settings: Settings = Depends(get_settings),
    client_factory: OciClientFactory = Depends(get_oci_client_factory),
) -> ConnectivityService:
    return ConnectivityService(settings=settings, client_factory=client_factory)


def get_preflight_service(
    settings: Settings = Depends(get_settings),
    client_factory: OciClientFactory = Depends(get_oci_client_factory),
) -> PreflightService:
    return PreflightService(settings=settings, client_factory=client_factory)
