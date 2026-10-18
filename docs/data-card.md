# Demonstration timetable data card

## Purpose

This dataset supports repeatable RailConnect portfolio demonstrations:
station selection, dated search, overnight journeys and provenance.

It is not an official timetable, live feed or complete railway network.

## Files

- data/processed/demo_stations.json
- data/processed/demo_timetable.json
- data/processed/demo_timetable.source.json

Timetable source reference: demo-timetable-v1.
Station source reference: demo-stations-v1.

## Origin and reuse basis

Service names, timetable times and operating patterns are project-generated
fictional examples.

Station names represent selected Sri Lankan locations.
DEMO_ station codes are project identifiers, not official railway codes.

No official or third-party timetable text is represented as the source
of these fictional schedules.

Metadata records title, repository location and reuse basis.
External retrieval time is null because no external provider supplied
this timetable.

This card does not establish licensing for future imports.
Check source terms and record reuse basis before importing third-party data.

## Counts and coverage

- 30 selected stations.
- 12 service patterns.
- 42 recurring ordered stops.
- Northern, eastern, central, southern and hill-country examples.
- Daily, weekday, weekend, reverse and overnight examples.

Coverage is selective.
Missing stations/journeys do not establish real service unavailability.

## Effective period

The fictional timetable is valid from 2026-01-01 through 2028-12-31,
inclusive.

These dates define demonstration applicability.
They do not establish observation dates or current railway operations.

## Field meanings

- Service code: stable project identifier.
- operating_days: bit mask, Monday 1 through Sunday 64.
- arrival_minutes/departure_minutes: offsets from midnight on the
  service's starting date in Asia/Colombo.
- Offsets above 1439 represent later calendar days.
- stop_sequence: position in the ordered service stop list.
- pickup_allowed: boarding permission.
- dropoff_allowed: alighting permission.

Omitted demonstration permissions follow departure/arrival presence
respectively. Explicit values are preserved.

## Validation and normalization

Validation strips surrounding text whitespace.

It rejects unknown fields, invalid identifiers/dates, duplicate service codes,
repeated stations within a demonstration service, missing endpoint times,
invalid ordering and permissions without corresponding scheduled times.

Seeding rejects missing/inactive stations and conflicting existing records.

The loader does not rewrite raw file content.
Dataset SHA-256 uses exact file bytes.
Git preserves processed JSON with LF line endings.

## Missingness and limitations

Origin arrival and terminal departure are intentionally absent.

This dataset provides no observed/estimated arrivals, telemetry, fares,
seat inventory, platforms or real operational status.

Intermediate stops are selected examples, not every real stop.

## Dated runs

Explicit materialization creates dated runs from recurring patterns.

Baseline example: 2026-10-12 through 2026-10-18.

- 70 runs created on a fresh table.
- 14 nonoperating service/date combinations skipped.
- Repetition verifies existing runs without duplication.

Other dates must be prepared explicitly.
The Stage 6 manual workflow additionally used 2026-10-19.

Scheduled timestamps are stored in UTC.
Passenger search/display use Asia/Colombo.

Search does not create missing runs.
Empty results can indicate an unprepared range.

## Provenance and import history

Registration stores reference, metadata, effective period and exact content hash.

Registration time means RailConnect registration.
It does not establish operational freshness.

Successful summaries record dataset counts, inserted/existing counts,
importer version and execution context.

Execution context is not authenticated staff identity.

Registration, verification/seeding and summary creation are transactional.
Failure rolls back the operation.

Repeated imports preserve the original successful summary.
Changed content/metadata cannot silently reuse the source reference.

## Update process

1. Prepare candidate data and provenance metadata.
2. Validate and preview differences.
3. Investigate conflicts rather than overwrite existing definitions.
4. Import through the transactional service.
5. Record results and prepare required dated runs.
6. Run regression checks and update this card.

The importer supports insertion and verification.
Replacing service definitions requires a reviewed versioning/migration workflow.

Protected staff import access and actor attribution remain pending.

## Passenger reports and incident scenarios

Reports and incidents are separate from timetable JSON.

Passenger claims begin unverified.
Acceptance does not establish an operational disruption.

Staff verification creates an incident, initial approved revision and audit.
Rejection creates a decision and audit without an incident.

Amendments create new approved revisions.
Resolution records actor, reason, decision time and effective resolution time.

Expected versions protect lifecycle changes.
Business changes and audit writes are atomic.

Protected audit history requires audit.read.
Its reasons, actor references and request IDs are private management data,
not public timetable provenance.

Public incident responses expose approved current facts, lifecycle status,
versions and timetable source reference.

They exclude narrative, private evidence basis, decision reasons and staff IDs.

The timetable reference identifies the schedule source, not incident evidence.

Staff approval does not turn synthetic scenarios into official announcements.

Reporting, review, lifecycle and audit interfaces are implemented.
The complete workflow was manually checked on 2026-10-18.

Verified incidents do not yet change journey results.
Review/lifecycle changes do not overwrite scheduled run-stop timestamps.

## Repeatability

Synthetic API scenarios cover complete lifecycle and rejection workflows.
Each is executed twice with isolated database fixtures.

They verify:

- Decision versions and approved revisions.
- Audit event references.
- Public/private field boundaries.
- No incident after rejection.
- Preserved scheduled timestamps.

See docs/incident-workflow-check.md for commands and browser replay.

These fixtures are not official records or timetable JSON entries.
They do not constitute a persistent production incident seed dataset.

Repeating a browser scenario creates new report/incident references.
Do not assume local UUIDs are portable.

The release requirement for two demonstrations from reset fixtures
remains separate from these isolated API repetitions.

## Remaining limitations

- Fictional, selectively covered schedule.
- No live railway feed or official incident evidence.
- No journey impact calculation from approved incidents yet.
- No protected staff timetable importer or authenticated import attribution yet.
- Final responsive/accessibility review remains outstanding.
