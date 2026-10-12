# Project progress

## Current checkpoint

- Updated: 2026-10-12.
- Release target: v1.0 portfolio pilot, in progress.
- Branch: feat/journey-details.
- Foundation and initial journey search merged into main.
- Dated-run and journey detail/deadline slices completed.
- Provenance and import tracking validated locally; commit pending.
- Latest GitHub CI remains to be checked.
- Handbook alignment documents remain committed separately on
  feat/incident-reporting.

## Completed

- Created and cloned the GitHub repository.
- Recorded the modular-monolith architecture decision.
- Configured ignore rules, backend packaging and dependency lockfiles.
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
- Added inclusive arrival-deadline filtering with explicit arrival dates.
- Added the frontend detail panel and optional deadline controls.
- Added detail loading, retry, cancellation and focus restoration.
- Added timetable source records and persistent import summaries.
- Added read-only import preview.
- Added atomic source registration, timetable seeding and summary creation.
- Rejected changed content or metadata under an existing source reference.
- Verified repeated imports preserve the original successful summary.
- Added provenance to journey search and detail responses.
- Added the source card and explicit missing-provenance wording.
- Distinguished registration/retrieval times from live railway updates.
- Added import and provenance regression tests.
- Added timetable preview to CI.
- Standardized processed JSON line endings through .gitattributes.
- Documented the dataset in docs/data-card.md.
- Recorded dated-run, time-unit and provenance decisions in ADR 0004.
- Updated setup instructions, including Linux/macOS differences.

## Database and demonstration data

- PostgreSQL 17 runs locally through Docker Compose.
- Database access uses SQLAlchemy and psycopg.
- Migration d27ced7dc3b1 creates stations.
- Migration cbaf28463dbe creates train_services and service_stops.
- Migration 8b4605b4bc60 creates service_runs and run_stops
  and adds recurring-stop permissions.
- Migration b9c0a25509af creates source_records and timetable_imports.
- Current migration head: b9c0a25509af.
- Alembic reports no new upgrade operations.
- Seeded 30 selected demonstration stations.
- Station codes beginning with DEMO_ are project identifiers.
- Timetable data contains 12 fictional service patterns and 42 ordered stops.
- Examples include daily, weekday, weekend, reverse and overnight services.
- Timetable validity: 2026-01-01 through 2028-12-31, inclusive.
- Prepared 70 dated runs for 2026-10-12 through 2026-10-18.
- Repeated materialization inserted 0 runs and verified 70 existing runs.
- Fourteen service dates were skipped according to operating rules.
- Search reads prepared runs and does not create them.
- Scheduled run timestamps are stored in UTC and displayed in Asia/Colombo.
- Timetable source reference: demo-timetable-v1.
- Source metadata is stored in demo_timetable.source.json.
- Source registration records the exact timetable file SHA-256.
- Registered the existing timetable without reinserting its services.
- Repeated imports returned the same source and import-summary IDs.
- Preview reports no conflicts for the current demonstration dataset.
- Demonstration data is not an official timetable or live service feed.

## Current local validation

- Backend lint: passed across source, tests, migrations and scripts.
- Backend formatting: passed across the checked files.
- mypy: passed for 51 source files.
- Full backend suite: 184 passed.
- Alembic migration upgrade and schema check: passed.
- Station and timetable seed repeatability: passed.
- Dated-run materialization repeatability: passed.
- Source registration and import-summary repeatability: passed.
- Import tests cover read-only preview, conflicts and transaction rollback.
- Provenance API tests cover registered sources and null source metadata.
- Frontend ESLint and production build: passed.
- Frontend tests: 33 passed.
- Manually verified ordered stops and selected passenger segments.
- Manually verified inclusive arrival deadlines and overnight arrival dates.
- Manually verified clearing outdated results after input changes.
- Manually verified the registered source card and freshness explanation.
- Latest GitHub CI remains to be checked after the final provenance commit.

## Earlier validation

These checks were performed before the latest journey-details branch changes:

- GitHub Actions backend and frontend checks passed for prior commits.
- Foundation clean-checkout verification passed on Windows.
- Locked backend and frontend installation passed on the verification clone.
- Fresh PostgreSQL migration and repeatable station seeding passed.
- Foundation verification ran 41 backend and 5 frontend tests.
- The verification checkout remained clean.

The earlier clean-checkout results do not establish verification of every
change on the current branch.

## Current limitations and deferred integration

- Timetable schedules and operating patterns are fictional.
- Search coverage depends on explicitly prepared dated runs.
- Minute-resolution recurring offsets are retained and documented.
- Existing service definitions are verified rather than overwritten.
- Source references are resolved by source_ref, not a database foreign key.
- Source immutability is enforced by the import workflow, not a universal
  database prohibition on updates.
- Registration time does not establish operational freshness.
- Restricted runs expose their status; detailed impact eligibility rules
  remain part of the disruption workflow.
- The demonstration import command supports development and test environments.
- Execution context identifies the command environment, not a staff actor.
- Protected staff import access and attribution require the identity workflow.
- Handbook alignment documents must be reconciled from feat/incident-reporting.

## Remaining v1 work

- Staff accounts, expiring/revocable sessions and server-side permissions.
- Protected staff navigation and management workflows.
- Authenticated timetable import access and actor attribution.
- Separate passenger reports and verified incidents.
- Versioned review, resolution and transactional audit history.
- Disruption effects and feasible alternatives.
- Policy retrieval and ownership-protected passenger assistant.
- Assistant evaluation and browser workflow tests.
- Final responsive/accessibility review.
- Deployment, persistence and recovery verification.
- Portfolio documentation, demonstration video and release tag.

Check remaining handbook requirements, including station alias handling,
repository templates, license and OpenAPI compatibility verification,
before declaring v1 complete.

## Next task

Commit and push the validated provenance/import slice.
Check GitHub CI for the exact branch commit and review the pull request.
Merge journey details into main after checks pass.

Then implement staff identity, sessions and permissions before returning
to protected incident review.
