from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from railconnect.modules.timetable.import_loader import MAX_DATASET_BYTES, MAX_METADATA_BYTES

MAX_DATASET_BASE64_LENGTH = 4 * ((MAX_DATASET_BYTES + 2) // 3)
MAX_METADATA_BASE64_LENGTH = 4 * ((MAX_METADATA_BYTES + 2) // 3)
MAX_IMPORT_REQUEST_BYTES = MAX_DATASET_BASE64_LENGTH + MAX_METADATA_BASE64_LENGTH + 1024


class StaffTimetableImportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_base64: str = Field(min_length=1, max_length=MAX_DATASET_BASE64_LENGTH)
    metadata_base64: str = Field(min_length=1, max_length=MAX_METADATA_BASE64_LENGTH)


class StaffTimetablePreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_ref: str
    content_sha256: str
    source_registered: bool
    import_recorded: bool
    new_service_codes: tuple[str, ...]
    existing_service_codes: tuple[str, ...]
    stops_to_insert: int
    conflicts: tuple[str, ...]
    can_import: bool


class StaffTimetableImportResponse(BaseModel):
    source_id: UUID
    source_ref: str
    content_sha256: str
    import_id: UUID
    summary_created: bool
    imported_by_user_id: UUID | None
    inserted_services: int
    existing_services: int
    inserted_stops: int
