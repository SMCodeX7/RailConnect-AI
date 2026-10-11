from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from railconnect.modules.timetable.seed_schemas import DemoStop, DemoTimetableDataset


def timetable_data() -> dict[str, Any]:
    return {
        "kind": "demonstration",
        "timezone": "Asia/Colombo",
        "source_ref": "timetable-test",
        "valid_from": "2026-01-01",
        "valid_until": "2028-12-31",
        "services": [
            {
                "code": "DEMO_TEST_NIGHT",
                "name": "Test Overnight Service",
                "operating_days": 127,
                "stops": [
                    {"station_code": "DEMO_FORT", "departure_minutes": 1260},
                    {
                        "station_code": "DEMO_GALOYA",
                        "arrival_minutes": 1660,
                        "departure_minutes": 1665,
                    },
                    {"station_code": "DEMO_TRINCOMALEE", "arrival_minutes": 1800},
                ],
            }
        ],
    }


def test_accepts_overnight_service() -> None:
    dataset = DemoTimetableDataset.model_validate(timetable_data())

    assert dataset.services[0].stops[-1].arrival_minutes == 1800


@pytest.mark.parametrize(
    ("arrival", "departure"),
    [
        (None, None),
        (100, 99),
        (-1, 10),
        (0, 4320),
        (True, 10),
        ("100", 110),
    ],
)
def test_rejects_invalid_stop_times(
    arrival: object,
    departure: object,
) -> None:
    with pytest.raises(ValidationError):
        DemoStop.model_validate(
            {
                "station_code": "DEMO_FORT",
                "arrival_minutes": arrival,
                "departure_minutes": departure,
            }
        )


def test_rejects_arrival_before_previous_departure() -> None:
    data = timetable_data()
    data["services"][0]["stops"][1]["arrival_minutes"] = 1200

    with pytest.raises(ValidationError, match="previous departure"):
        DemoTimetableDataset.model_validate(data)


def test_rejects_starting_on_a_later_day() -> None:
    data = timetable_data()
    data["services"][0]["stops"][0]["departure_minutes"] = 1440

    with pytest.raises(ValidationError, match="starting date"):
        DemoTimetableDataset.model_validate(data)


def test_rejects_repeated_station() -> None:
    data = timetable_data()
    data["services"][0]["stops"][-1]["station_code"] = "DEMO_FORT"

    with pytest.raises(ValidationError, match="repeat a station"):
        DemoTimetableDataset.model_validate(data)


def test_rejects_duplicate_service_codes() -> None:
    data = timetable_data()
    data["services"].append(deepcopy(data["services"][0]))

    with pytest.raises(ValidationError, match="Service codes must be unique"):
        DemoTimetableDataset.model_validate(data)


def test_rejects_reversed_validity_dates() -> None:
    data = timetable_data()
    data["valid_until"] = "2025-12-31"

    with pytest.raises(ValidationError, match="validity end date"):
        DemoTimetableDataset.model_validate(data)


@pytest.mark.parametrize("operating_days", [0, 128, True])
def test_rejects_invalid_operating_days(operating_days: object) -> None:
    data = timetable_data()
    data["services"][0]["operating_days"] = operating_days

    with pytest.raises(ValidationError):
        DemoTimetableDataset.model_validate(data)
