# RailConnect AI roadmap

## Baseline

The Complete Project and Development Handbook, document version 1.0,
defines the release requirements. This roadmap tracks implementation,
local validation, and deployment verification.

## Current checkpoint

- Updated 2026-11-17.
- Release target is the v1.0 portfolio pilot.
- Active branch is `feat/pilot-release`. UI polish is committed as `aeff9b0`.
- `main` includes incident reporting, timetable management, disruption effects,
  the passenger assistant, and pilot validation.
- Latest local validation passed 653 backend tests, 135 frontend tests, and
  four Playwright tests. Frontend lint and build passed. Alembic detected
  no new upgrade operations.
- Release-candidate CI, clean-checkout verification, and deployment checks
  are pending. See [project progress](progress.md).

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
- [x] Authenticated import preview and commit.
- [x] Staff actor attribution for imports.
- [x] Protected timetable management interface.

Schedules are fictional. Search depends on prepared dated runs. Source
registration time records when data was registered. Live updates are unavailable.

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
- [x] Resolved incidents are read-only.
- [x] Origin and CSRF protection.
- [x] Audit failures roll back business changes.
- [x] Verification/rejection concurrency.
- [x] Amendment/amendment concurrency.
- [x] Amendment/resolution concurrency.
- [x] Resolution/resolution concurrency.
- [x] Protected audit history requiring `audit.read`.
- [x] Audit pagination, allowlists and permission tests.

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

Run listings include approved active and resolved incidents. Journey effects
depend on the applicable run, segment, and effective time. Scheduled timestamps
remain visible alongside estimates.

### Branch stages

- [x] Stage 1 — Models, migrations and constraints.
- [x] Stage 2 — Passenger API, limits and cleanup.
- [x] Stage 3 — Protected queue and report decisions.
- [x] Stage 4 — Lifecycle and audit history.
- [x] Stage 5 — Public incident responses.
- [x] Stage 6 — Passenger/staff interfaces and manual verification.
- [ ] Stage 7 — Confirm final incident-branch documentation and CI evidence.
- [x] Incident-reporting branch merged into `main`.

## v1 disruptions and alternatives

- [x] Match effects to dated runs and ordered segments.
- [ ] Apply effective-time boundaries.
- [x] Preserve scheduled timestamps.
- [ ] Represent estimated timestamps and their basis separately.
- [ ] Propagate approved downstream delays.
- [ ] Handle cancellation and restriction eligibility.
- [ ] Document overlapping-effect rules.
- [ ] Return feasible known alternatives with explanations.
- [x] Handle no available alternative explicitly.
- [ ] Test unrelated incidents, resolution and overnight boundaries.
- [x] Refresh affected journey views after operational changes.

Only approved, applicable effects can change journey estimates or
eligibility. Review the overlapping-effect rules before closing that
checklist item.

## v1 passenger assistant

- [ ] Approved versioned policy documents and sources.
- [x] Lexical retrieval and stable chunk references.
- [ ] Authorized journey, incident and policy tools.
- [ ] Entity resolution and ambiguity clarification.
- [ ] Bounded calls, response sizes and deadlines.
- [x] Persisted conversations with server-issued guest ownership.
- [x] Ownership checks before reading/continuing conversations.
- [ ] Structured answers, citations, freshness and warnings.
- [x] Deterministic evidence-based fallback.
- [x] Assistant interface with citations and failure states.
- [ ] Optional model adapter with timeout and evidence validation.

Distinguish approved evidence, fictional examples and unavailable information.

## v1 evaluation and release

- [x] At least 60 independent English evaluation cases.
- [x] At least 15 multi-turn scenarios.
- [x] Separate tuning and final evaluation examples.
- [ ] Retrieval, faithfulness, ambiguity and coverage results.
- [ ] No unsupported critical operational claims in the release set.
- [x] Browser automation for search, review and affected-journey refresh.
- [x] Negative authorization and conversation ownership tests.
- [ ] Complete the demonstration twice from reset fixtures.
- [ ] Responsive and accessible passenger/staff interfaces.
- [x] Correct checkbox confirmation layout.
- [ ] Deployment build files and HTTPS.
- [ ] Trusted origin and proxy configuration.
- [ ] Cleanup operational procedures.
- [ ] Restart and persistence verification.
- [ ] Backup and separate-environment restore verification.
- [ ] Setup, architecture, evaluation and operations documentation.
- [ ] README, screenshots and demonstration video.
- [ ] Final release documentation committed and pushed.
- [ ] GitHub CI verified for the pushed release candidate.
- [ ] Release branch reviewed and merged.
- [ ] Deployed commit recorded and v1.0.0 tagged after release gates pass.

The independent assistant evaluation passed 51 of 60 cases. It declined
all 20 unsupported questions and returned a fallback for nine supported
questions. See the [evaluation results](../evaluation/assistant/README.md).

## Validation checkpoints

See [project progress](progress.md#local-validation) for the latest results.

Historical:

- Foundation — 41 backend and 5 frontend tests.
- Journey details — 184 backend and 33 frontend tests.
- Staff identity — 310 backend and 62 frontend tests.
- Incident stages 1–2 — 431 backend tests.
- Incident stage 3 — 512 backend tests.
- Incident stage 4 — 566 backend tests.
- Incident stage 5 — 581 backend tests.
- Incident reporting checkpoint — 585 backend and 122 frontend tests.
- Timetable management checkpoint — 603 backend and 128 frontend tests.

Focused counts are subsets of the complete suites. Concurrency fixtures use
independent transactions in temporary metadata schemas. Migration-installed
history triggers are tested separately.

## Known limitations

- Fictional schedules and incident scenarios.
- Explicit preparation required for journey dates.
- Some supported assistant questions return a fallback.
- UUID-based incident/report lookup in staff forms.
- Incident reopening and self-service password recovery are unavailable.
- Anonymous reports lack person-level identity verification.
- Audit updates require a manual refresh.
- Deployment and full release verification are outstanding.

## Remaining feature branches

`feat/pilot-release` is the final planned v1 feature branch. The handbook
requirements apply to the full release.

## Later versions

- **v1.1** — Passenger accounts, saved journeys, subscriptions, notifications,
  and further usability and recovery improvements.
- **v2** — Multilingual evaluation and booking sandbox.
- **v3** — Observed-data delay intelligence or explicitly labelled simulation.
- **v4** — Maintenance and expanded operations workflows.
- **v5** — Conditional integrations, scaling and operational readiness.

## Next task

Finish the release documentation, verify the release candidate from a
clean checkout, and check CI against the pushed commit.
