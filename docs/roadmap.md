# RailConnect AI roadmap

## Baseline

The Complete Project and Development Handbook, document version 1.0,
defines release requirements.

This checklist tracks implementation and validation.
Local tests do not establish deployment or release completion.

## Current checkpoint

- Updated: 2026-10-18.
- Release target: v1.0 portfolio pilot.
- Branch: feat/incident-reporting.
- Foundation, journeys and staff identity merged into main.
- Incident-reporting stages 1–6 complete and pushed through c36ae1a.
- Stage 6 manual workflow verification passed.
- Complete backend suite: 585 passed without skips.
- Complete frontend suite: 122 passed.
- Four repeatable synthetic API scenario cases passed.
- Stage 7 documentation, final branch review and CI verification in progress.
- Incident-reporting work has not been merged into main.
- Checkbox confirmation layout remains deferred.

## Foundation

- [x] Modular FastAPI backend and React/TypeScript frontend.
- [x] Backend packaging and dependency lockfiles.
- [x] PostgreSQL configuration and Alembic migrations.
- [x] Settings, request IDs, error responses and structured logging.
- [x] Liveness and database readiness.
- [x] Station listing/search and connected selectors.
- [x] Backend and frontend CI.
- [x] Foundation clean-checkout verification.
- [x] Linux/macOS setup differences documented.
- [ ] Repository templates and license review.
- [ ] Station alias requirements reconciled.
- [ ] OpenAPI compatibility requirements verified.
- [ ] Release-candidate clean-checkout verification.

## v1 journey and data requirements

- [x] Demonstration station and timetable seeding.
- [x] Validated, repeatable timetable imports.
- [x] Direct journey search.
- [x] Operating-day and validity checks during preparation.
- [x] Reverse-direction and overnight handling.
- [x] Search pagination, loading, retry and request cancellation.
- [x] Source records and dataset card.
- [x] Import preview and successful import summaries.
- [x] Canonical dated runs and ordered segment identity.
- [x] Boarding and alighting permissions.
- [x] Journey detail API and ordered-stop view.
- [x] Inclusive arrival-deadline filtering.
- [x] Source/version and freshness wording.
- [x] Timetable units and API naming decisions.
- [x] Constraints and materialization regression tests.
- [ ] Authenticated import preview and commit.
- [ ] Staff actor attribution for imports.
- [ ] Protected timetable management interface.

Schedules are fictional.
Search depends on prepared dated runs.
Source registration time does not establish operational freshness.

## v1 staff identity

- [x] Users, roles and explicit permissions.
- [x] Argon2id hashing and interactive provisioning.
- [x] Expiring, revocable sessions.
- [x] Login, logout and current-session API.
- [x] Staff interface and session restoration.
- [x] Origin and CSRF protection.
- [x] Database-backed login limits.
- [x] Authentication and permission-denial tests.
- [x] Concurrent client/account limit verification.
- [x] Bounded cleanup with preview.
- [x] Cleanup preservation and rollback.
- [x] Login, logout, expiry and navigation tests.
- [x] Manual staff-access verification.
- [x] Authorization connected to reporting, review, lifecycle and audit.
- [ ] Cleanup scheduling or operational procedure during deployment.
- [ ] Authorization connected to remaining management workflows.

Visible permission labels do not implement management actions.
Authorization is enforced on the server.

## v1 reports and incidents

### Storage and submission

- [x] Separate reports and verified incidents.
- [x] Immutable revision and audit storage.
- [x] Review, resolution, scope and impact constraints.
- [x] Database protections against history mutation.
- [x] Input rejects server-owned fields.
- [x] Prepared run, station and segment hint validation.
- [x] Aware observation times and future-time rejection.
- [x] Server-forced pending submission.
- [x] Safe submission receipts.
- [x] Anonymous submission and server-derived staff attribution.
- [x] Staff-cookie CSRF enforcement.
- [x] Origin and content-type checks.
- [x] Independent database-backed report limits.
- [x] Counter transactions survive report creation failure.
- [x] Concurrent admission verification.
- [x] Bounded counter cleanup and preview.

### Review and lifecycle

- [x] Protected pending queue and pagination.
- [x] Stable queue ordering.
- [x] Verification/rejection with actor and reason.
- [x] Expected-version validation and locked decisions.
- [x] Independent approval of operational facts.
- [x] Identified staff self-review prevention.
- [x] Current account and role checks.
- [x] Atomic verification and rejection audit writes.
- [x] New approved revisions for amendments.
- [x] Resolution actor, reason and effective time.
- [x] Preserved revision history after resolution.
- [x] No further mutation of resolved incidents.
- [x] Origin and CSRF protection.
- [x] Audit failures roll back business changes.
- [x] Verification/rejection concurrency.
- [x] Amendment/amendment concurrency.
- [x] Amendment/resolution concurrency.
- [x] Resolution/resolution concurrency.
- [x] Protected audit history requiring audit.read.
- [x] Audit pagination, allowlists and permission tests.

No reopening workflow is implemented.

### Public responses and interfaces

- [x] Public incident detail and run-filtered listing.
- [x] Current approved revision selection.
- [x] Public field allowlists.
- [x] Pending/rejected report exclusion.
- [x] Private narrative, evidence basis, reasons and actors excluded.
- [x] Lifecycle status, versions and resolution time exposed.
- [x] Timetable source reference distinguished from incident evidence.
- [x] Passenger reporting form and receipt.
- [x] Staff pending queue and verification/rejection forms.
- [x] Amendment and resolution interfaces.
- [x] Administrator audit interface.
- [x] Permission-aware navigation and panel visibility.
- [x] Refresh after confirmed queue/lifecycle changes.
- [x] Conflict handling requires reload.
- [x] Request cancellation and duplicate-submission prevention.
- [x] Component and API-client regression tests.
- [x] Manual submission-to-resolution workflow verification.
- [x] Manual rejection and audit verification.
- [x] Signed-out public-response verification.
- [x] Repeatable isolated API lifecycle/rejection scenarios.
- [ ] Final documentation changes committed and pushed.
- [ ] GitHub CI verified for the final branch commit.
- [ ] Branch review and separately authorized merge.

Active lifecycle state does not establish current journey applicability.
Run listings include approved active and resolved incidents.

Verified incident records do not yet alter journey calculations.

### Branch stages

- [x] Stage 1: models, migrations and constraints.
- [x] Stage 2: passenger API, limits and cleanup.
- [x] Stage 3: protected queue and report decisions.
- [x] Stage 4: lifecycle and audit history.
- [x] Stage 5: public incident responses.
- [x] Stage 6: passenger/staff interfaces and manual verification.
- [ ] Stage 7: final integration, documentation and CI verification.

Approximate branch completion: 95%.
This is not overall v1 completion.

Pushes update feat/incident-reporting only.
A merge into main is a separate action.

## v1 disruptions and alternatives

- [ ] Match effects to dated runs and ordered segments.
- [ ] Apply effective-time boundaries.
- [ ] Preserve scheduled timestamps.
- [ ] Represent estimated timestamps and their basis separately.
- [ ] Propagate approved downstream delays.
- [ ] Handle cancellation and restriction eligibility.
- [ ] Document overlapping-effect rules.
- [ ] Return feasible known alternatives with explanations.
- [ ] Handle no available alternative explicitly.
- [ ] Test unrelated incidents, resolution and overnight boundaries.
- [ ] Refresh affected journey views after operational changes.

Unverified claims must not affect operational journey results.
Do not blindly add overlapping reported delays.

## v1 passenger assistant

- [ ] Approved versioned policy documents and sources.
- [ ] Lexical retrieval and stable chunk references.
- [ ] Authorized journey, incident and policy tools.
- [ ] Entity resolution and ambiguity clarification.
- [ ] Bounded calls, response sizes and deadlines.
- [ ] Persisted conversations with server-issued guest ownership.
- [ ] Ownership checks before reading/continuing conversations.
- [ ] Structured answers, citations, freshness and warnings.
- [ ] Deterministic evidence-based fallback.
- [ ] Assistant interface with citations and failure states.
- [ ] Optional model adapter with timeout and evidence validation.

Distinguish approved evidence, fictional examples and unavailable information.

## v1 evaluation and release

- [ ] At least 60 independent English evaluation cases.
- [ ] At least 15 multi-turn scenarios.
- [ ] Separate tuning and final evaluation examples.
- [ ] Retrieval, faithfulness, ambiguity and coverage results.
- [ ] No unsupported critical operational claims in the release set.
- [ ] Browser automation for search, review and affected-journey refresh.
- [ ] Negative authorization and conversation ownership tests.
- [ ] Complete the demonstration twice from reset fixtures.
- [ ] Responsive and accessible passenger/staff interfaces.
- [ ] Correct checkbox confirmation layout.
- [ ] Deployment build files and HTTPS.
- [ ] Trusted origin and proxy configuration.
- [ ] Cleanup operational procedures.
- [ ] Restart and persistence verification.
- [ ] Backup and separate-environment restore verification.
- [ ] Setup, architecture, evaluation and operations documentation.
- [ ] README, screenshots and demonstration video.
- [ ] Deployed commit recorded and v1.0.0 tagged after release gates pass.

Repeated isolated API tests do not replace browser automation or
the two release demonstrations from reset fixtures.

## Validation checkpoints

Current:

- Backend: 585 passed without skips.
- Frontend: 122 passed across 16 files.
- Latest full backend lint/formatting passed.
- Backend formatting checkpoint: 168 files.
- mypy checkpoint: 112 source files.
- Alembic check passed; head af88e86de607.
- New scenario-test lint/formatting passed.
- Four repeatable API cases passed.
- Full backend suite passed after adding those cases.
- Frontend lint and production build passed.
- Stage 6 manual workflow passed.
- Git whitespace check passed before final documentation changes.
- Final branch CI remains unverified.

Historical:

- Foundation: 41 backend and 5 frontend tests.
- Journey-details: 184 backend and 33 frontend tests.
- Staff identity: 310 backend and 62 frontend tests.
- Incident stages 1–2: 431 backend tests.
- Incident Stage 3: 512 backend tests.
- Incident Stage 4: 566 backend tests.
- Incident Stage 5: 581 backend tests.

Focused counts are subsets of the complete suites.

Concurrency fixtures use independent transactions in temporary metadata
schemas. Migration-installed history triggers are tested separately.

## Known limitations

- Fictional schedules and incident scenarios.
- Explicit preparation required for journey dates.
- Protected timetable imports and actor attribution not implemented.
- Incident effects not connected to journey calculations.
- UUID-based incident/report lookup in staff forms.
- No incident reopening.
- No self-service password recovery.
- No person-level identity guarantee for anonymous reports.
- Manual audit refresh rather than live notifications.
- Checkbox layout correction deferred to UI review.
- Deployment and full release verification outstanding.

## Remaining feature branches

1. feat/incident-reporting — finalization in progress.
2. feat/timetable-management.
3. feat/disruption-effects.
4. feat/passenger-assistant.
5. feat/pilot-validation.
6. feat/pilot-release.

Split branches where useful for review.
Branch organization does not reduce handbook requirements.

## Later versions

v1.1:
Passenger accounts, saved journeys, subscriptions, notifications
and further usability/recovery improvements.

v2:
Multilingual evaluation and booking sandbox.

v3:
Observed-data delay intelligence or explicitly labelled simulation.

v4:
Maintenance and expanded operations workflows.

v5:
Conditional integrations, scaling and operational readiness.

## Next task

Finish Stage 7 documentation and final Git review.
Push the final feat/incident-reporting commit and verify both CI jobs.

Prepare a pull request when branch verification is complete.
Merge into main only as a separate authorized action.

After the branch is merged and main is synchronized, continue with
authenticated timetable management.
