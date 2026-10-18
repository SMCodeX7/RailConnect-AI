# Project progress

## Current checkpoint

- Updated: 2026-10-18.
- Release target: v1.0 portfolio pilot, in progress.
- Branch: feat/incident-reporting.
- Foundation, journey search/details and staff identity merged into main.
- Incident-reporting stages 1–3 completed and committed locally.
- Stage 3 commit: 71bc123, protected report review and atomic decisions.
- Stage 4 lifecycle and protected audit-history APIs validated locally.
- Complete backend suite: 566 passed without skips.
- Stage 4 documentation updated; checkpoint commit pending.
- Public incident responses, frontend and final branch integration remain.
- GitHub CI for the latest branch changes has not yet been verified.

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
- Documented dataset coverage and limitations in docs/data-card.md.
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
- Added approved incident revisions and actor-attributed audit storage.
- Added constraints for review state, resolution state, scope and impact.
- Added run/segment foreign keys and unique incident revision numbers.
- Added triggers rejecting revision/audit updates, deletes and truncation.
- Verified immutable-history protections and transaction rollback.
- Updated ADR 0003 and reconciled the roadmap.

### Stage 2: passenger submission

- Added schemas rejecting server-owned review and approval fields.
- Validated scope hints against prepared runs, stops and active stations.
- Allowed reporting of cancelled and restricted runs.
- Added POST /api/v1/reports with server-forced pending state.
- Added receipt responses excluding narrative and private review fields.
- Required aware observation times and rejected future observations.
- Added server-derived staff attribution for authenticated submissions.
- Required CSRF protection when a staff session cookie is present.
- Rejected invalid staff cookies rather than becoming anonymous.
- Added origin and JSON content-type checks.
- Added separate atomic PostgreSQL report-submission counters.
- Preserved counters independently of report transaction failures.
- Verified concurrent report-limit admission.
- Added counter cleanup preview and bounded transactional deletion.
- Fixed identity and report cleanup to delete selected, locked keys only.
- Strengthened cleanup tests to verify actual deletion counts.
- Complete backend checkpoint: 431 passed.

### Stage 3: protected staff review

- Added GET /api/v1/staff/reports for the pending queue.
- Added bounded pagination and ordering by submission time and report ID.
- Required reports.read in the HTTP dependency and queue service.
- Added explicit staff-only queue response fields.
- Added strict expected-version verify/reject schemas.
- Required approved scope, impact, effective interval and evidence basis.
- Added POST /api/v1/staff/reports/{report_id}/verify.
- Added POST /api/v1/staff/reports/{report_id}/reject.
- Required reports.review, allowed Origin and session-bound CSRF token.
- Rechecked current reviewer account and role permissions.
- Prevented identified staff self-review.
- Locked reports and refreshed their database state before decisions.
- Rejected stale versions and already-reviewed reports with conflicts.
- Validated approved run/segment references independently of hints.
- Verification atomically creates the decision, incident, revision and audit.
- Rejection atomically records the decision and audit without an incident.
- Recorded server-derived actors, timestamps and request IDs.
- Returned resulting versions and record references.
- Verified complete rollback when verification/rejection audit insertion fails.
- Verified disabled accounts and removed roles invalidate earlier snapshots.
- Verified simultaneous verification/rejection allows one decision and one conflict.
- Complete backend checkpoint: 512 passed.
- Committed locally as 71bc123.

### Stage 4: incident lifecycle and audit history

- Added strict amendment and resolution schemas.
- Added POST /api/v1/staff/incidents/{incident_id}/amend.
- Added POST /api/v1/staff/incidents/{incident_id}/resolve.
- Required incidents.edit for amendments.
- Required incidents.resolve for resolution.
- Required valid authentication, allowed Origin and session-bound CSRF tokens.
- Rechecked current staff account and role permissions in lifecycle transactions.
- Locked incidents and rejected stale versions or changes to resolved incidents.
- Amendments create a new approved revision and increment incident version.
- Preserved earlier revisions and the originating report's review version.
- Resolution records actor, reason, decision time and effective resolution time.
- Rejected future resolution times and times before the current revision starts.
- Added transactional lifecycle audit events referencing the applicable revision.
- Verified audit-insertion failures roll back amendments and resolution.
- Added GET /api/v1/staff/reports/{report_id}/audit.
- Required audit.read for audit-history access.
- Added explicit audit fields, bounded pagination and no-store responses.
- Included verification, rejection, amendment and resolution in report history.
- Verified unauthenticated and insufficient-permission audit access is denied.
- Verified removing the only staff role invalidates staff authentication.
- Verified invalid amendment scope preserves current revision and audit history.
- Verified amendment/amendment, amendment/resolution and resolution/resolution races.
- Each tested race permits one successful change and one version conflict.
- Complete backend checkpoint: 566 passed.
- Stage 4 checkpoint commit remains pending.

Public incident responses and passenger/staff reporting interfaces remain pending.

## Database and demonstration data

- PostgreSQL 17 runs locally through Docker Compose.
- Database access uses SQLAlchemy and psycopg.
- Migration d27ced7dc3b1 creates stations.
- Migration cbaf28463dbe creates train_services and service_stops.
- Migration 8b4605b4bc60 creates service_runs and run_stops
  and adds recurring-stop permissions.
- Migration b9c0a25509af creates source_records and timetable_imports.
- Migration dfeb4f1c64a4 creates identity, session and login-limit tables.
- Migration 5c23c99becea creates report, incident, revision and audit tables.
- Migration 5c23c99becea protects revision and audit history
  against updates, deletes and truncation.
- Migration af88e86de607 creates report_rate_limits.
- Current migration head: af88e86de607.
- Stages 3 and 4 required no additional migration.
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

## Configuration and operational behavior

### Staff identity

- Provisioned passwords contain 15 to 128 characters.
- Password whitespace is preserved.
- Initial roles are controller and administrator.
- Administrator permissions are explicitly mapped.
- Absolute session lifetime defaults to eight hours.
- Idle timeout defaults to thirty minutes.
- Login limits default to 30 attempts per client and 5 per account
  within a five-minute window.
- The browser receives an HTTP-only session cookie.
- The database stores the authentication token's SHA-256 hash.
- CSRF tokens are separate from authentication tokens.
- Session and CSRF state are not persisted in localStorage.
- Local HTTP development explicitly disables Secure cookies.
- Production requires Secure cookies and configured HTTPS origins.
- Cleanup defaults to seven-day session retention and one-day login-limit retention.
- Cleanup defaults to 500 records per table and requires explicit application.
- Local account passwords are not recorded in Git.

### Passenger reporting and review

- Report limits default to five attempts per client within one hour.
- Report counters are separate from staff-login counters.
- Counter keys store hashes rather than raw client identifiers.
- Attempts reaching the submission service consume the report counter.
- Malformed bodies are rejected before the submission service.
- Failed report creation does not reset its committed attempt counter.
- Rate rejection returns 429 with Retry-After.
- New reports have pending status and version 1.
- Receipts do not establish verification.
- Report-counter cleanup defaults to one-day retention and batch limit 500.
- Cleanup preserves reports, login counters and current report-limit windows.
- Queue pagination defaults to limit 20 and offset 0.
- Queue and audit limits are 1 through 100, with offsets up to 10000.
- Review reasons are required and limited to 2000 characters.
- Approved delay values are integer minutes between 1 and 1440.
- Cancellation requires whole-run scope.
- Effective intervals require aware timestamps and an end after the start.
- Report decisions increment report version.
- Initial verified incidents and revisions start at version/revision 1.
- Stale or already-reviewed report decisions return 409.

### Lifecycle and audit history

- Amendment and resolution require the expected incident version.
- Amendments increment incident version and current revision number.
- Resolution increments incident version and preserves the current revision.
- Only active incidents may be amended or resolved.
- No reopening workflow is implemented.
- Resolution effective time cannot be in the future or before the current
  revision's effective start.
- Lifecycle changes and their audit writes share one transaction.
- Audit history requires audit.read.
- Controllers lack audit.read by default; administrators have it.
- Audit responses contain private management history.
- Audit history does not replace the planned public incident response.

## Current local validation

- Backend Ruff lint passed across source, tests, migrations and scripts.
- Backend formatting passed: 164 files already formatted.
- mypy passed for 108 source files.
- Complete backend suite: 566 passed without skips.
- Incident database and scope tests: 36 passed.
- Submission schema tests: 28 passed.
- Report-limit tests: 13 passed.
- Submission-service tests: 11 passed.
- Report API tests: 17 passed.
- Concurrent report-limit test: 1 passed.
- Report cleanup tests: 15 passed.
- Pending-queue tests: 14 passed.
- Review-schema tests: 43 passed.
- Review, lifecycle and audit API/security tests: 58 passed.
- Lifecycle schema tests: 16 passed.
- Review and lifecycle concurrency tests: 4 passed.
- Combined lifecycle schemas, API/security and concurrency checks: 78 passed.
- Combined identity/report cleanup tests: 29 passed.
- Alembic reports no new upgrade operations.
- Git whitespace check passed before these documentation updates.
- Previous frontend checkpoint: 62 tests, lint and build passed.
- No incident frontend changes have been implemented yet.
- Latest incident-reporting GitHub CI remains pending.

Focused counts are subsets of the complete suite.
The combined counts are not additional tests.

Concurrency cases use independent connections and committed fixtures
in uniquely named temporary schemas created from model metadata.
Those schemas are removed afterward.

Migration-installed history triggers are verified separately by the
incident immutability tests.

## Earlier validation

These historical checks do not establish clean-checkout verification
of every change on the current branch:

- Incident-reporting Stage 3 backend suite: 512 passed.
- Incident-reporting stages 1–2 backend suite: 431 passed.
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
- Restricted-run eligibility belongs to the disruption workflow.
- Demonstration imports require development or test environments.
- Import execution context identifies the command environment,
  not an authenticated staff actor.
- Protected import access and actor attribution remain pending.
- Staff provisioning is an interactive CLI, not public registration.
- Self-service password recovery and account management are not implemented.
- Reporting, review, lifecycle changes and audit access are implemented at API level.
- Passenger reporting and staff incident-management interfaces remain pending.
- Public incident responses remain pending.
- Verified incident records do not yet affect journey results.
- Anonymous reports do not establish submitter identity.
- Self-review prevention applies to recorded staff submitters.
- Identity and report-counter cleanup scheduling remain deployment responsibilities.
- Deployment must configure HTTPS, origins and trusted proxies correctly.
- Concurrency tests require permission to create temporary schemas.
- Latest branch changes require GitHub CI before merge.
- Manual incident workflow verification remains pending with the frontend.

## Incident-reporting branch stages

1. Database models, migrations and validation: completed and committed.
2. Passenger submission API, rate limiting and cleanup: completed and committed.
3. Protected staff queue and verify/reject workflow: completed and committed.
4. Revisions, resolution and transactional lifecycle audit history:
   validated; checkpoint commit pending.
5. Approved public incident responses: pending.
6. Passenger and staff frontend workflows: pending.
7. Final integration, documentation, CI and merge: pending.

Estimated branch completion is approximately 72%.
This is an effort estimate, not a count of checked items.
It does not represent completion of the entire v1 release.

## Remaining v1 work

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

Commit the validated Stage 4 lifecycle and audit-history checkpoint.

Continue on feat/incident-reporting with Stage 5:
approved public incident responses with explicit field allowlists
and private-field exclusion.

Commit each validated stage separately.
Push and review the completed branch before merging after CI passes.
