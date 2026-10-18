from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.models import Base
from railconnect.db.session import create_db_engine
from railconnect.modules.identity.models.auth_session import AuthSession
from railconnect.modules.identity.models.role import Role
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.session_service import (
    AuthenticatedSession,
    authenticate_staff_session,
)
from railconnect.modules.identity.tokens import (
    generate_csrf_token,
    generate_session_token,
    hash_session_token,
)
from railconnect.modules.incidents.errors import (
    IncidentConflictError,
    ReportReviewConflictError,
)
from railconnect.modules.incidents.lifecycle_schemas import (
    AmendIncidentInput,
    ResolveIncidentInput,
)
from railconnect.modules.incidents.lifecycle_service import (
    amend_incident,
    resolve_incident,
)
from railconnect.modules.incidents.models.incident import Incident
from railconnect.modules.incidents.models.incident_audit_event import IncidentAuditEvent
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.models.incident_revision import IncidentRevision
from railconnect.modules.incidents.review_decision_service import (
    reject_report,
    verify_report,
)
from railconnect.modules.incidents.review_schemas import (
    RejectReportInput,
    VerifyReportInput,
)
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.train_service import TrainService


@pytest.mark.parametrize(
    ("first_action", "second_action"),
    [
        ("verify", "reject"),
        ("amend", "amend"),
        ("amend", "resolve"),
        ("resolve", "resolve"),
    ],
)
def test_concurrent_decisions_allow_only_one_winner(
    first_action: str,
    second_action: str,
) -> None:
    database_settings = Settings()

    if database_settings.database_url is None:
        pytest.skip("PostgreSQL is required for concurrency tests.")

    if database_settings.environment not in {"development", "test"}:
        pytest.fail("Concurrency tests require a development or test database.")

    settings = Settings(
        _env_file=None,
        environment="test",
        session_cookie_secure=False,
    )
    engine = create_db_engine(database_settings)

    schema_name = f"review_test_{uuid4().hex}"
    isolated_engine = engine.execution_options(schema_translate_map={None: schema_name})
    schema_created = False
    now = datetime(2026, 10, 18, 6, 0, tzinfo=UTC)
    lifecycle_race = first_action != "verify"

    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema_name}"')
        schema_created = True

        Base.metadata.create_all(isolated_engine)

        with Session(isolated_engine) as session:
            with session.begin():
                role = Role(
                    code="controller",
                    display_name="Controller",
                )
                users = [
                    User(
                        username=f"reviewer_{index}_{uuid4().hex}",
                        display_name=f"Synthetic Reviewer {index}",
                        password_hash="unused-concurrency-test-hash",
                        is_active=True,
                        auth_version=1,
                    )
                    for index in (1, 2)
                ]
                stations = [
                    Station(
                        code=f"DEMO_RACE_{index}",
                        name=f"Synthetic Race Station {index}",
                        source_ref="review-concurrency-test",
                        is_active=True,
                    )
                    for index in (1, 2)
                ]
                service = TrainService(
                    code="DEMO_REVIEW_RACE",
                    name="Synthetic Review Race Service",
                    source_ref="review-concurrency-test",
                    operating_days=127,
                    valid_from=now.date(),
                    valid_until=now.date() + timedelta(days=7),
                    is_active=True,
                )

                session.add_all([role, service, *users, *stations])
                session.flush()

                session.add_all([UserRole(user_id=user.id, role_id=role.id) for user in users])

                run = ServiceRun(
                    service_id=service.id,
                    service_date=now.date(),
                    source_ref="review-concurrency-test",
                    status="scheduled",
                    version=1,
                )
                session.add(run)
                session.flush()

                session.add_all(
                    [
                        RunStop(
                            run_id=run.id,
                            station_id=stations[0].id,
                            stop_sequence=1,
                            scheduled_departure_at=now + timedelta(hours=1),
                            pickup_allowed=True,
                            dropoff_allowed=False,
                        ),
                        RunStop(
                            run_id=run.id,
                            station_id=stations[1].id,
                            stop_sequence=2,
                            scheduled_arrival_at=now + timedelta(hours=2),
                            pickup_allowed=False,
                            dropoff_allowed=True,
                        ),
                    ]
                )

                report = IncidentReport(
                    title="Synthetic concurrent review",
                    narrative="An unverified synthetic passenger claim.",
                    observed_at=now - timedelta(minutes=10),
                    submitted_at=now - timedelta(minutes=5),
                    status="pending",
                    version=1,
                )
                session.add(report)

                tokens = [generate_session_token() for _ in users]
                session.add_all(
                    [
                        AuthSession(
                            user_id=user.id,
                            token_hash=hash_session_token(token),
                            csrf_token=generate_csrf_token(),
                            auth_version=1,
                            created_at=now,
                            last_seen_at=now,
                            expires_at=now + timedelta(hours=8),
                        )
                        for user, token in zip(users, tokens, strict=True)
                    ]
                )
                session.flush()

                authenticated = [
                    authenticate_staff_session(
                        session,
                        token,
                        settings,
                        now,
                    )
                    for token in tokens
                ]
                report_id = report.id
                run_id = run.id

        verify_input = VerifyReportInput.model_validate(
            {
                "expected_version": 1,
                "reason": "Synthetic concurrent verification.",
                "approved": {
                    "run_id": str(run_id),
                    "scope_kind": "run",
                    "impact_kind": "delay",
                    "estimated_delay_minutes": 15,
                    "effective_from": now,
                    "effective_until": now + timedelta(hours=4),
                    "public_summary": "Synthetic demonstration delay.",
                    "evidence_basis": "Controlled concurrency test.",
                },
            }
        )
        reject_input = RejectReportInput(
            expected_version=1,
            reason="Synthetic concurrent rejection.",
        )
        amend_input = AmendIncidentInput(
            expected_version=1,
            reason="Synthetic concurrent amendment.",
            approved=verify_input.approved.model_copy(update={"estimated_delay_minutes": 30}),
        )
        resolve_input = ResolveIncidentInput(
            expected_version=1,
            reason="Synthetic concurrent resolution.",
            resolution_effective_at=now,
        )

        incident_id = None
        initial_revision_id = None

        if lifecycle_race:
            with Session(isolated_engine) as session:
                initial = verify_report(
                    session,
                    authenticated[0],
                    report_id,
                    verify_input,
                    request_id=f"initial-{uuid4().hex}",
                    now=now,
                )
                incident_id = initial.incident_id
                initial_revision_id = initial.revision_id

            assert incident_id is not None
            assert initial_revision_id is not None

        barrier = Barrier(2)

        def decide(
            action: str,
            actor: AuthenticatedSession,
        ) -> str:
            with isolated_engine.connect() as connection:
                connection.exec_driver_sql("SET statement_timeout = '10s'")
                connection.commit()

                try:
                    with Session(bind=connection) as session:
                        barrier.wait(timeout=15)
                        request_id = f"race-{uuid4().hex}"

                        try:
                            if action == "verify":
                                verify_report(
                                    session,
                                    actor,
                                    report_id,
                                    verify_input,
                                    request_id=request_id,
                                    now=now,
                                )
                            elif action == "reject":
                                reject_report(
                                    session,
                                    actor,
                                    report_id,
                                    reject_input,
                                    request_id=request_id,
                                    now=now,
                                )
                            elif action == "amend":
                                assert incident_id is not None
                                amend_incident(
                                    session,
                                    actor,
                                    incident_id,
                                    amend_input,
                                    request_id=request_id,
                                    now=now,
                                )
                            else:
                                assert action == "resolve"
                                assert incident_id is not None
                                resolve_incident(
                                    session,
                                    actor,
                                    incident_id,
                                    resolve_input,
                                    request_id=request_id,
                                    now=now,
                                )

                            return action
                        except (
                            ReportReviewConflictError,
                            IncidentConflictError,
                        ):
                            return "conflict"
                finally:
                    connection.exec_driver_sql("RESET statement_timeout")
                    connection.commit()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                decide,
                first_action,
                authenticated[0],
            )
            second_future = executor.submit(
                decide,
                second_action,
                authenticated[1],
            )
            results = [
                first_future.result(timeout=30),
                second_future.result(timeout=30),
            ]

        assert results.count("conflict") == 1
        winners = [result for result in results if result != "conflict"]
        assert len(winners) == 1
        winner = winners[0]

        with Session(isolated_engine) as session:
            stored_report = session.get(IncidentReport, report_id)
            assert stored_report is not None
            assert stored_report.version == 2

            audits = session.scalars(
                select(IncidentAuditEvent).where(IncidentAuditEvent.report_id == report_id)
            ).all()
            incidents = session.scalars(
                select(Incident).where(Incident.originating_report_id == report_id)
            ).all()
            revisions = session.scalars(select(IncidentRevision)).all()

            if not lifecycle_race:
                expected_status = "verified" if winner == "verify" else "rejected"
                assert stored_report.status == expected_status
                assert len(audits) == 1
                assert audits[0].action == f"report_{expected_status}"
                assert audits[0].report_version == 2

                if winner == "verify":
                    assert len(incidents) == 1
                    assert len(revisions) == 1
                    assert incidents[0].version == 1
                    assert revisions[0].incident_id == incidents[0].id
                    assert audits[0].revision_id == revisions[0].id
                else:
                    assert incidents == []
                    assert revisions == []
                    assert audits[0].incident_id is None
            else:
                assert stored_report.status == "verified"
                assert len(incidents) == 1
                incident = incidents[0]
                assert incident.id == incident_id
                assert incident.version == 2
                assert len(audits) == 2

                changes = [audit for audit in audits if audit.action != "report_verified"]
                assert len(changes) == 1
                change = changes[0]
                assert change.incident_version == 2
                assert change.report_version == 2
                assert change.incident_id == incident.id

                original = session.get(
                    IncidentRevision,
                    initial_revision_id,
                )
                assert original is not None
                assert original.revision_number == 1
                assert original.estimated_delay_minutes == 15

                if winner == "amend":
                    assert incident.status == "active"
                    assert incident.current_revision_number == 2
                    assert len(revisions) == 2
                    assert change.action == "incident_revised"

                    latest = next(
                        revision for revision in revisions if revision.revision_number == 2
                    )
                    assert latest.estimated_delay_minutes == 30
                    assert change.revision_id == latest.id
                else:
                    assert incident.status == "resolved"
                    assert incident.current_revision_number == 1
                    assert incident.resolution_effective_at == now
                    assert len(revisions) == 1
                    assert change.action == "incident_resolved"
                    assert change.revision_id == original.id

    finally:
        try:
            if schema_created:
                with engine.begin() as connection:
                    connection.exec_driver_sql(f'DROP SCHEMA "{schema_name}" CASCADE')
        finally:
            engine.dispose()
