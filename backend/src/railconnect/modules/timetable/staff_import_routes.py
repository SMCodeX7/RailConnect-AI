from base64 import b64decode
from binascii import Error as Base64Error
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg.errors import DeadlockDetected, SerializationFailure, UniqueViolation
from sqlalchemy.exc import DBAPIError

from railconnect.modules.identity.dependencies import (
    NO_STORE_HEADERS,
    IdentitySession,
    require_staff_permission,
)
from railconnect.modules.identity.permissions import Permission
from railconnect.modules.identity.session_service import AuthenticatedSession
from railconnect.modules.timetable.import_loader import parse_timetable_snapshot
from railconnect.modules.timetable.import_preview import preview_timetable_import
from railconnect.modules.timetable.import_schemas import TimetableImportSnapshot
from railconnect.modules.timetable.import_service import import_timetable
from railconnect.modules.timetable.staff_import_schemas import (
    MAX_IMPORT_REQUEST_BYTES,
    StaffTimetableImportInput,
    StaffTimetableImportResponse,
    StaffTimetablePreviewResponse,
)

router = APIRouter(prefix="/staff/timetable/imports", tags=["Staff timetable"])

TimetableManager = Annotated[
    AuthenticatedSession,
    Depends(require_staff_permission(Permission.TIMETABLE_MANAGE, mutation=True)),
]


async def read_import_input(
    request: Request,
    authenticated: TimetableManager,
) -> StaffTimetableImportInput:
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(status_code=415, headers=NO_STORE_HEADERS)

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_IMPORT_REQUEST_BYTES:
            raise HTTPException(status_code=413, headers=NO_STORE_HEADERS)
        body.extend(chunk)

    try:
        return StaffTimetableImportInput.model_validate_json(body)
    except ValueError as error:
        raise HTTPException(status_code=422, headers=NO_STORE_HEADERS) from error


ImportInput = Annotated[StaffTimetableImportInput, Depends(read_import_input)]


def parse_import_input(data: StaffTimetableImportInput) -> TimetableImportSnapshot:
    try:
        return parse_timetable_snapshot(
            b64decode(data.dataset_base64, validate=True),
            b64decode(data.metadata_base64, validate=True),
        )
    except (Base64Error, ValueError) as error:
        raise HTTPException(status_code=422, headers=NO_STORE_HEADERS) from error


@router.post("/preview", response_model=StaffTimetablePreviewResponse)
def post_timetable_preview(
    data: ImportInput,
    response: Response,
    session: IdentitySession,
) -> StaffTimetablePreviewResponse:
    snapshot = parse_import_input(data)

    with session.begin():
        preview = preview_timetable_import(session, snapshot)
        result = StaffTimetablePreviewResponse.model_validate(preview)

    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("", response_model=StaffTimetableImportResponse)
def post_timetable_import(
    data: ImportInput,
    response: Response,
    authenticated: TimetableManager,
    session: IdentitySession,
) -> StaffTimetableImportResponse:
    snapshot = parse_import_input(data)
    actor_id = UUID(authenticated.actor.user_id)

    try:
        with session.begin():
            imported = import_timetable(
                session,
                snapshot,
                execution_context="staff-api",
                imported_by_user_id=actor_id,
            )
            result = StaffTimetableImportResponse(
                source_id=imported.source.id,
                source_ref=imported.source.source_ref,
                content_sha256=imported.source.content_sha256,
                import_id=imported.summary.id,
                summary_created=imported.summary_created,
                imported_by_user_id=imported.summary.imported_by_user_id,
                inserted_services=imported.seed_result.inserted_services,
                existing_services=imported.seed_result.existing_services,
                inserted_stops=imported.seed_result.inserted_stops,
            )
    except ValueError as error:
        raise HTTPException(status_code=409, headers=NO_STORE_HEADERS) from error
    except DBAPIError as error:
        cause = error.orig
        if isinstance(cause, (DeadlockDetected, SerializationFailure)) or (
            isinstance(cause, UniqueViolation)
            and cause.diag.constraint_name in {"pk_train_services", "uq_train_services_code"}
        ):
            raise HTTPException(status_code=409, headers=NO_STORE_HEADERS) from error
        raise

    response.headers["Cache-Control"] = "no-store"
    return result
