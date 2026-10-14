# Project progress

## Current checkpoint

- Updated: 2026-10-14.
- Release target: v1.0 portfolio pilot, in progress.
- Branch: feat/staff-identity.
- Foundation, initial journey search and journey-details work merged into main.
- Backend staff authentication checkpoint committed.
- Identity cleanup, concurrency verification and staff frontend completed locally.
- Latest changes are ready for commit after documentation review.
- Latest staff-identity GitHub CI and merge remain pending.
- Handbook alignment documents remain on feat/incident-reporting.

## Completed foundation

- Created and cloned the GitHub repository.
- Recorded the modular-monolith architecture decision.
- Configured ignore rules, backend packaging and dependency lockfiles.
- Added validated settings and environment examples.
- Added the app factory, liveness and database readiness endpoints.
- Added server-generated request IDs and consistent error responses.
- Added structured request logging.
- Added application-managed database sessions and shutdown cleanup.
- Added station listing/search with validation and pagination.
- Set up React, TypeScript, Vite and ESLint.
- Configured Vitest and React Testing Library.
- Connected station selectors through the development proxy.
- Added loading, empty, error and retry states.
- Prevented duplicate departure and arrival selections.

## Completed journeys and timetable provenance

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
- Added detail loading, retry, cancellation and focus restoration.
- Added timetable source records and persistent import summaries.
- Added read-only import preview.
- Added atomic source registration, seeding and summary creation.
- Rejected changed content or metadata under an existing source reference.
- Verified repeated imports preserve the original successful summary.
- Added provenance to search and detail responses.
- Added source cards and explicit missing-provenance wording.
- Distinguished registration/retrieval times from live railway updates.
- Added import and provenance regression tests.
- Added timetable preview to CI.
- Standardized processed JSON line endings through .gitattributes.
- Documented the dataset in docs/data-card.md.
- Recorded dated-run and provenance decisions in ADR 0004.
- Documented Windows, Linux and macOS setup differences.

## Completed staff identity

- Recorded identity and session decisions in ADR 0005.
- Added individual users, roles and role assignments.
- Added Argon2id password hashing and verification.
- Added interactive staff provisioning without default credentials.
- Added hashed opaque session tokens and separate CSRF tokens.
- Added absolute and idle session expiry.
- Added session revocation and account-version invalidation.
- Added explicit permission mappings and denial for unknown roles.
- Rechecked roles and permissions during session authentication.
- Added database-backed client and account login limits.
- Committed login attempt counters before credential rejection.
- Rechecked account state before creating a login session.
- Added login, logout and current-session endpoints.
- Added host-only HTTP-only cookies and production security validation.
- Added origin checks and CSRF protection for authenticated mutations.
- Added generic authentication errors.
- Added non-cacheable session responses and frontend API requests.
- Added provisioning, session, login and authorization regression tests.
- Added read-only cleanup preview and explicit transactional deletion.
- Added retention periods and bounded cleanup batches.
- Added cleanup preservation and rollback tests.
- Verified concurrent client and account login limits.
- Added the staff-access section and public journey navigation.
- Added session restoration, login, logout and explicit refresh.
- Displayed roles, permissions and absolute expiry.
- Cleared password input after submission.
- Added visible expiry and unconfirmed-logout handling.
- Added cancellation when the staff panel unmounts.
- Added shared HTTP, authentication API, staff-panel and navigation tests.
- Provisioned local controller accounts interactively.
- Verified the staff workflow against the running backend.

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
- Alembic reports no new upgrade operations.
- Seeded 30 selected demonstration stations.
- Station codes beginning with DEMO_ are project identifiers.
- Timetable data contains 12 fictional patterns and 42 ordered stops.
- Examples include daily, weekday, weekend, reverse and overnight services.
- Timetable validity: 2026-01-01 through 2028-12-31, inclusive.
- Prepared 70 dated runs for 2026-10-12 through 2026-10-18.
- Repeated materialization verified 70 existing runs and inserted none.
- Fourteen service dates were skipped according to operating rules.
- Search reads prepared runs and does not create them.
- Run timestamps are stored in UTC and displayed in Asia/Colombo.
- Timetable source reference: demo-timetable-v1.
- Metadata is stored in demo_timetable.source.json.
- Source registration records the exact timetable file SHA-256.
- Repeated imports preserve source and import-summary identities.
- Demonstration data is not an official timetable or live service feed.

## Staff identity configuration

- Provisioned passwords contain 15 to 128 characters.
- Password whitespace is preserved.
- Initial roles are controller and administrator.
- Administrator has explicitly mapped permissions, not a blanket bypass.
- Session absolute lifetime defaults to eight hours.
- Session idle timeout defaults to thirty minutes.
- Login-rate window defaults to five minutes.
- Default limits are 30 attempts per client and 5 per account per window.
- The browser receives an HTTP-only session cookie.
- The database stores the session token's SHA-256 hash.
- CSRF tokens are separate from authentication tokens.
- Session and CSRF state are not persisted in browser localStorage.
- Local HTTP development explicitly disables Secure cookies.
- Production requires Secure cookies and configured HTTPS origins.
- Default cleanup retention is seven days for expired/revoked sessions
  and one day for expired login-rate windows.
- Default cleanup batch size is 500 records per table.
- Cleanup requires explicit application and is not automatically scheduled.
- Local account passwords are not recorded in Git.

## Current local validation

- Ruff lint passed across source, tests, migrations and scripts.
- Ruff formatting: 119 files already formatted.
- mypy passed for 78 source files.
- Complete backend suite: 310 passed, with no skipped tests.
- Identity cleanup tests: 14 passed.
- Concurrent login-limit tests: 2 passed.
- Current migration head and schema checks passed.
- Frontend ESLint passed.
- Frontend TypeScript checking and production build passed.
- Complete frontend suite: 62 passed across 9 files.
- Staff-panel tests: 12 passed.
- Shared HTTP tests: 11 passed.
- Staff API contract tests: 3 passed.
- Application navigation tests: 3 passed.
- Existing journey frontend tests: 33 passed.
- Manually verified public journey access without staff login.
- Manually verified generic credential errors and cleared password input.
- Manually verified successful login and controller permissions.
- Manually verified session restoration after browser refresh.
- Manually verified explicit session refresh.
- Manually verified switching between journey and staff sections.
- Manually verified logout and remaining signed out after refresh.
- Latest GitHub CI remains pending.

## Earlier validation

These are historical checkpoints, not clean-checkout verification of
every change on the current branch:

- Journey-details backend suite: 184 passed.
- Journey frontend suite: 33 passed.
- Timetable, source registration and run materialization were repeatable.
- Manually verified ordered stops, selected segments and source cards.
- Manually verified inclusive deadlines and overnight arrival dates.
- Foundation clean-checkout verification passed on Windows.
- Locked backend and frontend installation passed on that clone.
- Fresh PostgreSQL migration and repeatable station seeding passed.
- Foundation verification ran 41 backend and 5 frontend tests.
- The verification checkout remained clean.

## Current limitations and deferred integration

- Timetable schedules and operating patterns are fictional.
- Search coverage depends on explicitly prepared dated runs.
- Minute-resolution recurring offsets are retained and documented.
- Existing service definitions are verified rather than overwritten.
- Sources are resolved by source_ref rather than a database foreign key.
- Source immutability is enforced by the import workflow.
- Registration time does not establish operational freshness.
- Restricted-run impact eligibility belongs to the disruption workflow.
- Demonstration imports require development or test environments.
- Import execution context currently identifies the command environment,
  not an authenticated staff actor.
- Protected staff import access and actor attribution remain pending.
- Displayed permissions do not implement incident or import workflows.
- Staff provisioning is an interactive CLI, not public registration.
- Self-service password recovery and account management are not implemented.
- Identity cleanup scheduling remains a deployment responsibility.
- Deployment must configure HTTPS, origins and trusted proxies correctly.
- Handbook alignment documents must be reconciled from feat/incident-reporting.
- Latest branch changes still require GitHub CI before merge.

## Remaining v1 work

- Protected staff management workflows.
- Authenticated timetable import access and actor attribution.
- Separate passenger reports and verified incidents.
- Versioned review, resolution and transactional audit history.
- Disruption effects and feasible alternatives.
- Policy retrieval and ownership-protected passenger assistant.
- Assistant evaluation and browser workflow tests.
- Final responsive and accessibility review.
- Deployment, persistence and recovery verification.
- Portfolio documentation, demonstration video and release tag.

Check remaining handbook requirements, including station aliases,
repository templates, license and OpenAPI compatibility verification,
before declaring v1 complete.

## Next task

Commit and push the completed identity cleanup and staff frontend.

Verify GitHub CI and review the staff-identity pull request before merging.
Then reconcile the incident-reporting planning documents and implement
the next feature according to the handbook.
