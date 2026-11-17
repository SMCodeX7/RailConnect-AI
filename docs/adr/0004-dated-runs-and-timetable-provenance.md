# ADR 0004: Dated runs and timetable provenance

## Status

Accepted

## Context

Journey search needs stable run identities and ordered scheduled stops.
Timetable definitions need identifiable source versions and import history.

## Decision

Keep recurring patterns in `train_services`. Materialise dated runs with a
unique service/date pair, status and version. Store ordered run stops with
station identity, UTC scheduled timestamps and boarding/alighting permissions.
Prepare runs explicitly. Public journey search reads prepared runs.

`service_date` is the run start date. `travel_date` is the passenger boarding
date in Asia/Colombo. Details use `run_id` and optional paired stop sequences.
The inclusive `arrive_before` uses local time and defaults to `travel_date`.
An explicit `arrival_date` requires `arrive_before` and cannot precede travel.

Recurring offsets use integer minutes. Second-resolution inputs require a
schema and import contract change.

## Provenance and imports

`source_ref` resolves a registered source version by value. Source records
hold metadata, validity dates and the exact dataset SHA-256. Legacy
unregistered references return `source: null`. Registration and retrieval
timestamps describe provenance.

Preview writes no timetable records. Source registration, timetable writes
and the successful summary share a caller-owned transaction. Imports of the
same source use a PostgreSQL transaction advisory lock. Import rechecks the
candidate. Existing definitions are verified and identical repeats retain the
original summary. Source-version replacement requires a separate workflow.

Staff endpoints require a valid session, `timetable.manage`, allowed Origin
and a session-bound CSRF token. The server records the authenticated user
when creating a staff import summary. Historical and CLI summaries may have
no staff attribution. Both CLI and API hash the original dataset bytes.

## Consequences

Operators prepare coverage dates after importing recurring definitions.
Stable run identities support incident references. Journey responses retain
scheduled timestamps and expose applicable disruption estimates separately.
See the [incident decision](0003-incident-reporting.md#journey-integration)
for the effect matching and estimation rules.
