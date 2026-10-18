from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.incidents.errors import InvalidApprovedIncidentError
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.review_schemas import ApprovedIncidentInput
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun


def list_pending_reports(
    session: Session,
    limit: int,
    offset: int,
) -> tuple[Sequence[IncidentReport], int]:
    total = session.scalar(
        select(func.count()).select_from(IncidentReport).where(IncidentReport.status == "pending")
    )
    assert total is not None

    reports = session.scalars(
        select(IncidentReport)
        .where(IncidentReport.status == "pending")
        .order_by(
            IncidentReport.submitted_at,
            IncidentReport.id,
        )
        .limit(limit)
        .offset(offset)
    ).all()

    return reports, total


def get_report_for_review(
    session: Session,
    report_id: UUID,
) -> IncidentReport | None:
    return session.scalar(
        select(IncidentReport)
        .where(IncidentReport.id == report_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def validate_approved_run_scope(
    session: Session,
    approved: ApprovedIncidentInput,
) -> None:
    run = session.scalar(
        select(ServiceRun)
        .where(ServiceRun.id == approved.run_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if run is None:
        raise InvalidApprovedIncidentError("The approved dated service run does not exist.")

    sequences = set(
        session.scalars(
            select(RunStop.stop_sequence).where(RunStop.run_id == approved.run_id)
        ).all()
    )

    if len(sequences) < 2:
        raise InvalidApprovedIncidentError("The approved run requires at least two prepared stops.")

    if approved.scope_kind == "segment":
        if (
            approved.departure_stop_sequence not in sequences
            or approved.arrival_stop_sequence not in sequences
        ):
            raise InvalidApprovedIncidentError(
                "The approved segment endpoints do not belong to the run."
            )
