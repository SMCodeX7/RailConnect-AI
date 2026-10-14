import argparse

from sqlalchemy.orm import Session

from railconnect.core.clock import utc_now
from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.identity.cleanup_service import cleanup_identity_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview or apply bounded cleanup of old identity records."
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--session-retention-days", type=int, default=7)
    parser.add_argument("--rate-retention-days", type=int, default=1)
    args = parser.parse_args()

    settings = Settings()
    if settings.database_url is None:
        parser.error("Configure the database URL before cleanup.")

    engine = create_db_engine(settings)

    try:
        with Session(engine) as session:
            with session.begin():
                result = cleanup_identity_records(
                    session,
                    utc_now(),
                    apply=args.apply,
                    batch_size=args.batch_size,
                    session_retention_days=args.session_retention_days,
                    rate_retention_days=args.rate_retention_days,
                )

        print(f"Mode: {'apply' if result.applied else 'preview'}")
        print(f"Session retention days: {args.session_retention_days}")
        print(f"Rate-limit retention days: {args.rate_retention_days}")
        print(f"Batch limit per table: {args.batch_size}")
        print(f"Session records: {result.sessions}")
        print(f"Login-limit records: {result.login_limits}")
    except ValueError as error:
        parser.exit(status=2, message=f"Cleanup failed: {error}\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
