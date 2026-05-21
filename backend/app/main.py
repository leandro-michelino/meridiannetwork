from fastapi import FastAPI

from app.config import get_settings
from app.routers import health, scope


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(health.router)
    app.include_router(scope.router)
    return app


app = create_app()

