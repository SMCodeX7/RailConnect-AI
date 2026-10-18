# RailConnect AI roadmap

## Baseline

The Complete Project and Development Handbook, document version 1.0,
defines the release requirements.

This checklist tracks implementation and validation.
Passing local tests does not establish that a feature is deployed or released.

## Current checkpoint

- Updated: 2026-10-18.
- Release target: v1.0 portfolio pilot.
- Active branch: feat/incident-reporting.
- Foundation, journey search/details and staff identity merged into main.
- Incident-reporting stages 1-2 completed and committed locally.
- Stage 3 protected staff queue and verify/reject workflow validated locally.
- Complete backend suite: 512 passed without skips.
- Stage 3 documentation and checkpoint commit are pending.
- Incident amendments, resolution, public responses and frontend remain.
- GitHub CI for the current incident-reporting changes remains pending.

## Foundation

Implemented and validated:

- [x] Modular FastAPI backend and React/TypeScript frontend.
- [x] Backend packaging and dependency lockfiles.
- [x] PostgreSQL configuration and Alembic migrations.
- [x] Validated settings, request IDs, error responses and structured logging.
- [x] Liveness and database readiness endpoints.
- [x] Station listing/search API and connected selectors.
- [x] Backend and frontend CI.
- [x] Foundation clean-checkout verification.
- [x] Documented Linux/macOS setup differences.

Remaining release checks:

- [ ] Check repository templates and license.
- [ ] Reconcile station alias requirements with the handbook.
- [ ] Verify OpenAPI compatibility requirements.
- [ ] Repeat clean-checkout verification for the release candidate.

## v1 journey and data requirements

- [x] Demonstration station and timetable seeding.
- [x] Input validation and repeatable timetable imports.
- [x] Direct journey search.
- [x] Operating-day and validity checks during run preparation.
- [x] Reverse-direction and overnight handling.
- [x] Search pagination, loading, retry and stale-request cancellation.
- [x] Source records and dataset card.
- [x] Import preview and persistent successful import summary.
- [x] Canonical dated service runs and ordered segment identity.
- [x] Boarding and alighting permissions.
- [x] Journey detail API and ordered-stop view.
- [x] Inclusive arrival-deadline filtering.
- [x] Source/version and freshness information in journey views.
- [x] Documented timetable units and API naming decisions.
- [x] Database constraint and run-materialization regression tests.
- [ ] Authenticated staff import preview and commit.
- [ ] Staff actor attribution for protected imports.
- [ ] Protected timetable management interface.

Demonstration schedules are fictional.
Search coverage depends on explicitly prepared dated runs.
Source registration time does not establish live operational freshness.

## v1 staff identity

- [x] Staff users, roles and explicit permissions.
- [x] Argon2id password hashing and interactive provisioning.
- [x] Expiring, revocable sessions.
- [x] Login, logout and current-session API.
- [x] Staff-access interface and session restoration.
- [x] CSRF and origin protection.
- [x] Database-backed login rate limiting.
- [x] Missing, expired, revoked and insufficient-permission tests.
- [x] Concurrent client and account limit verification.
- [x] Bounded identity cleanup with read-only preview.
- [x] Frontend login, logout, expiry and navigation tests.
- [x] Manual login, restoration, refresh and logout verification.
- [x] Verified identity cleanup deletes only selected, locked batch keys.
- [x] Connected authorization to report queue and review operations.
- [ ] Configure identity cleanup scheduling during deployment.
- [ ] Connect authorization to remaining management workflows.

Permission displays do not implement the corresponding management actions.
Every protected action requires server-side authorization.

## v1 reports and incidents

### Completed database and submission work

- [x] Separate passenger-report and verified-incident database records.
- [x] Incident revision and actor-attributed audit storage.
- [x] Database constraints for review state, scope and impact values.
- [x] Database protection against revision/audit updates, deletes and truncation.
- [x] Submission schemas rejecting server-owned review fields.
- [x] Scope-hint validation against prepared runs, stops and active stations.
- [x] Timezone-aware observation times and future-observation rejection.
- [x] POST /api/v1/reports with server-forced pending state.
- [x] Submission receipts excluding narratives and private review fields.
- [x] Anonymous submission and server-derived staff attribution.
- [x] CSRF checks when a staff session cookie is present.
- [x] Origin and JSON content-type checks.
- [x] Separate database-backed report-submission rate limits.
- [x] Counter transactions preserved independently of report creation failures.
- [x] Concurrent report-limit admission verification.
- [x] Report-counter cleanup preview and bounded transactional deletion.
- [x] Submission authorization, validation and rollback tests.

### Completed protected review work

- [x] Protected pending queue with bounded pagination.
- [x] Stable queue ordering by submission time and report ID.
- [x] Explicit staff-only queue response fields.
- [x] Verification and rejection with authenticated actor and reason.
- [x] Strict expected-version request validation.
- [x] Locked report reads and conflict checks.
- [x] Independent validation of approved run/segment references.
- [x] Atomic verification creating the linked incident and initial revision.
- [x] Transactional audit writes for verification and rejection.
- [x] Server-derived reviewer identity, decision time and audit request ID.
- [x] Prevention of identified staff self-review.
- [x] Current account and role-permission checks in the decision service.
- [x] Review authorization and rollback tests.
- [x] Simultaneous verification/rejection produces one decision and one conflict.

### Remaining lifecycle and interface work

- [ ] Approved amendment workflow creating new immutable revisions.
- [ ] Expected-version conflict checks for amendments and resolution.
- [ ] Transactional audit writes for amendment and resolution.
- [ ] Resolution with effective end time and preserved history.
- [ ] Approved public incident response allowlists.
- [ ] Public exclusion of pending/rejected claims and private notes.
- [ ] Passenger reporting interface.
- [ ] Staff review and incident-management interfaces.
- [ ] Refresh after successful review and lifecycle decisions.
- [ ] Repeatable synthetic report and incident scenarios.
- [ ] Lifecycle authorization, concurrency and rollback tests.
- [ ] Protected audit-history access.
- [ ] Manual end-to-end incident workflow verification.

Verification and rejection are implemented at API and service levels.
Amendments, resolution, public incident responses and reporting/review
interfaces remain pending.

### Incident-reporting branch stages

- [x] Stage 1: database models, migrations and constraint validation.
- [x] Stage 2: passenger submission API, rate limiting and cleanup.
- [x] Stage 3: protected staff queue and verify/reject workflow.
- [ ] Stage 4: revisions, resolution and transactional lifecycle audit history.
- [ ] Stage 5: approved public incident responses.
- [ ] Stage 6: passenger and staff frontend workflows.
- [ ] Stage 7: final integration, documentation, CI and merge.

Stages 1-2 are committed locally.
Stage 3 has passed local validation; its documentation and commit are pending.

Estimated incident-reporting branch completion is approximately 55%.
This is an effort estimate, not overall v1 release completion.

Commit each validated stage separately.
Keep the work on feat/incident-reporting until branch review and merge.

## v1 disruptions and alternatives

- [ ] Match effects to dated runs and ordered segments.
- [ ] Apply effective-time boundaries.
- [ ] Preserve scheduled times and distinguish estimated times.
- [ ] Propagate approved delays to relevant downstream stops.
- [ ] Handle cancellations and restrictions.
- [ ] Document overlapping-effect rules.
- [ ] Return feasible known alternatives with explanations.
- [ ] Handle no available alternative explicitly.
- [ ] Test unrelated incidents, resolution and overnight boundaries.
- [ ] Refresh affected journey views after operational changes.

Unverified passenger reports must not change operational journey results.
Estimated delays require approved values and an explicit evidence basis.

Verified incident records do not yet affect journey results.
That integration belongs to the disruption feature.

## v1 passenger assistant

- [ ] Approved, versioned policy documents and source records.
- [ ] Lexical retrieval with stable chunk references.
- [ ] Authorized journey, incident and policy tools.
- [ ] Entity resolution and ambiguity clarification.
- [ ] Bounded tool calls, response sizes and deadlines.
- [ ] Persisted conversations with server-issued guest ownership.
- [ ] Ownership checks before reading or continuing conversations.
- [ ] Structured answers, citations, freshness and warnings.
- [ ] Deterministic evidence-based fallback.
- [ ] Assistant UI with citations and failure states.
- [ ] Optional model adapter with timeout and evidence validation.

The assistant must distinguish verified operational evidence,
fictional demonstration data and unavailable information.

## v1 evaluation and release

- [ ] At least 60 independent English evaluation cases.
- [ ] At least 15 multi-turn scenarios.
- [ ] Separate tuning and final evaluation examples.
- [ ] Record retrieval, faithfulness, ambiguity and coverage results.
- [ ] No unsupported critical operational claims in the release set.
- [ ] Browser tests for search, review and affected-journey refresh.
- [ ] Negative authorization and conversation ownership tests.
- [ ] Complete the demonstration twice from reset fixtures.
- [ ] Responsive, accessible passenger and staff UI.
- [ ] Deployment build files and HTTPS configuration.
- [ ] Trusted origin and proxy configuration.
- [ ] Identity and report-counter cleanup operational procedures.
- [ ] Restart and persistence verification.
- [ ] Backup and separate-environment restore verification.
- [ ] Setup, architecture, evaluation and operations documentation.
- [ ] README, screenshots and short demonstration video.
- [ ] Record deployed commit and tag v1.0.0 after release gates pass.

## Validation checkpoints

Historical checkpoints:

- Foundation verification: 41 backend and 5 frontend tests passed.
- Journey-details backend suite: 184 passed.
- Journey frontend suite: 33 passed.
- Completed staff-identity backend suite: 310 passed without skips.
- Completed staff-identity frontend suite: 62 passed.
- Nine manual staff-access checks passed.
- Incident-reporting stages 1-2 backend suite: 431 passed without skips.

Current incident-reporting checkpoint:

- Complete backend suite: 512 passed without skips.
- Incident database and scope tests: 36 passed.
- Submission schema tests: 28 passed.
- Report-limit tests: 13 passed.
- Submission-service tests: 11 passed.
- Report API tests: 17 passed.
- Concurrent report-limit test: 1 passed.
- Report cleanup tests: 15 passed.
- Pending-queue tests: 14 passed.
- Review-schema tests: 43 passed.
- Review API and service-security tests: 23 passed.
- Simultaneous-review test: 1 passed.
- Combined identity/report cleanup tests: 29 passed.
- Ruff lint passed across source, tests, migrations and scripts.
- Ruff formatting: 155 files already formatted.
- mypy passed for 100 source files.
- Alembic reports no new upgrade operations.
- Migration head remains af88e86de607.
- Git whitespace check passed before the latest documentation edits.
- Current incident-reporting GitHub CI remains pending.

Focused test counts are subsets of the complete suite.
The combined cleanup count is not an additional set of tests.

The review concurrency test uses independent connections in a temporary
schema created from model metadata and removes that schema afterward.
Migration-installed history triggers are tested separately.

New features must be validated against the complete current suite.
Historical frontend results do not verify future incident interface changes.

## Remaining feature branches

The working sequence after staff identity is:

1. feat/incident-reporting
2. feat/timetable-management
3. feat/disruption-effects
4. feat/passenger-assistant
5. feat/pilot-validation
6. feat/pilot-release

Split a branch when necessary to keep changes reviewable.
Branch organization does not reduce the handbook acceptance requirements.

## Later versions

v1.1:
Passenger accounts, saved journeys, subscriptions and notifications,
plus further usability and recovery improvements.

v2:
Multilingual evaluation and booking sandbox.

v3:
Observed-data delay intelligence or explicitly labelled simulation.

v4:
Maintenance and expanded operations workflows.

v5:
Conditional integrations, scaling and operational readiness.

## Next implementation task

Update the stage 3 documentation and commit the validated protected
staff-review checkpoint on feat/incident-reporting.

Continue with stage 4:
versioned incident amendments, resolution and transactional lifecycle audit history.

Reuse the identity module for authenticated actors and explicit permissions.
Require expected versions for lifecycle changes.
Preserve previous approved revisions and audit records.

Then implement approved public incident responses and passenger/staff interfaces.

Commit each validated stage separately.
Push and review the completed branch before merging after CI passes.

Connect disruption calculations in the subsequent disruption feature.
Preserve the existing tested journey and authentication behavior.
