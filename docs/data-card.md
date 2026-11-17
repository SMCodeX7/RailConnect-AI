# Demonstration timetable data card

## Files and coverage

| File | Purpose |
| --- | --- |
| `data/processed/demo_stations.json` | 30 selected stations, source `demo-stations-v1`. |
| `data/processed/demo_timetable.json` | 12 fictional service patterns and 42 recurring stops, source `demo-timetable-v1`. |
| `data/processed/demo_timetable.source.json` | Source title, location, reuse basis and optional retrieval time. |

Service names, times and operating patterns are project-generated. Station
names represent selected Sri Lankan locations and `DEMO_` codes are project
identifiers. The timetable covers selected daily, weekday, weekend and
overnight services from 2026-01-01 through 2028-12-31, inclusive.

The dataset has no external retrieval date, live feed, telemetry, fare data,
seat inventory or platform information. Check the terms of any future
third-party source before reuse.

## Fields and dates

- `operating_days` is a bit mask from Monday 1 through Sunday 64.
- Arrival and departure offsets use minutes from midnight on the service date
  in Asia/Colombo. Offsets above 1439 roll into later days.
- Origins omit arrivals and terminals omit departures. Omitted boarding and
  alighting permissions default from departure and arrival presence.
- `stop_sequence` defines the order of stops.

Operators prepare dated runs explicitly. On a fresh database, the
2026-10-12 through 2026-10-18 baseline creates 70 runs and skips 14
nonoperating combinations. Repetition verifies existing runs. Scheduled times
are stored in UTC and displayed in Asia/Colombo. See [setup](setup.md) for
the date used by the README demo and browser tests.

## Import and provenance

Preview validates stations, service definitions and source metadata. Import
inserts or verifies definitions in one transaction with the source record
and summary. SHA-256 uses the original dataset bytes. Changed content or
metadata cannot reuse a registered source reference.

Staff with `timetable.manage` can preview and import demonstration timetables.
A new staff summary records the authenticated importing user. Repeats retain
the original summary and attribution. A previous CLI import can have an empty
staff reference.

See [setup](setup.md#staff-timetable-import) and
[ADR 0004](adr/0004-dated-runs-and-timetable-provenance.md).

## Incidents

Synthetic reports and approved incidents are stored separately from the
timetable. Pending and rejected reports are excluded from journey effects.

An approved disruption can affect a journey when its scope and effective
window apply to the dated run and selected segment. Delays can produce an
estimated arrival alongside the scheduled arrival. Cancellations and
restrictions can affect journey eligibility. The imported timetable retains
its scheduled timestamps.

Public incident responses expose approved facts and the schedule source
reference. Private narrative, evidence, reasons and staff identities stay
protected. The schedule source reference identifies the timetable used by
the run.
