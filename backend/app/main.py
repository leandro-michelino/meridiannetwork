from __future__ import annotations
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import threading

from fastapi import FastAPI

from app.config import get_settings
from app.oci_clients import OciClientFactory
from app.routers import connectivity, export, health, identity, network, preflight, scope, security, traffic
from app.services.network_inventory import NetworkInventoryService
from app.services.traffic_telemetry import TrafficTelemetryService


def _start_traffic_telemetry_sweeper(app: FastAPI) -> None:
    settings = get_settings()
    if not settings.enable_live_oci:
        return
    stop_event = threading.Event()

    def sweep_loop() -> None:
        client_factory = OciClientFactory(settings=settings)
        service = TrafficTelemetryService(
            settings=settings,
            client_factory=client_factory,
            network_inventory=NetworkInventoryService(
                settings=settings,
                client_factory=client_factory,
            ),
        )
        service.disable_expired_leases()
        while not stop_event.wait(max(10, settings.traffic_flow_logs_expiry_sweep_seconds)):
            service.disable_expired_leases()

    app.state.traffic_telemetry_sweeper_stop = stop_event
    thread = threading.Thread(target=sweep_loop, name="meridian-traffic-telemetry-sweeper", daemon=True)
    app.state.traffic_telemetry_sweeper = thread
    thread.start()


def _stop_traffic_telemetry_sweeper(app: FastAPI) -> None:
    stop_event = getattr(app.state, "traffic_telemetry_sweeper_stop", None)
    if stop_event is not None:
        stop_event.set()
    thread = getattr(app.state, "traffic_telemetry_sweeper", None)
    if thread is not None:
        thread.join(timeout=2)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _start_traffic_telemetry_sweeper(app)
        try:
            yield
        finally:
            _stop_traffic_telemetry_sweeper(app)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(scope.router)
    app.include_router(network.router)
    app.include_router(security.router)
    app.include_router(identity.router)
    app.include_router(export.router)
    app.include_router(preflight.router)
    app.include_router(traffic.router)
    app.include_router(connectivity.router)
    return app


app = create_app()
