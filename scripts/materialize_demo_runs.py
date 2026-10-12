import argparse
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.run_service import materialize_service_run

DEMO_SOURCE = "demo-timetable-v1"
MAX_RANGE_DAYS = 31


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a date in YYYY-MM-DD format.") from error


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize demonstration service runs for an explicit date range."
    )
    parser.add_argument("--start-date", type=parse_date, required=True)
    parser.add_argument("--end-date", type=parse_date, required=True)
    args = parser.parse_args()

    start_date: date = args.start_date
    end_date: date = args.end_date
    range_days = (end_date - start_date).days + 1

    if range_days < 1:
        parser.error("The end date cannot precede the start date.")

    if range_days > MAX_RANGE_DAYS:
        parser.error(f"A single invocation supports at most {MAX_RANGE_DAYS} days.")

    settings = Settings()

    if settings.environment not in {"development", "test"}:
        parser.error("This command requires a development or test environment.")

    if settings.database_url is None:
        parser.error("Configure the database URL before running this command.")

    engine = create_db_engine(settings)
    inserted = 0
    existing = 0
    skipped = 0

    try:
        with Session(engine) as session:
            with session.begin():
                services = list(
                    session.scalars(
                        select(TrainService)
                        .where(
                            TrainService.source_ref == DEMO_SOURCE,
                            TrainService.is_active.is_(True),
                        )
                        .order_by(TrainService.code)
                    )
                )

                if not services:
                    raise ValueError("No active demonstration services found. Seed them first.")

                for day_offset in range(range_days):
                    service_date = start_date + timedelta(days=day_offset)
                    weekday_flag = 1 << service_date.weekday()

                    for service in services:
                        if (
                            not service.valid_from <= service_date <= service.valid_until
                            or service.operating_days & weekday_flag == 0
                        ):
                            skipped += 1
                            continue

                        result = materialize_service_run(
                            session,
                            service.id,
                            service_date,
                        )

                        if result.inserted:
                            inserted += 1
                        else:
                            existing += 1
    except ValueError as error:
        parser.exit(status=2, message=f"Materialization failed: {error}\n")
    finally:
        engine.dispose()

    print(f"Date range: {start_date.isoformat()} to {end_date.isoformat()}")
    print(f"Runs inserted: {inserted}")
    print(f"Runs already present: {existing}")
    print(f"Service dates not operating: {skipped}")


if __name__ == "__main__":
    main()
