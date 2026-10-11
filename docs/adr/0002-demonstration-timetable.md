# ADR 0002: Demonstration timetable and direct journey search

## Status

Accepted.

## Context

The pilot needs searchable train journeys using clearly labelled
demonstration schedules. Existing stations provide stable identifiers.

The design must support intermediate stops, operating days, validity
dates, and overnight journeys.

## Decision

Create a timetable module with two tables:

- train_services: service identity, name, operating weekdays, validity
  dates, active status, and source reference.
- service_stops: service reference, station reference, stop sequence,
  and arrival and departure offsets.

Store offsets as minutes from midnight on the service's starting date.
Values above 1440 represent times on subsequent days.

Use Asia/Colombo when converting schedules into journey timestamps.

A service's operating weekdays and validity dates apply to its starting
date. The user's travel date refers to boarding at the departure station.
Search must account for services that started on a preceding date.

Return a direct journey only when:

- The service and both selected stations are active.
- The service operates on the relevant starting date.
- The departure stop occurs before the arrival stop.
- Boarding and arrival times are available.
- Arrival occurs after departure.

Return results ordered by departure time, arrival time, and service code.

Reject identical departure and arrival stations.
Distinguish invalid station selections from a valid search with no results.

## Data integrity

Use foreign keys for services and stations.
Require unique service codes and unique stop sequences within a service.
Validate chronological stop times and operating dates before seeding.
Seed complete services transactionally and without duplicate records.

## Scope

The pilot supports direct journeys without changing trains.
Schedules are fictional demonstration data and must be labelled in
the dataset, API responses, and frontend.

Transfers, live feeds, fares, seat availability, and booking are
outside this milestone.

## Code organization

Keep timetable models and seed validation in the timetable module.
Keep journey query schemas, repository queries, service logic, and
HTTP routes in the journeys module.

Keep frontend requests, types, hooks, forms, and result components
in separate files.
