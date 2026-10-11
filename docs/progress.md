# Project progress

## Current checkpoint

- Updated: 2026-10-11
- Phase: journey search, in progress
- Branch: feat/journey-search
- Foundation completed and merged into main.
- Timetable models, migration, validation, and repeatable seeding validated.

## Completed

- Created and cloned the GitHub repository.
- Recorded the modular-monolith architecture decision.
- Extended ignore rules.
- Configured the backend package and development dependencies.
- Installed the package in an isolated Python environment.
- Added an app factory and separate health router.
- Verified liveness and interactive API documentation.
- Added validated application settings and environment examples.
- Corrected import classification and test-client dependencies.
- Added server-generated request IDs and response-header tests.
- Added consistent HTTP, validation, and unexpected-error responses.
- Added application-managed database sessions and shutdown cleanup.
- Added the versioned station listing and search API.
- Added station API response, query-validation, and missing-database tests.
- Added a database readiness endpoint.
- Added readiness failure-response tests.
- Added PostgreSQL repository tests for active stations, search, pagination, and literal wildcard handling.
- Set up React, TypeScript, Vite, and ESLint.
- Connected the frontend to the station API through a development proxy.
- Separated API requests, station types, loading state, and UI components.
- Added departure and arrival selectors with loading, error, and retry states.
- Prevented selecting the same departure and arrival station.
- Configured Vitest and React Testing Library.
- Added five frontend interaction tests.
- Added structured JSON request logs with request IDs, status codes, and duration.
- Added logging tests for response correlation, failures, omitted request values, and handler reuse.

## Database and station data

- PostgreSQL 17 runs locally through Docker Compose.
- Database connections use SQLAlchemy and psycopg.
- Verified the application's database connection.
- Alembic migration d27ced7dc3b1 creates the stations table.
- Alembic reports no pending schema changes.
- Seeded 30 selected Sri Lankan demonstration stations, including northern and eastern stations.
- Station codes beginning with DEMO_ are project identifiers.
- Repeated seeding inserts no duplicates: 0 inserted, 30 already present.

## Timetable data

- Migration cbaf28463dbe adds train_services and service_stops.
- Validated 12 fictional services with 42 ordered stops.
- Included northern, eastern, central, southern, and hill-country examples.
- Supported daily, weekday, weekend, reverse, and overnight schedules.
- Added timetable validation and PostgreSQL seeding tests.
- Verified repeatability and rollback on conflicting data.

## Validation

- pip check: passed.
- Ruff lint and formatting: passed for the checked files.
- mypy: passed for 24 source files.
- pytest: 62 passed, with no skipped database tests.
- Manually verified station searches and pagination against PostgreSQL.
- Database connection check: passed.
- Alembic migration and schema check: passed.
- Station seed repeatability check: passed.
- Frontend ESLint: passed.
- Frontend TypeScript checking and production build: passed.
- Manually verified station loading and selected-journey display.
- Frontend interaction tests: 5 passed.
- GitHub Actions: backend and frontend checks passed.
- Fresh Windows clone: locked backend and frontend installations passed.
- Fresh PostgreSQL database: migration and repeatable station seeding passed.
- Fresh clone tests: 41 backend and 5 frontend tests passed.
- Fresh clone working tree remained clean.

## Remaining foundation work

- None.

## Next task

Implement and test the direct journey search API.
