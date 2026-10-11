from pathlib import Path

from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "demo_timetable.json"


def main() -> None:
    dataset = DemoTimetableDataset.model_validate_json(DATA_PATH.read_text(encoding="utf-8-sig"))
    engine = create_db_engine(Settings())

    try:
        with Session(engine) as session:
            with session.begin():
                result = seed_timetable(session, dataset)

        print(f"Services inserted: {result.inserted_services}")
        print(f"Services already present: {result.existing_services}")
        print(f"Stops inserted: {result.inserted_stops}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
