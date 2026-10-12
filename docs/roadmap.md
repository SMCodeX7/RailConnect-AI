# RailConnect AI roadmap

## Baseline

The Complete Project and Development Handbook, document version 1.0,
defines the release requirements.

This checklist tracks implementation. Passing tests alone does not
mean a feature is deployed or released.

## v0.1 foundation

Implemented and locally validated:

- Modular FastAPI backend and React/TypeScript frontend.
- Installed backend package and dependency lockfiles.
- PostgreSQL configuration and Alembic migrations.
- Validated settings, request IDs, error responses and structured logging.
- Liveness and database readiness endpoints.
- Station listing/search API and connected selectors.
- Backend and frontend CI.
- Foundation clean-checkout verification.

Remaining verification:

- [ ] Check repository templates and license.
- [ ] Document Linux/macOS setup differences.
- [ ] Verify explicit database constraint regression tests.

## v1 journey and data requirements

Implemented and tested:

- Demonstration station and timetable seeding.
- Input validation and repeatable timetable imports.
- Direct journey search with operating days and validity dates.
- Reverse-direction and overnight handling.
- Frontend search, pagination, loading, retry and cancellation of stale requests.

Remaining:

- [ ] Source records and dataset card.
- [ ] Import preview and traceable import summary.
- [ ] Canonical dated service runs and ordered segment identity.
- [ ] Boarding and alighting permissions.
- [ ] Journey detail API and ordered-stop view.
- [ ] Arrival-deadline filtering.
- [ ] Source/version and freshness information in journey views.
- [ ] Record and reconcile timetable unit and API naming decisions.

## v1 staff identity

- [ ] Staff users, roles and explicit permissions.
- [ ] Secure password hashing and initial staff provisioning.
- [ ] Expiring, revocable sessions.
- [ ] Login, logout and current-session API.
- [ ] Protected staff navigation and login UI.
- [ ] CSRF protection for cookie-authenticated mutations.
- [ ] Login rate limiting.
- [ ] Missing, expired, revoked and insufficient-permission tests.

## v1 reports and incidents

- [ ] Separate passenger reports and verified incidents.
- [ ] Rate-limited submission with server-forced pending state.
- [ ] Protected pending queue.
- [ ] Verification and rejection with actor and reason.
- [ ] Expected-version conflict checks.
- [ ] Immutable incident revisions.
- [ ] Transactional audit records.
- [ ] Resolution with effective end time and preserved history.
- [ ] Public response allowlists.
- [ ] Staff review UI and refresh after decisions.
- [ ] Repeatable synthetic report and incident scenarios.

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
- [ ] Restart and persistence verification.
- [ ] Backup and separate-environment restore verification.
- [ ] Setup, architecture, evaluation and operations documentation.
- [ ] README, screenshots and short demonstration video.
- [ ] Record deployed commit and tag v1.0.0 after release gates pass.

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

Complete the journey data contract and detail workflow before adding
staff identity and incident review.

Preserve the existing tested search behavior while introducing
reviewed migrations and compatibility changes.
