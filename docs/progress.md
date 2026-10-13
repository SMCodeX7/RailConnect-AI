# Project progress

## Current checkpoint

- Updated: 2026-10-13.
- Release target: v1.0 portfolio pilot, in progress.
- Branch: feat/staff-identity.
- Foundation, initial journey search and journey-details work merged into main.
- Backend staff authentication validated locally; commit pending.
- Staff frontend, expired-record cleanup and concurrency checks remain.
- Latest staff-identity GitHub CI remains to be checked.
- Handbook alignment documents remain on feat/incident-reporting.

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
- Recorded the staff identity and session design in ADR 0005.
- Added individual users, roles and role assignments.
- Added Argon2id password hashing and verification.
- Added interactive staff provisioning without default credentials.
- Added hashed opaque session tokens and session-bound CSRF tokens.
- Added absolute and idle session expiry.
- Added session revocation and account-version invalidation.
- Added explicit permission mappings with default denial for unknown roles.
- Rechecked roles and permissions during session authentication.
- Added database-backed client and account login limits.
- Committed login attempt counters before credential rejection.
- Verified account state again before creating a login session.
- Added login, logout and current-session endpoints.
- Added host-only HTTP-only cookies and production security validation.
- Added origin checks and CSRF protection for authenticated mutations.
- Added generic authentication errors and non-cacheable auth responses.
- Added provisioning, session, login and authorization regression tests.
- Provisioned a local controller account interactively.

## Database and demonstration data

- PostgreSQL 17 runs locally through Docker Compose.
- Database access uses SQLAlchemy and psycopg.
- Migration d27ced7dc3b1 creates stations.
- Migration cbaf28463dbe creates train_services and service_stops.
- Migration 8b4605b4bc60 creates service_runs and run_stops
  and adds recurring-stop permissions.
- Migration b9c0a25509af creates source_records and timetable_imports.
- Migration dfeb4f1c64a4 creates users, roles, user_roles,
  sessions and login_rate_limits.
- Current migration head: dfeb4f1c64a4.
- Migration upgrade and Alembic schema checks passed.
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

## Staff identity configuration

- Password provisioning policy: 15–128 characters.
- Password whitespace is preserved.
- Initial roles: controller and administrator.
- Permissions are explicitly mapped; administrator has no blanket bypass.
- Session absolute lifetime defaults to eight hours.
- Session idle timeout defaults to thirty minutes.
- Login-rate window defaults to five minutes.
- Default limits: 30 attempts per client and 5 per account per window.
- Raw session tokens are stored only in the browser cookie.
- The database stores their SHA-256 hashes.
- CSRF tokens are separate from session authentication tokens.
- Local HTTP development explicitly disables Secure cookies.
- Production requires Secure cookies and configured HTTPS origins.
- A local controller account exists; its password is not recorded in Git.

## Current backend validation

- Ruff lint: passed across source, tests, migrations and scripts.
- Ruff formatting: 114 files already formatted.
- mypy: passed for 76 source files.
- Full backend suite: 294 passed.
- Configuration and password tests: 29 passed.
- Permission and provisioning tests: 16 passed.
- Session-service tests: 22 passed.
- Login-rate-limit tests: 13 passed.
- Login-service tests: 12 passed.
- Authentication API tests: 22 passed.
- Tests verify failed logins preserve their rate counters.
- Tests verify changed account credentials/state prevent stale login.
- Tests verify logout revocation and rejection of replayed cookies.
- Tests verify origin checks, CSRF failures and permission denial.
- Tests verify idle and absolute expiry boundaries.
- Latest staff-identity GitHub CI: pending.

## Completed journey validation

These results belong to the completed journey-details work:

- Backend suite at that checkpoint: 184 passed.
- Frontend ESLint and production build: passed.
- Frontend tests: 33 passed.
- Timetable and run materialization repeatability: passed.
- Source registration and import-summary repeatability: passed.
- Manually verified ordered stops and selected passenger segments.
- Manually verified inclusive deadlines and overnight arrival dates.
- Manually verified clearing outdated results after input changes.
- Manually verified the source card and freshness explanation.

The staff frontend has not yet been implemented or validated.

## Earlier clean-checkout validation

These are historical checks and do not verify the current identity branch:

- Foundation clean-checkout verification passed on Windows.
- Locked backend and frontend installation passed on the verification clone.
- Fresh PostgreSQL migration and repeatable station seeding passed.
- Foundation verification ran 41 backend and 5 frontend tests.
- The verification checkout remained clean.

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
- Import execution context identifies the command environment, not a staff actor.
- Protected staff import access and attribution are not yet implemented.
- Expired session and rate-limit cleanup is not yet implemented.
- Concurrent login-rate enforcement still requires dedicated verification.
- Browser login, session restoration and permission-aware navigation are pending.
- Deployment must configure trusted proxies correctly.
- Staff provisioning is a trusted interactive CLI, not a public registration API.
- Handbook alignment documents must be reconciled from feat/incident-reporting.

## Remaining v1 work

- Expired identity-record cleanup and concurrent login-limit verification.
- Staff login/session frontend and interaction tests.
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

Commit and push the validated backend staff-authentication checkpoint.

Add expired identity-record cleanup and concurrent login-limit tests.
Then implement and test the staff login/session frontend.

Keep feat/staff-identity open until its remaining work and CI checks pass.
