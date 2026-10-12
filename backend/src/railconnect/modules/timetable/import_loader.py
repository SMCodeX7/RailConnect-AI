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
    dataset_bytes = _read_bounded(dataset_path, MAX_DATASET_BYTES)
    metadata_bytes = _read_bounded(metadata_path, MAX_METADATA_BYTES)

    dataset = DemoTimetableDataset.model_validate_json(dataset_bytes.decode("utf-8-sig"))
    metadata = TimetableSourceMetadata.model_validate_json(metadata_bytes.decode("utf-8-sig"))

    return TimetableImportSnapshot(
        dataset=dataset,
        metadata=metadata,
        content_sha256=sha256(dataset_bytes).hexdigest(),
    )
