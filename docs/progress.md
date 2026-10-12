# Project progress

## Current checkpoint

- Updated: 2026-10-12
- Release target: v1.0 portfolio pilot, in progress.
- Branch: feat/journey-details.
- Foundation and initial journey search merged into main.
- Dated-run implementation completed.
- Journey details and arrival-deadline workflow validated locally; commit pending.
- Handbook alignment documents committed separately on feat/incident-reporting.

## Completed

- Created and cloned the GitHub repository.
- Recorded the modular-monolith architecture decision.
- Configured ignore rules, backend packaging and development dependencies.
- Installed the backend package in an isolated Python environment.
- Added validated settings and environment examples.
- Added an app factory, liveness and database readiness endpoints.
- Added server-generated request IDs and consistent error responses.
- Added structured request logging.
- Added application-managed database sessions and shutdown cleanup.
- Added station listing/search with validation and pagination.
- Set up React, TypeScript, Vite and ESLint.
- Connected station selectors through the development proxy.
- Added loading, empty, error and retry states.
- Prevented duplicate departure and arrival selections.
- Configured Vitest and React Testing Library.
- Added direct journey search and its frontend.
- Added travel-date selection, results and pagination.
- Cancelled outdated requests and cleared results after input changes.
- Added validated, repeatable demonstration timetable seeding.
- Added persisted dated service runs and scheduled run stops.
- Added boarding and alighting permissions with validated demo defaults.
- Added repeatable run materialization with UTC timestamps.
- Connected search to dated runs and ordered segment references.
- Excluded cancelled runs and disallowed boarding/alighting.
- Returned explicit run status and version.
- Added database constraints and materialization regression tests.
- Added repeated demonstration run materialization to CI.
- Added journey details with ordered stops and selected passenger segments.
- Added inclusive arrival-deadline filtering with explicit overnight arrival dates.
- Added the frontend detail panel and optional deadline controls.
- Added detail loading, retry, cancellation and focus restoration.

## Database and demonstration data

- PostgreSQL 17 runs locally through Docker Compose.
- Database access uses SQLAlchemy and psycopg.
- Migration d27ced7dc3b1 creates stations.
- Migration cbaf28463dbe creates train_services and service_stops.
- Migration 8b4605b4bc60 creates service_runs and run_stops
  and adds recurring-stop permissions.
- Alembic reports no new upgrade operations.
- Seeded 30 selected demonstration stations.
- Station codes beginning with DEMO_ are project identifiers.
- Timetable data contains 12 fictional services and 42 ordered stops.
- Examples include daily, weekday, weekend, reverse and overnight services.
- Timetable seeding verifies existing records and rejects conflicting data.
- Prepared 70 dated runs for 2026-10-12 through 2026-10-18.
- Repeated materialization inserted 0 runs and verified 70 existing runs.
- Fourteen service dates were skipped according to operating rules.
- Search reads prepared runs and does not create them.
- Scheduled run timestamps are stored in UTC and displayed in Asia/Colombo.
- Demonstration data is not an official timetable or live service feed.

## Current local validation

- Backend source lint and formatting: passed after detail/deadline changes.
- mypy: passed for 43 source files.
- Full backend suite: 167 passed, with no skipped tests.
- Detail, journey API and journey service tests: 72 passed.
- Migration upgrade and schema check: passed.
- Timetable seed repeatability: passed.
- Dated-run materialization repeatability: passed.
- Frontend ESLint and production build: passed.
- Frontend tests: 30 passed.
- Manually verified ordered stops, selected segments, inclusive deadlines,
  overnight arrival dates and clearing outdated results.
- GitHub CI for the latest changes remains to be checked.

## Earlier validation

These results precede the current dated-run changes:

- Frontend ESLint and production build: passed.
- Frontend interaction and API tests: 18 passed.
- Manually verified direct journeys, overnight arrivals, empty results
  and clearing results after input changes.
- GitHub Actions backend and frontend checks passed for prior commits.
- Foundation clean-checkout verification passed on Windows.
- Fresh PostgreSQL migration and station seeding passed.
- Foundation verification ran 41 backend and 5 frontend tests.
- The verification checkout remained clean.

## Remaining v1 work

- Source records, dataset card and import traceability.
- Staff accounts, sessions and server-side permissions.
- Separate passenger reports and verified incidents.
- Versioned review, resolution and transactional audit history.
- Disruption effects and feasible alternatives.
- Policy retrieval and ownership-protected passenger assistant.
- Assistant evaluation and browser workflow tests.
- Final responsive/accessibility review.
- Deployment, persistence and recovery verification.
- Portfolio documentation, demonstration video and release tag.

Foundation release requirements will also be checked against the
handbook for remaining documentation and repository housekeeping.

## Next task

Commit the validated journey detail and arrival-deadline slice.
Then implement source provenance, dataset documentation and import
traceability on feat/journey-details.
