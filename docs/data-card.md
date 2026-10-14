# Demonstration timetable data card

## Purpose

This dataset supports a repeatable RailConnect portfolio demonstration:
station selection, dated journey search, overnight journeys and source
provenance.

It is not an official timetable, live feed or complete railway network.

## Files

- data/processed/demo_stations.json
- data/processed/demo_timetable.json
- data/processed/demo_timetable.source.json

The timetable source reference is demo-timetable-v1.
Station records use demo-stations-v1.

## Origin and reuse basis

Timetable service names, times and operating patterns are project-generated
fictional examples.

Station names represent selected Sri Lankan locations. DEMO_ station codes
are project identifiers, not official railway codes.

No official timetable or third-party timetable text is represented as the
source of these fictional schedules.

The metadata file records the timetable's title, repository location and
reuse basis. External retrieval time is null because this timetable was
not acquired from an external provider.

This card does not establish licensing for future third-party imports.
Check source terms and record their reuse basis before importing them.

## Counts and coverage

- 30 selected demonstration stations.
- 12 service patterns.
- 42 ordered recurring stops.
- Northern, eastern, central, southern and hill-country examples.
- Daily, weekday, weekend, reverse-direction and overnight examples.

Coverage is selective. Missing stations or journeys do not establish that
real railway services are unavailable.

## Effective period

The fictional timetable is valid from 2026-01-01 through 2028-12-31,
inclusive.

These dates define demonstration schedule applicability.
They are not observation dates or evidence of current railway operations.

## Field meanings

- service code: stable project identifier.
- operating_days: bit mask; Monday is 1, Tuesday is 2, through Sunday at 64.
- arrival_minutes and departure_minutes: offsets from midnight on the
  service's starting date in Asia/Colombo.
- Offsets above 1439 represent subsequent calendar days.
- stop_sequence: position in the service's ordered stop list.
- pickup_allowed: passengers may board at that stop.
- dropoff_allowed: passengers may alight at that stop.

For this demonstration import, omitted permissions follow the presence
of departure and arrival times respectively. Explicit values are preserved.

## Validation and normalization

Validation strips surrounding text whitespace and rejects unknown fields,
invalid identifiers, invalid date ranges, duplicate service codes,
repeated stations within a demonstration service, missing endpoint times,
invalid stop ordering and permissions without corresponding times.

Seeding rejects missing or inactive stations and conflicting existing
service or stop records.

Raw file content is not rewritten by the loader.
The dataset hash is SHA-256 of the exact file bytes.
Git preserves processed JSON files with LF line endings.

## Missingness and limitations

Origin arrival times and terminal departure times are intentionally absent.

No observed or estimated arrival times, telemetry, fares, seat inventory,
platform information or real operational status is supplied by this dataset.

Intermediate stops are selected demonstration stops and do not represent
all stops made by real trains.

## Dated runs

An explicit command materializes recurring patterns into dated runs.

The documented example prepares 2026-10-12 through 2026-10-18:
70 runs, with 14 nonoperating service/date combinations skipped.

Scheduled run-stop timestamps are stored in UTC.
Search and display use Asia/Colombo.

Search does not create missing runs. An empty result can reflect an
unprepared date range rather than the absence of a recurring pattern.

## Provenance and import history

Source registration stores the source reference, metadata, effective
period and exact dataset content hash.

Registration time records when RailConnect registered the source.
It does not establish live railway freshness.

A successful import summary records dataset counts, inserted/existing
counts, importer version and execution context.

Execution context is not authenticated staff identity.

Source registration, timetable seeding and summary creation share one
transaction. Failure rolls back the operation.

Repeated imports verify the source and data and preserve the original
summary. Changed content or metadata cannot silently reuse an existing
source reference.

## Update process

1. Prepare a candidate dataset and provenance metadata.
2. Validate the files and preview database differences.
3. Investigate conflicts rather than overwriting existing records.
4. Import through the transactional application service.
5. Record the import result and prepare the required dated runs.
6. Run regression tests and update this card.

The current demonstration importer supports insertion and verification.
Replacement of existing service definitions requires a separately reviewed
versioning and migration workflow.

A protected staff import interface and authenticated attribution will be
implemented with the staff identity workflow.
