from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.stations.models import Station
from railconnect.modules.stations.schemas import DemoStationDataset

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "demo_stations.json"


def main() -> None:
    dataset = DemoStationDataset.model_validate_json(DATA_PATH.read_text(encoding="utf-8-sig"))
    codes = [station.code for station in dataset.stations]

    if len(codes) != len(set(codes)):
        raise ValueError("Demo dataset contains duplicate station codes.")

    expected = {station.code: station for station in dataset.stations}
    engine = create_db_engine(Settings())

    try:
        with engine.begin() as connection:
            existing = connection.execute(
                select(Station.code, Station.name, Station.source_ref).where(
                    Station.code.in_(codes)
                )
            ).all()

            for row in existing:
                if row.name != expected[row.code].name or row.source_ref != dataset.source_ref:
                    raise ValueError(f"Existing station differs from demo dataset: {row.code}")

            rows = [
                {
                    "id": uuid5(
                        NAMESPACE_URL,
                        f"railconnect:station:{station.code}",
                    ),
                    "code": station.code,
                    "name": station.name,
                    "source_ref": dataset.source_ref,
                }
                for station in dataset.stations
            ]

            statement = (
                insert(Station)
                .values(rows)
                .on_conflict_do_nothing(index_elements=[Station.code])
                .returning(Station.code)
            )
            inserted = connection.execute(statement).scalars().all()

        print(f"Inserted: {len(inserted)}")
        print(f"Already present: {len(dataset.stations) - len(inserted)}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
