import pytest
from pydantic import ValidationError

from railconnect.modules.timetable.seed_schemas import DemoStop


@pytest.mark.parametrize(
    ("times", "expected_pickup", "expected_dropoff"),
    [
        ({"departure_minutes": 600}, True, False),
        ({"arrival_minutes": 660}, False, True),
        ({"arrival_minutes": 660, "departure_minutes": 665}, True, True),
    ],
)
def test_demo_defaults_follow_available_times(
    times: dict[str, int],
    expected_pickup: bool,
    expected_dropoff: bool,
) -> None:
    stop = DemoStop.model_validate({"station_code": "DEMO_TEST", **times})

    assert stop.pickup_allowed is expected_pickup
    assert stop.dropoff_allowed is expected_dropoff


def test_explicit_permissions_are_preserved() -> None:
    stop = DemoStop.model_validate(
        {
            "station_code": "DEMO_TEST",
            "arrival_minutes": 660,
            "departure_minutes": 665,
            "pickup_allowed": False,
            "dropoff_allowed": False,
        }
    )

    assert stop.pickup_allowed is False
    assert stop.dropoff_allowed is False


@pytest.mark.parametrize(
    "values",
    [
        {"arrival_minutes": 660, "pickup_allowed": True},
        {"departure_minutes": 600, "dropoff_allowed": True},
        {"departure_minutes": 600, "pickup_allowed": "true"},
        {"arrival_minutes": 660, "dropoff_allowed": 1},
    ],
)
def test_rejects_invalid_permissions(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DemoStop.model_validate({"station_code": "DEMO_TEST", **values})
