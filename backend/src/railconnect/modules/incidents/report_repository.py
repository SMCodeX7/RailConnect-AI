from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.identity.models.user import User
from railconnect.modules.incidents.errors import InvalidReportError
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.report_schemas import SubmitReportInput
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun


def validate_report_references(
    session: Session,
    data: SubmitReportInput,
    submitted_by_user_id: UUID | None,
) -> None:
    if submitted_by_user_id is not None:
        user = session.scalar(select(User).where(User.id == submitted_by_user_id).with_for_update())
        if user is None or not user.is_active:
            raise InvalidReportError("The submitting staff account is unavailable.")

    if data.station_hint_id is not None:
        station = session.get(Station, data.station_hint_id)
        if station is None or not station.is_active:
            raise InvalidReportError("The station hint is unavailable.")

    if data.run_hint_id is None:
        return

    run = session.get(ServiceRun, data.run_hint_id)
    if run is None:
        raise InvalidReportError("The dated service run hint does not exist.")

    stops = session.scalars(
        select(RunStop).where(RunStop.run_id == data.run_hint_id).order_by(RunStop.stop_sequence)
    ).all()

    if not stops:
        raise InvalidReportError("The dated service run has no prepared stops.")

    if data.station_hint_id is not None:
        station_ids = {stop.station_id for stop in stops}
        if data.station_hint_id not in station_ids:
            raise InvalidReportError("The station hint is not on the dated service run.")

    departure = data.departure_stop_sequence_hint
    arrival = data.arrival_stop_sequence_hint

    if departure is None and arrival is None:
        return

    sequences = {stop.stop_sequence for stop in stops}

    if departure not in sequences or arrival not in sequences:
        raise InvalidReportError("The segment hints do not identify stops on the run.")

    if data.station_hint_id is not None:
        segment_station_ids = {
            stop.station_id
            for stop in stops
            if departure is not None
            and arrival is not None
            and departure <= stop.stop_sequence <= arrival
        }

        if data.station_hint_id not in segment_station_ids:
            raise InvalidReportError("The station hint is outside the hinted segment.")


def create_pending_report(
    session: Session,
    data: SubmitReportInput,
    submitted_at: datetime,
    submitted_by_user_id: UUID | None,
) -> IncidentReport:
    report = IncidentReport(
        title=data.title,
        narrative=data.narrative,
        observed_at=data.observed_at,
        submitted_at=submitted_at,
        submitted_by_user_id=submitted_by_user_id,
        run_hint_id=data.run_hint_id,
        station_hint_id=data.station_hint_id,
        departure_stop_sequence_hint=data.departure_stop_sequence_hint,
        arrival_stop_sequence_hint=data.arrival_stop_sequence_hint,
        status="pending",
        version=1,
    )

    session.add(report)
    session.flush()
    return report
