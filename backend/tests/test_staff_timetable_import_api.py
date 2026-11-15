from base64 import b64encode
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.modules.identity.dependencies import (
    get_identity_clock,
    get_identity_session,
)
from railconnect.modules.identity.passwords import hash_password
from railconnect.modules.identity.permissions import RoleCode
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user
from railconnect.modules.timetable import import_service
from railconnect.modules.timetable.import_loader import parse_timetable_snapshot
from railconnect.modules.timetable.import_schemas import TimetableSourceMetadata
from railconnect.modules.timetable.import_service import import_timetable
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.models.source_record import SourceRecord
from railconnect.modules.timetable.models.timetable_import import TimetableImport
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import SeedResult, seed_timetable

ORIGIN = "http://127.0.0.1:5173"
NOW = datetime(2026, 10, 19, 6, tzinfo=UTC)
PASSWORD = "Fictional timetable API test passphrase"
IMPORT_URL = "/api/v1/staff/timetable/imports"
PREVIEW_URL = f"{IMPORT_URL}/preview"


@dataclass
class TimetableAPI:
    client: TestClient
    database: Session
    dataset: DemoTimetableDataset
    dataset_bytes: bytes
    metadata_bytes: bytes
    password_hash: str

    def payload(self) -> dict[str, str]:
        return {
            "dataset_base64": b64encode(self.dataset_bytes).decode("ascii"),
            "metadata_base64": b64encode(self.metadata_bytes).decode("ascii"),
        }

    def sign_in(self, role: RoleCode) -> tuple[UUID, dict[str, str]]:
        user = provision_staff_user(
            self.database,
            ProvisionStaffInput(
                username=f"import_{uuid4().hex}",
                display_name="Synthetic Timetable Staff",
                role=role,
            ),
            self.password_hash,
        )
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": PASSWORD},
            headers={"Origin": ORIGIN},
        )
        assert response.status_code == 200, response.text
        token = response.json()["csrf_token"]
        assert isinstance(token, str)
        return user.id, {"Origin": ORIGIN, "X-CSRF-Token": token}


@pytest.fixture(scope="module")
def timetable_api_password_hash() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def timetable_api(
    timetable_database: tuple[Session, DemoTimetableDataset],
    timetable_api_password_hash: str,
) -> Iterator[TimetableAPI]:
    database, fixture_dataset = timetable_database
    dataset = fixture_dataset.model_copy(update={"source_ref": f"test-import-{uuid4().hex}"})
    metadata = TimetableSourceMetadata(
        title="Synthetic API timetable",
        source_uri="test-fixtures/timetable.json",
        reuse_basis="Project-generated fictional test data.",
    )
    dataset_bytes = (
        b"\xef\xbb\xbf" + dataset.model_dump_json(indent=2).replace("\n", "\r\n").encode() + b"\r\n"
    )

    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            database_url=None,
            session_cookie_secure=False,
            trusted_origins=[ORIGIN],
        )
    )

    def override_session() -> Iterator[Session]:
        with Session(
            bind=database.get_bind(),
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_identity_session] = override_session
    app.dependency_overrides[get_identity_clock] = lambda: lambda: NOW

    try:
        with TestClient(app, base_url="https://testserver") as client:
            yield TimetableAPI(
                client=client,
                database=database,
                dataset=dataset,
                dataset_bytes=dataset_bytes,
                metadata_bytes=metadata.model_dump_json().encode(),
                password_hash=timetable_api_password_hash,
            )
    finally:
        app.dependency_overrides.clear()


def timetable_counts(session: Session) -> tuple[int | None, ...]:
    return tuple(
        session.scalar(select(func.count()).select_from(model))
        for model in (SourceRecord, TimetableImport, TrainService, ServiceStop)
    )


@pytest.mark.parametrize("url", [PREVIEW_URL, IMPORT_URL])
@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("anonymous", 401),
        ("controller", 403),
        ("wrong-origin", 403),
        ("missing-csrf", 403),
        ("invalid-csrf", 403),
    ],
)
def test_staff_timetable_access(
    timetable_api: TimetableAPI,
    url: str,
    case: str,
    expected: int,
) -> None:
    context = timetable_api
    headers = {"Origin": ORIGIN, "X-CSRF-Token": "0" * 64}

    if case != "anonymous":
        role = RoleCode.CONTROLLER if case == "controller" else RoleCode.ADMINISTRATOR
        _, headers = context.sign_in(role)

    if case == "wrong-origin":
        headers["Origin"] = "https://untrusted.example"
    elif case == "missing-csrf":
        del headers["X-CSRF-Token"]
    elif case == "invalid-csrf":
        headers["X-CSRF-Token"] = "0" * 64

    before = timetable_counts(context.database)
    response = context.client.post(url, json=context.payload(), headers=headers)

    assert response.status_code == expected, response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert timetable_counts(context.database) == before


@pytest.mark.parametrize("url", [PREVIEW_URL, IMPORT_URL])
@pytest.mark.parametrize("invalid_input", ["bad-base64", "client-supplied-actor"])
def test_staff_timetable_rejects_invalid_input(
    timetable_api: TimetableAPI,
    url: str,
    invalid_input: str,
) -> None:
    context = timetable_api
    actor_id, headers = context.sign_in(RoleCode.ADMINISTRATOR)
    payload = context.payload()
    if invalid_input == "bad-base64":
        payload["dataset_base64"] = "not valid base64!"
    else:
        payload["imported_by_user_id"] = str(actor_id)

    before = timetable_counts(context.database)
    response = context.client.post(url, json=payload, headers=headers)

    assert response.status_code == 422, response.text
    assert timetable_counts(context.database) == before


def test_preview_import_and_repeat_preserve_exact_bytes_and_attribution(
    timetable_api: TimetableAPI,
) -> None:
    context = timetable_api
    actor_id, headers = context.sign_in(RoleCode.ADMINISTRATOR)
    before = timetable_counts(context.database)
    expected_hash = sha256(context.dataset_bytes).hexdigest()
    payload = context.payload()

    preview = context.client.post(PREVIEW_URL, json=payload, headers=headers)

    assert preview.status_code == 200, preview.text
    assert preview.headers["Cache-Control"] == "no-store"
    body = preview.json()
    assert body["can_import"] is True
    assert body["source_registered"] is False
    assert body["import_recorded"] is False
    assert body["content_sha256"] == expected_hash
    assert body["new_service_codes"] == [service.code for service in context.dataset.services]
    assert body["stops_to_insert"] == 6
    assert timetable_counts(context.database) == before

    first = context.client.post(IMPORT_URL, json=payload, headers=headers)

    assert first.status_code == 200, first.text
    assert first.headers["Cache-Control"] == "no-store"
    first_body = first.json()
    assert first_body["summary_created"] is True
    assert first_body["content_sha256"] == expected_hash
    assert first_body["imported_by_user_id"] == str(actor_id)
    assert first_body["inserted_services"] == 2
    assert first_body["existing_services"] == 0
    assert first_body["inserted_stops"] == 6

    stored = context.database.get(TimetableImport, UUID(first_body["import_id"]))
    assert stored is not None
    assert stored.imported_by_user_id == actor_id
    assert stored.execution_context == "staff-api"
    original_time = stored.imported_at
    after_first = timetable_counts(context.database)

    repeat_actor, repeat_headers = context.sign_in(RoleCode.ADMINISTRATOR)
    assert repeat_actor != actor_id
    repeat = context.client.post(IMPORT_URL, json=payload, headers=repeat_headers)

    assert repeat.status_code == 200, repeat.text
    repeated_body = repeat.json()
    assert repeated_body["summary_created"] is False
    assert repeated_body["source_id"] == first_body["source_id"]
    assert repeated_body["import_id"] == first_body["import_id"]
    assert repeated_body["imported_by_user_id"] == str(actor_id)
    assert repeated_body["inserted_services"] == 0
    assert repeated_body["existing_services"] == 2
    assert repeated_body["inserted_stops"] == 0
    assert timetable_counts(context.database) == after_first
    context.database.refresh(stored)
    assert stored.imported_at == original_time
    assert stored.inserted_services == 2


def test_staff_repeat_preserves_cli_attribution(timetable_api: TimetableAPI) -> None:
    context = timetable_api
    snapshot = parse_timetable_snapshot(context.dataset_bytes, context.metadata_bytes)
    cli = import_timetable(context.database, snapshot, execution_context="test-cli")
    _, headers = context.sign_in(RoleCode.ADMINISTRATOR)
    before = timetable_counts(context.database)

    response = context.client.post(IMPORT_URL, json=context.payload(), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["import_id"] == str(cli.summary.id)
    assert body["summary_created"] is False
    assert body["imported_by_user_id"] is None
    context.database.refresh(cli.summary)
    assert cli.summary.execution_context == "test-cli"
    assert cli.summary.imported_by_user_id is None
    assert timetable_counts(context.database) == before


def test_import_rechecks_after_preview(timetable_api: TimetableAPI) -> None:
    context = timetable_api
    _, headers = context.sign_in(RoleCode.ADMINISTRATOR)
    payload = context.payload()

    ready = context.client.post(PREVIEW_URL, json=payload, headers=headers)
    assert ready.status_code == 200, ready.text
    assert ready.json()["can_import"] is True

    seed_timetable(context.database, context.dataset)
    service = context.database.scalar(
        select(TrainService).where(TrainService.code == context.dataset.services[0].code)
    )
    assert service is not None
    service.name = "Changed after preview"
    context.database.flush()
    before = timetable_counts(context.database)

    rejected = context.client.post(IMPORT_URL, json=payload, headers=headers)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "CONFLICT"
    assert timetable_counts(context.database) == before

    blocked = context.client.post(PREVIEW_URL, json=payload, headers=headers)
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["can_import"] is False
    assert blocked.json()["conflicts"]
    assert timetable_counts(context.database) == before


def test_import_rolls_back_after_timetable_rows_are_written(
    timetable_api: TimetableAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = timetable_api
    _, headers = context.sign_in(RoleCode.ADMINISTRATOR)
    before = timetable_counts(context.database)

    def seed_then_conflict(session: Session, dataset: DemoTimetableDataset) -> SeedResult:
        result = seed_timetable(session, dataset)
        assert result.inserted_services == 2
        assert result.inserted_stops == 6
        raise ValueError("Synthetic conflict after timetable rows were flushed.")

    monkeypatch.setattr(import_service, "seed_timetable", seed_then_conflict)

    response = context.client.post(IMPORT_URL, json=context.payload(), headers=headers)

    assert response.status_code == 409, response.text
    assert timetable_counts(context.database) == before
