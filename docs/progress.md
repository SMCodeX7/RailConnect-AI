# Project progress

## Current checkpoint

- Updated: 2026-10-18.
- Release target: v1.0 portfolio pilot, in progress.
- Branch: feat/incident-reporting.
- Foundation, journey search/details and staff identity merged into main.
- Incident-reporting stages 1–6 implemented, committed and pushed.
- Last confirmed pushed implementation commit: c36ae1a.
- Stage 6 manual workflow verification completed.
- Complete backend suite: 585 passed without skips.
- Complete frontend suite: 122 passed.
- Stage 7 repeatable API scenarios validated.
- Stage 7 documentation, final Git review and CI verification remain in progress.
- No incident-reporting merge into main has been performed.
- Checkbox confirmation layout is deferred to the final UI review.

## Completed foundation

- Created and cloned the GitHub repository.
- Recorded the modular-monolith architecture decision.
- Configured ignore rules, backend packaging and dependency lockfiles.
- Added validated settings and environment examples.
- Added an app factory, liveness and database readiness endpoints.
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

- Added direct journey search, travel dates, results and pagination.
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
- Added interactive provisioning without default credentials.
- Added hashed opaque session tokens and separate CSRF tokens.
- Added absolute and idle expiry, revocation and account-version invalidation.
- Added explicit permissions and denial for unknown roles.
- Rechecked current roles and permissions during authentication.
- Added database-backed client and account login limits.
- Committed attempt counters independently of credential rejection.
- Rechecked account state before creating login sessions.
- Added login, logout and current-session endpoints.
- Added host-only HTTP-only cookies and production security validation.
- Added origin and CSRF protection for authenticated mutations.
- Added generic errors and non-cacheable session responses.
- Added provisioning, session, login and authorization regression tests.
- Added cleanup preview, retention periods and bounded transactional deletion.
- Verified cleanup preservation, rollback and concurrent login limits.
- Added staff navigation, restoration, login, logout and explicit refresh.
- Displayed roles, permissions and absolute expiry.
- Cleared submitted passwords and handled expiry/unconfirmed logout.
- Cancelled requests when staff panels unmount.
- Added shared HTTP, authentication, panel and navigation tests.
- Manually verified the staff workflow against the running backend.

## Incident-reporting implementation

### Stage 1: database models and protections

- Added separate report, incident, revision and audit records.
- Added review, resolution, scope and impact constraints.
- Added dated-run/segment references and unique revision numbers.
- Added triggers rejecting revision/audit updates, deletes and truncation.
- Verified immutable-history protections and transaction rollback.
- Reconciled ADR 0003 and the roadmap.

### Stage 2: passenger submission

- Added schemas rejecting server-owned review and approval fields.
- Validated hints against prepared runs, stops and active stations.
- Allowed reports concerning cancelled and restricted runs.
- Added server-forced pending state and version 1.
- Added safe receipts excluding narrative and private review fields.
- Required aware observations and rejected future observations.
- Derived authenticated staff submitter identity on the server.
- Required staff-cookie authentication and CSRF protection.
- Rejected invalid staff cookies rather than becoming anonymous.
- Added origin and JSON content-type checks.
- Added separate atomic PostgreSQL submission counters.
- Preserved committed counters when report creation fails.
- Verified concurrent report-limit admission.
- Added report-counter cleanup preview and bounded deletion.
- Fixed identity/report cleanup to delete selected, locked keys only.
- Backend checkpoint: 431 passed.

### Stage 3: protected staff review

- Added a pending queue with bounded pagination and stable ordering.
- Required reports.read for queue access.
- Added explicit protected response fields.
- Added strict expected-version verification/rejection schemas.
- Required independently approved scope, impact, interval and evidence basis.
- Required reports.review, allowed Origin and session-bound CSRF token.
- Rechecked current reviewer account and role permissions.
- Prevented identified staff self-review.
- Locked and refreshed reports before decisions.
- Rejected stale versions and already-reviewed reports.
- Verification atomically creates decision, incident, revision and audit.
- Rejection atomically creates decision and audit without an incident.
- Recorded server-derived actors, timestamps and request IDs.
- Verified complete rollback when audit insertion fails.
- Verified disabled accounts and removed roles invalidate earlier snapshots.
- Verified simultaneous verification/rejection allows one winner and one conflict.
- Backend checkpoint: 512 passed.
- Commit: 71bc123.

### Stage 4: incident lifecycle and audit history

- Added versioned amendment and resolution APIs.
- Required incidents.edit for amendments and incidents.resolve for resolution.
- Required authentication, allowed Origin and session-bound CSRF tokens.
- Rechecked current account and role permissions inside lifecycle transactions.
- Locked incidents and rejected stale versions or changes to resolved incidents.
- Amendments create a new approved revision and increment incident version.
- Preserved earlier revisions and originating report review version.
- Resolution records actor, reason, decision time and effective resolution time.
- Rejected future resolution times and times before the current revision starts.
- Added atomic lifecycle audit writes.
- Verified rollback when lifecycle audit insertion fails.
- Added protected report audit history requiring audit.read.
- Added explicit fields, bounded pagination and no-store responses.
- Included verification, rejection, amendment and resolution history.
- Verified audit authentication and permission restrictions.
- Verified invalid scope leaves incident history unchanged.
- Verified three lifecycle race combinations.
- Backend checkpoint: 566 passed.

### Stage 5: public incident responses

- Added GET /api/v1/incidents with required run_id and bounded pagination.
- Added GET /api/v1/incidents/{incident_id}.
- Selected only incidents linked to verified reports and their current revision.
- Returned incident/revision versions, approved facts and timetable source reference.
- Returned lifecycle status and effective resolution time.
- Excluded private narrative, evidence basis, reasons and actor identities.
- Excluded pending/rejected reports from public incident evidence.
- Included approved active and resolved incidents in run-based listings.
- Verified current revision selection after amendment.
- Verified resolution preserves the approved revision.
- Added public response, pagination and validation tests.
- Backend checkpoint: 581 passed.
- Commit: a16cfbb.

### Stage 6: passenger and staff interfaces

- Added public reporting navigation and form.
- Converted Sri Lanka observation times to UTC.
- Added validation, duplicate-submission prevention and pending receipts.
- Added current-session checks and staff CSRF handling before submission.
- Preserved input after failures and avoided automatic submission retries.
- Added protected queue loading, pagination, errors and retry.
- Added verification and rejection forms with explicit approved facts.
- Added independent-review confirmation and expected-version submission.
- Reloaded the queue after confirmed decisions.
- Blocked decisions after conflicts until successful reload.
- Added amendment and resolution interfaces.
- Loaded current approved incident state before lifecycle mutations.
- Required a fresh evidence basis for amendments.
- Used loaded incident versions rather than manually entered versions.
- Refreshed incident state after successful changes.
- Preserved confirmed success if subsequent refresh fails.
- Added administrator-only audit history with pagination and error handling.
- Added permission-aware panels and session-invalid handling.
- Added request cancellation on unmount.
- Fixed duplicate React keys across staff panels.
- Added passenger, queue, lifecycle and audit interaction tests.
- Frontend checkpoint: 122 passed.
- Latest implementation commit: c36ae1a.

### Stage 7: final integration and documentation

Completed locally:

- Reviewed the existing CI workflow and test execution.
- Added complete synthetic lifecycle and rejection API scenarios.
- Parameterized each scenario for two isolated repetitions.
- Verified original revisions and scheduled run-stop times are preserved.
- Verified lifecycle audit references and resulting versions.
- Verified signed-out public responses exclude private fields.
- Verified rejection creates no linked incident.
- Focused repeatable scenario tests: 4 passed.
- Complete backend suite: 585 passed.

Remaining:

- Commit final scenario/documentation changes if not already committed.
- Complete final Git review and push the feature branch.
- Verify GitHub backend and frontend CI for the final pushed commit.
- Prepare a reviewable pull request when branch work is complete.
- Merge only as a separate authorized action after CI passes.

## Database and demonstration data

- PostgreSQL 17 runs locally through Docker Compose.
- SQLAlchemy and psycopg provide database access.
- Migration d27ced7dc3b1 creates stations.
- Migration cbaf28463dbe creates recurring services and stops.
- Migration 8b4605b4bc60 creates runs/stops and recurring permissions.
- Migration b9c0a25509af creates source records and import summaries.
- Migration dfeb4f1c64a4 creates staff identity, sessions and login limits.
- Migration 5c23c99becea creates incident storage and history protections.
- Migration af88e86de607 creates report submission limits.
- Current migration head: af88e86de607.
- Alembic reports no new upgrade operations.
- Demonstration dataset: 30 stations, 12 patterns and 42 recurring stops.
- Timetable validity: 2026-01-01 through 2028-12-31, inclusive.
- The baseline week 2026-10-12 through 2026-10-18 produces 70 runs
  and skips 14 nonoperating service/date combinations.
- Additional dated runs were prepared for the Stage 6 manual check.
- Search reads explicitly prepared runs and does not create them.
- Timestamps are stored in UTC and displayed in Asia/Colombo.
- Source reference: demo-timetable-v1.
- Source registration records exact file SHA-256.
- Repeated imports preserve source and summary identities.
- These schedules and incidents do not represent live railway operations.

## Current local validation

- Full backend suite: 585 passed without skips.
- Full frontend suite: 122 passed across 16 files.
- Latest complete backend lint and formatting checks passed.
- Backend formatting checkpoint: 168 files.
- mypy checkpoint: 112 source files passed.
- Alembic schema check passed.
- Stage 7 scenario-test lint and formatting passed.
- Four new repeatable scenario cases passed.
- Full backend suite passed after those additions.
- Git whitespace check passed before these documentation updates.
- Frontend lint and production build passed.
- Latest branch CI has not yet been verified.

Focused test groups include:

- Incident database constraints: 36 tests.
- Report review/public/lifecycle/audit API file: 77 tests.
- Lifecycle schemas: 16 tests.
- Review and lifecycle concurrency: 4 tests.
- Passenger form: 9 tests.
- Staff report queue/review: 13 tests.
- Incident lifecycle panel: 14 tests.
- Audit panel: 12 tests.

Focused groups are subsets of the complete suites, not additional tests.

Concurrency tests use independent connections and temporary schemas
created from model metadata. Migration-installed history triggers
are verified separately by migration-backed immutability tests.

The four repeated API scenarios use isolated fixtures.
They are not automated browser tests or two release demonstrations
from reset fixtures.

## Manual verification

Completed on 2026-10-18:

- Database health, application connection and migration checks.
- Backend and frontend startup.
- Station loading through the development proxy.
- Jaffna to Colombo Fort search for 2026-10-19.
- Demo Northern Return, 07:00–16:00, duration nine hours.
- Ordered details, boarding/alighting permissions and source card.
- Signed-out synthetic passenger submission and pending receipt.
- Controller verification: incident version 1, revision 1.
- Amendment to 30-minute synthetic delay: version 2, revision 2.
- Resolution: version 3, revision 2, further changes unavailable.
- Administrator audit history containing all three decisions.
- Controller audit panel restriction.
- Separate rejection and removal from the pending queue.
- Rejection audit with no incident or revision references.
- Signed-out public incident response with approved fields only.

See docs/incident-workflow-check.md for replay instructions.

## Configuration and operational behavior

- Provisioned passwords contain 15–128 characters.
- Passwords and database credentials are not recorded in Git.
- Roles are controller and administrator with explicit permission mappings.
- Session lifetime defaults to eight hours, idle timeout to thirty minutes.
- Login limits default to 30 client and 5 account attempts per five minutes.
- Report limits default to 5 client attempts per hour.
- Report counters are independent of login counters.
- Authentication uses an HTTP-only cookie; only its hash is stored.
- Session-bound CSRF tokens are separate from authentication tokens.
- Session/CSRF state is not persisted in localStorage.
- Queue, audit and public-list pagination default to 20 items and offset 0.
- Limits are 1–100; offsets are 0–10000.
- Approved delays are integer minutes from 1–1440.
- Cancellation requires whole-run scope.
- Lifecycle changes require expected incident versions.
- Resolution increments incident version without replacing the revision.
- No incident reopening workflow is implemented.
- Cleanup is bounded, transactional and operator-run.
- Cleanup scheduling remains a deployment responsibility.

## Limitations and deferred integration

- All timetable patterns and incident scenarios are demonstrations.
- Search coverage depends on explicitly prepared runs.
- Recurring offsets remain minute-resolution.
- Existing service definitions are verified rather than overwritten.
- Sources are resolved through source_ref rather than a database foreign key.
- Source immutability is enforced by the import workflow.
- Source registration does not establish live freshness.
- Staff import access and authenticated import attribution remain pending.
- Staff provisioning remains a CLI; self-service recovery is not implemented.
- Public incident listings include resolved and future-effective records.
- Active lifecycle status alone does not establish current journey impact.
- Verified incidents do not yet alter journey results or scheduled times.
- Anonymous reporting cannot establish person-level submitter identity.
- Self-review prevention applies to recorded staff submitters.
- Management forms currently use explicit record UUIDs.
- Audit panels refresh on request rather than receiving live updates.
- Checkbox confirmation layout remains deferred to the UI review.
- Responsive/accessibility release review remains outstanding.
- Browser automation, reset-fixture release demonstrations and deployment
  verification remain separate release requirements.
- Latest changes require GitHub CI verification before merge.

## Incident-reporting branch stages

1. Models, migrations and constraint validation: complete.
2. Passenger submission API, limits and cleanup: complete.
3. Protected queue and report decisions: complete.
4. Incident lifecycle and audit history: complete.
5. Public incident responses: complete.
6. Passenger/staff interfaces and manual verification: complete.
7. Final integration, documentation and CI verification: in progress.

Approximate branch completion: 95%.
This is an effort estimate, not overall v1 release completion.

## Remaining v1 work

- Authenticated timetable import access and actor attribution.
- Protected timetable management interface.
- Disruption effects and feasible alternatives.
- Policy retrieval and ownership-protected passenger assistant.
- Assistant evaluation and browser workflow tests.
- Two complete release demonstrations from reset fixtures.
- Responsive/accessibility review and checkbox layout correction.
- Deployment, persistence, restart, backup and restore verification.
- Cleanup operational procedures or scheduling.
- Final portfolio documentation, demonstration video and release tag.

Reconcile station aliases, repository templates, license and OpenAPI
compatibility requirements with the handbook before declaring v1 complete.

## Next task

Finish Stage 7 documentation and final branch review.
Commit any remaining validated changes and push feat/incident-reporting.

Verify backend and frontend CI against the final pushed commit.

Keep main unchanged until a separately authorized pull-request merge.
