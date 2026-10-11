from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = cast(Settings, app.state.settings)
    engine = create_db_engine(settings) if settings.database_url is not None else None
    app.state.db_engine = engine
    app.state.session_factory = (
        sessionmaker(bind=engine, expire_on_commit=False) if engine is not None else None
    )

    try:
        yield
    finally:
        app.state.session_factory = None
        app.state.db_engine = None
        if engine is not None:
            engine.dispose()
