from pathlib import Path

from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.timetable.import_loader import load_timetable_snapshot
from railconnect.modules.timetable.import_service import import_timetable

DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "processed"


def main() -> None:
    settings = Settings()

    if settings.environment not in {"development", "test"}:
        raise SystemExit("Demo timetable import requires a development or test environment.")

    if settings.database_url is None:
        raise SystemExit("Configure the database URL before importing.")

    snapshot = load_timetable_snapshot(
        DATA_DIRECTORY / "demo_timetable.json",
        DATA_DIRECTORY / "demo_timetable.source.json",
    )
    engine = create_db_engine(settings)

    try:
        with Session(engine) as session:
            with session.begin():
                result = import_timetable(
                    session,
                    snapshot,
                    execution_context=f"{settings.environment}-cli",
                )
                summary_id = result.summary.id
                source_id = result.source.id
                seed_result = result.seed_result
                summary_created = result.summary_created

        print(f"Source: {snapshot.dataset.source_ref}")
        print(f"Source ID: {source_id}")
        print(f"Content SHA-256: {snapshot.content_sha256}")
        print(f"Import summary ID: {summary_id}")
        print(f"Import summary created: {summary_created}")
        print(f"Services inserted: {seed_result.inserted_services}")
        print(f"Services already present: {seed_result.existing_services}")
        print(f"Stops inserted: {seed_result.inserted_stops}")
    except ValueError as error:
        raise SystemExit(f"Timetable import failed: {error}") from error
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
