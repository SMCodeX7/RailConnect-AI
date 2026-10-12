from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.import_schemas import TimetableImportSnapshot
from railconnect.modules.timetable.models.source_record import SourceRecord
from railconnect.modules.timetable.models.timetable_import import TimetableImport
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.seeding import verify_existing_service


@dataclass(frozen=True)
class TimetableImportPreview:
    source_ref: str
    content_sha256: str
    source_registered: bool
    import_recorded: bool
    new_service_codes: tuple[str, ...]
    existing_service_codes: tuple[str, ...]
    stops_to_insert: int
    conflicts: tuple[str, ...]

    @property
    def can_import(self) -> bool:
        return not self.conflicts


def verify_source_record(
    source: SourceRecord,
    snapshot: TimetableImportSnapshot,
) -> None:
    actual = (
        source.source_ref,
        source.title,
        source.source_uri,
        source.reuse_basis,
        source.data_kind,
        source.content_sha256,
        source.effective_from,
        source.effective_until,
        source.retrieved_at,
    )
    expected = (
        snapshot.dataset.source_ref,
        snapshot.metadata.title,
        snapshot.metadata.source_uri,
        snapshot.metadata.reuse_basis,
        snapshot.dataset.kind,
        snapshot.content_sha256,
        snapshot.dataset.valid_from,
        snapshot.dataset.valid_until,
        snapshot.metadata.retrieved_at,
    )

    if actual != expected:
        raise ValueError(
            "Registered source metadata or content differs. "
            "Do not reuse its source reference for changed data."
        )


def preview_timetable_import(
    session: Session,
    snapshot: TimetableImportSnapshot,
) -> TimetableImportPreview:
    if session.new or session.dirty or session.deleted:
        raise ValueError("Preview requires a session without pending changes.")

    dataset = snapshot.dataset
    conflicts: list[str] = []
    new_codes: list[str] = []
    existing_codes: list[str] = []
    stops_to_insert = 0
    import_recorded = False

    with session.no_autoflush:
        source = session.scalar(
            select(SourceRecord).where(SourceRecord.source_ref == dataset.source_ref)
        )

        if source is not None:
            try:
                verify_source_record(source, snapshot)
            except ValueError as error:
                conflicts.append(str(error))

            summary = session.scalar(
                select(TimetableImport).where(TimetableImport.source_id == source.id)
            )
            import_recorded = summary is not None

            if summary is not None:
                expected_stops = sum(len(service.stops) for service in dataset.services)
                if (
                    summary.services_in_dataset != len(dataset.services)
                    or summary.stops_in_dataset != expected_stops
                ):
                    conflicts.append("Recorded import counts differ from the dataset.")

        required_codes = {
            stop.station_code for service in dataset.services for stop in service.stops
        }
        stations = list(session.scalars(select(Station).where(Station.code.in_(required_codes))))
        station_ids = {station.code: station.id for station in stations}
        missing = sorted(required_codes - station_ids.keys())
        inactive = sorted(station.code for station in stations if not station.is_active)

        if missing:
            conflicts.append(f"Missing stations: {', '.join(missing)}")

        if inactive:
            conflicts.append(f"Inactive stations: {', '.join(inactive)}")

        service_codes = [service.code for service in dataset.services]
        services = list(
            session.scalars(select(TrainService).where(TrainService.code.in_(service_codes)))
        )
        by_code = {service.code: service for service in services}

        for expected in dataset.services:
            existing = by_code.get(expected.code)

            if existing is None:
                new_codes.append(expected.code)
                stops_to_insert += len(expected.stops)
                continue

            existing_codes.append(expected.code)

            if not missing:
                try:
                    verify_existing_service(
                        session,
                        existing,
                        expected,
                        dataset,
                        station_ids,
                    )
                except ValueError as error:
                    conflicts.append(str(error))

        if import_recorded and new_codes:
            conflicts.append(
                "A recorded import is missing services. "
                "Investigate the inconsistency before importing."
            )

    return TimetableImportPreview(
        source_ref=dataset.source_ref,
        content_sha256=snapshot.content_sha256,
        source_registered=source is not None,
        import_recorded=import_recorded,
        new_service_codes=tuple(new_codes),
        existing_service_codes=tuple(existing_codes),
        stops_to_insert=stops_to_insert,
        conflicts=tuple(conflicts),
    )
