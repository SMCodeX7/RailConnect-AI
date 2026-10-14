# Project progress

## Current checkpoint

- Updated: 2026-10-15.
- Release target: v1.0 portfolio pilot, in progress.
- Branch: feat/incident-reporting.
- Foundation, journey search/details and staff identity merged into main.
- Incident-reporting planning documents reconciled with completed features.
- Stage 1: incident database models and protections completed.
- Stage 2: passenger submission API and durable rate limiting completed.
- Complete backend suite: 431 passed without skips.
- Stage 1-2 checkpoint ready to commit.
- Staff review, incident lifecycle, public responses and frontend remain.
- GitHub CI for this branch checkpoint has not yet been verified.

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

## Completed incident-reporting stages

### Stage 1: database models and protections

- Added separate passenger-report and verified-incident database records.
- Added storage for approved incident revisions and actor-attributed audit events.
- Added constraints for review state, resolution state, scope and impact values.
- Added run/segment foreign keys and unique incident revision numbers.
- Added database triggers rejecting revision/audit updates, deletes and truncation.
- Verified immutable-history protections and transaction rollback.
- Updated ADR 0003 and reconciled the roadmap.

### Stage 2: passenger submission

- Added submission schemas rejecting server-owned review and approval fields.
- Added scope-hint validation against prepared runs, stops and active stations.
- Allowed reporting of cancelled and restricted runs.
- Added POST /api/v1/reports with server-forced pending state.
- Added receipt responses excluding narratives and private review fields.
- Required timezone-aware observation times and rejected future observations.
- Added server-derived staff attribution for authenticated submissions.
- Required CSRF protection when a staff session cookie is present.
- Rejected invalid staff cookies rather than falling back to anonymous access.
- Added origin and JSON content-type checks.
- Added separate atomic PostgreSQL report-submission counters.
- Preserved counters independently of report transaction failures.
- Verified concurrent report-limit admission.
- Added report-counter cleanup preview and bounded transactional deletion.
- Fixed identity and report cleanup to delete only selected, locked keys.
- Strengthened report cleanup tests to verify actual deletion counts.
- Added 121 incident/report tests, bringing the backend suite to 431.

Protected review, amendment, resolution and their audit-producing workflows
remain unimplemented. Their database storage is ready.

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
- Migration 5c23c99becea creates incident_reports, incidents,
  incident_revisions and incident_audit_events.
- Migration 5c23c99becea also protects revision and audit history
  against updates, deletes and truncation.
- Migration af88e86de607 creates report_rate_limits.
- Current migration head: af88e86de607.
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
- Administrator permissions are explicitly mapped.
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

## Passenger reporting configuration

- Default report limit is five attempts per client within one hour.
- Report counters are separate from staff-login counters.
- Counter keys store a hash rather than the raw client identifier.
- Attempts reaching the service consume the report counter.
- Malformed bodies are rejected before the submission service.
- A failed report transaction does not reset its committed attempt counter.
- Rate rejection returns 429 with Retry-After.
- New reports have pending status and version 1.
- Submission receipts do not establish verification.
- Default report-counter retention is one day after window expiry.
- Default report-counter cleanup batch limit is 500.
- Cleanup preserves reports, login counters and current report-limit windows.

## Current local validation

- Backend Ruff lint passed across source, tests, migrations and scripts.
- Backend formatting check passed; 146 files checked at this checkpoint.
- mypy passed for 95 source files.
- Complete backend suite: 431 passed, with no skipped tests.
- Incident database and scope tests: 36 passed.
- Submission schema tests: 28 passed.
- Report-limit tests: 13 passed.
- Submission-service tests: 11 passed.
- Report API tests: 17 passed.
- Concurrent report-limit test: 1 passed.
- Report cleanup tests: 15 passed.
- Combined identity/report cleanup tests: 29 passed.
- Current migration head: af88e86de607.
- Alembic reports no new upgrade operations.
- Report cleanup preview completed without deletion.
- Git whitespace check passed.
- Previous frontend checkpoint: 62 tests, lint and build passed.
- No frontend changes are included in the current incident-reporting slice.
- Latest incident-reporting GitHub CI remains pending.

Focused test counts are subsets of the complete suite.
The combined cleanup count is not an additional set of tests.

## Earlier validation

These are historical checkpoints, not clean-checkout verification of
every change on the current branch:

- Completed staff-identity backend suite: 310 passed.
- Completed staff-identity frontend suite: 62 passed.
- Nine manual staff login/session/logout checks passed.
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
- Passenger submission is implemented at API level; its frontend remains pending.
- Protected staff review, incident amendment and resolution remain pending.
- Transactional review/lifecycle audit writes remain pending.
- Public incident responses remain pending.
- Incident records do not yet affect journey results.
- Anonymous reports do not establish submitter identity.
- Self-review prevention currently applies to recorded staff submitters.
- Identity and report-counter cleanup scheduling remain deployment responsibilities.
- Deployment must configure HTTPS, origins and trusted proxies correctly.
- Latest branch changes still require GitHub CI before merge.

## Incident-reporting branch stages

1. Database models, migrations and validation: completed.
2. Passenger submission API, rate limiting and cleanup: completed.
3. Protected staff queue and verify/reject workflow: pending.
4. Revisions, resolution and transactional audit history: pending.
5. Approved public incident responses: pending.
6. Passenger and staff frontend workflows: pending.
7. Final integration, documentation, CI and merge: pending.

Estimated branch completion is approximately 40%.
This is an effort estimate, not a count of checked items.
It does not represent completion of the entire v1 release.

## Remaining v1 work

- Protected report queue and verify/reject decisions.
- Versioned incident amendments, resolution and transactional audit writes.
- Approved public incident responses.
- Passenger reporting and staff incident-management interfaces.
- Authenticated timetable import access and actor attribution.
- Protected timetable management interface.
- Disruption effects and feasible alternatives.
- Policy retrieval and ownership-protected passenger assistant.
- Assistant evaluation and browser workflow tests.
- Repeatable synthetic scenarios and release demonstration.
- Final responsive and accessibility review.
- Deployment, persistence and recovery verification.
- Cleanup operational procedures or scheduling.
- Portfolio documentation, demonstration video and release tag.

Check remaining handbook requirements, including station aliases,
repository templates, license and OpenAPI compatibility verification,
before declaring v1 complete.

## Next task

Commit the validated incident database and passenger submission checkpoint.

Continue on feat/incident-reporting with stage 3:
protected staff report queue and verify/reject decisions.

Implement expected-version conflict handling and atomic report decisions,
initial incident revisions and audit writes.

Commit each subsequent validated stage separately.
Push and review the completed branch before merging after CI passes.
