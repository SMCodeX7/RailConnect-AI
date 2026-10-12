from pathlib import Path

from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.timetable.import_loader import load_timetable_snapshot
from railconnect.modules.timetable.import_preview import preview_timetable_import

DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "processed"


def main() -> None:
    snapshot = load_timetable_snapshot(
        DATA_DIRECTORY / "demo_timetable.json",
        DATA_DIRECTORY / "demo_timetable.source.json",
    )
    engine = create_db_engine(Settings())

    try:
        with Session(engine) as session:
            preview = preview_timetable_import(session, snapshot)

        print(f"Source: {preview.source_ref}")
        print(f"Content SHA-256: {preview.content_sha256}")
        print(f"Source registered: {preview.source_registered}")
        print(f"Import recorded: {preview.import_recorded}")
        print(f"New services: {len(preview.new_service_codes)}")
        print(f"Existing services: {len(preview.existing_service_codes)}")
        print(f"Stops to insert: {preview.stops_to_insert}")
        print(f"Can import: {preview.can_import}")

        for code in preview.new_service_codes:
            print(f"New service: {code}")

        for conflict in preview.conflicts:
            print(f"Conflict: {conflict}")

        if not preview.can_import:
            raise SystemExit(2)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
