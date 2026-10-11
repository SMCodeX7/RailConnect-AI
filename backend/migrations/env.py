from alembic import context

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.stations.models import Station

target_metadata = Station.metadata


def run_migrations() -> None:
    engine = create_db_engine(Settings())

    try:
        if context.is_offline_mode():
            context.configure(
                url=engine.url,
                target_metadata=target_metadata,
                literal_binds=True,
                dialect_opts={"paramstyle": "named"},
            )
            with context.begin_transaction():
                context.run_migrations()
        else:
            with engine.connect() as connection:
                context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                    compare_type=True,
                    compare_server_default=True,
                )
                with context.begin_transaction():
                    context.run_migrations()
    finally:
        engine.dispose()


run_migrations()
