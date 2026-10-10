from importlib.metadata import version

from fastapi import FastAPI

from railconnect.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="RailConnect AI",
        description="Railway journey and disruption platform.",
        version=version("railconnect-ai"),
    )
    app.include_router(health_router)
    return app
