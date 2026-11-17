# RailConnect AI v1.0.0 draft release notes

## Pilot features

- Search prepared direct journeys and view scheduled stops, boarding and
  alighting permissions, and timetable provenance.
- See approved disruption effects, estimated arrivals when available, and
  feasible direct alternatives.
- Ask the passenger assistant about the guide, demonstration journeys, or
  verified incidents and inspect its citations.
- Submit a disruption report and receive a pending review receipt.
- Review reports and manage verified incidents through staff access.
  Authorized staff can also import demonstration timetables and inspect
  audit history.

## Local validation

The release branch passed 653 backend tests, 135 frontend tests, and four
Playwright browser tests on 17 November 2026. Frontend lint and the
production build passed. Alembic detected no new upgrade operations.

The independent assistant evaluation passed 51 of 60 cases. It correctly
declined all 20 unsupported questions and returned a fallback for nine
supported questions. See the [evaluation results](../evaluation/assistant/README.md).

## Pilot scope

The pilot uses fictional schedules and synthetic incidents for selected
Sri Lankan stations. Live railway updates, fares, bookings, and seat
availability are unavailable. Journey searches require prepared dated runs.

## Release status

Release verification is in progress. See [project progress](progress.md)
for the remaining checks and the [setup guide](setup.md) to run the pilot
locally.
