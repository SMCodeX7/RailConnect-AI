# ADR 0004: Dated runs and timetable provenance

## Status

Accepted

## Context

The handbook distinguishes recurring service patterns, dated service runs
and passenger journey segments.

The initial search calculated dates directly from recurring stops.
It did not provide persisted run identity or an ordered-stop detail view.

The timetable also needs identifiable source versions and import history.

## Decision

Keep train_services as the existing recurring-pattern table.

Persist service_runs with a unique service/date pair, operational status
and version.

Persist scheduled run_stops with station identity, stop sequence,
timezone-aware timestamps and boarding/alighting permissions.

Use explicit run materialization rather than database writes during
public journey searches.

Preserve service_date as the run's starting date.
travel_date identifies the passenger's boarding date in Asia/Colombo.

Return run IDs and selected departure/arrival stop sequences.

## Time units

Retain integer minute offsets in recurring stops for the current
minute-resolution demonstration dataset.

This differs from the handbook's suggested second offsets.

Materialize absolute scheduled timestamps and store them in UTC.
Do not infer additional timing precision.

Supporting second-resolution source data requires an explicit schema
and import-contract migration rather than silent rounding.

## Query contract

Retain the existing departure_station_id, arrival_station_id and
travel_date parameter names.

arrive_before is a local Asia/Colombo time without a timezone suffix.
Without arrival_date, its deadline applies on travel_date.

arrival_date requires arrive_before and cannot precede travel_date.
The deadline is inclusive.

Journey details use a run ID and optional paired stop-sequence parameters.

## Provenance

source_ref identifies a registered immutable source version.

Source records store metadata, effective dates and the exact dataset hash.
The current service/run reference is resolved by source_ref; it is not yet
a database foreign key to source_records.

Historical unregistered references return source: null.
The UI explicitly explains missing provenance.

The demonstration label does not establish real-world freshness.
Registration and retrieval timestamps have separate meanings.

## Imports

Preview performs no database writes.

Import registration, timetable writes and the successful summary share
a caller-owned transaction.

Repeated imports preserve the original successful summary.

Cooperating imports of the same source reference use a PostgreSQL
transaction advisory lock. Constraints remain the final safeguard.

Existing service definitions are verified rather than overwritten.
Source-version replacement is a separate future workflow.

## Consequences

Prepared date coverage must be documented and maintained.

Adding dated runs preserves stable identities for incidents and later
inventory, while scheduled times remain separate from future estimates.

Staff import authorization and actor attribution remain prerequisites
for exposing a protected management import API.
