import argparse

from sqlalchemy.orm import Session

from railconnect.core.clock import utc_now
from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.incidents.report_cleanup_service import (
    cleanup_report_counters,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview or delete old report-submission rate counters."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete eligible records; otherwise preview only.",
    )
    parser.add_argument("--retention-days", type=int, default=1)
    parser.add_argument("--batch-limit", type=int, default=500)
    args = parser.parse_args()

    if not 1 <= args.retention_days <= 365:
        parser.error("--retention-days must be between 1 and 365.")

    if not 1 <= args.batch_limit <= 1000:
        parser.error("--batch-limit must be between 1 and 1000.")

    settings = Settings()

    if settings.database_url is None:
        parser.error("A configured database is required.")

    engine = create_db_engine(settings)

    try:
        with Session(engine) as session:
            with session.begin():
                result = cleanup_report_counters(
                    session,
                    now=utc_now(),
                    apply=args.apply,
                    retention_days=args.retention_days,
                    batch_limit=args.batch_limit,
                )

        print(f"Mode: {'apply' if result.applied else 'preview'}")
        print(f"Retention days: {args.retention_days}")
        print(f"Batch limit: {args.batch_limit}")
        print(f"Report-limit records: {result.records}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
