from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url

from railconnect.core.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    if settings.database_url is None:
        raise ValueError("RAILCONNECT_DATABASE_URL must be configured.")

    url = make_url(settings.database_url.get_secret_value())

    if url.drivername != "postgresql+psycopg":
        raise ValueError("Database URL must use postgresql+psycopg.")

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
        connect_args={"connect_timeout": 5},
        hide_parameters=True,
    )
