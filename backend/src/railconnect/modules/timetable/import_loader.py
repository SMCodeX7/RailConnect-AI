from hashlib import sha256
from pathlib import Path

from railconnect.modules.timetable.import_schemas import (
    TimetableImportSnapshot,
    TimetableSourceMetadata,
)
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset

MAX_DATASET_BYTES = 5 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024


def _read_bounded(path: Path, maximum_bytes: int) -> bytes:
    with path.open("rb") as stream:
        content = stream.read(maximum_bytes + 1)

    if len(content) > maximum_bytes:
        raise ValueError(f"Import file exceeds the supported size: {path.name}")

    return content


def load_timetable_snapshot(
    dataset_path: Path,
    metadata_path: Path,
) -> TimetableImportSnapshot:
    return parse_timetable_snapshot(
        _read_bounded(dataset_path, MAX_DATASET_BYTES),
        _read_bounded(metadata_path, MAX_METADATA_BYTES),
    )


def parse_timetable_snapshot(
    dataset_bytes: bytes,
    metadata_bytes: bytes,
) -> TimetableImportSnapshot:
    if len(dataset_bytes) > MAX_DATASET_BYTES:
        raise ValueError("Timetable dataset exceeds the supported size.")

    if len(metadata_bytes) > MAX_METADATA_BYTES:
        raise ValueError("Source metadata exceeds the supported size.")

    dataset = DemoTimetableDataset.model_validate_json(dataset_bytes.decode("utf-8-sig"))
    metadata = TimetableSourceMetadata.model_validate_json(metadata_bytes.decode("utf-8-sig"))

    return TimetableImportSnapshot(
        dataset=dataset,
        metadata=metadata,
        content_sha256=sha256(dataset_bytes).hexdigest(),
    )
