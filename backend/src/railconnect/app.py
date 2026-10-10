from importlib.metadata import version

from fastapi import FastAPI

from railconnect.api.health import router as health_router
from railconnect.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()

    app = FastAPI(
        title=config.app_name,
        description="Railway journey and disruption platform.",
        version=version("railconnect-ai"),
        debug=config.debug,
    )
    app.include_router(health_router)
    return app
