from importlib.metadata import version

from fastapi import FastAPI

from railconnect.api.health import router as health_router
from railconnect.api.router import router as api_router
from railconnect.core.config import Settings
from railconnect.core.errors import register_error_handlers
from railconnect.core.lifespan import lifespan
from railconnect.core.logging import configure_logging
from railconnect.core.request_id import RequestIdMiddleware
from railconnect.core.request_logging import RequestLoggingMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    configure_logging()

    app = FastAPI(
        title=config.app_name,
        description="Railway journey and disruption platform.",
        version=version("railconnect-ai"),
        debug=config.debug,
        lifespan=lifespan,
    )
    app.state.settings = config
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)
    return app
