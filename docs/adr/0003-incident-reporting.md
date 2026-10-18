# ADR 0003: Incident reports, verified incidents and review

## Status

Accepted

## Context

The v1 handbook distinguishes a passenger report from a verified
operational incident.

A report is an unverified claim.
An authorized staff decision establishes approved scope, effective period
and impact.

The system must preserve attribution, review history, concurrency checks
and public evidence boundaries.

## Decision

Implement reporting and lifecycle management in the incidents module.

Keep separate records for:

- Reports: narrative, scope hints and review state.
- Incidents: identity, originating report, lifecycle state and current revision.
- Revisions: immutable approved operational facts.
- Audit events: actor, action, reason, time, request ID and references.

Link each incident to its originating report.
Store approved scope and impact in revisions.

## Identity and permissions

Reuse the individual staff identity and session model in ADR 0005.

Derive actor identity and permissions on the server.

Require:

- reports.read for the pending queue.
- reports.review for verification and rejection.
- incidents.edit for amendments.
- incidents.resolve for resolution.
- audit.read for protected audit history.

Controllers do not receive audit.read by default.
Administrators have explicitly mapped permissions including audit.read.

A shared credential does not replace individual staff identity.

Submitters cannot assign verification state, reviewer identity,
approved impacts or review timestamps.

## Submission

Accept title, narrative, aware observation time and optional scope hints.

Validate station hints against active stations.
Validate dated-run and ordered-segment references.
Require paired segment endpoints and increasing stop sequences.
When station and run/segment hints are combined, require matching scope.

Reject future observations.
Allow reports concerning cancelled and restricted runs.

Hints remain unverified.
Acceptance does not establish journey feasibility or operational impact.

New reports have server-forced pending state and version 1.

Anonymous submission is permitted.
Require JSON and an allowed browser Origin.

If a staff cookie is present, require valid authentication and CSRF.
Derive submitting staff identity on the server.

Invalid staff cookies must not silently become anonymous access.

Identified staff submitters cannot review their own reports.
Anonymous reports do not establish person-level identity.

Return a pending receipt without narrative or private review fields.

## Submission limits and cleanup

Use separate PostgreSQL counters for report submissions.

Default admission limit: five attempts per client per hour.
Use a hash of the server-observed client identifier.
Deployment must configure trusted proxies correctly.

Update counters atomically across workers.
Commit the attempt counter independently of report creation.

A report creation failure must not reset the attempt counter.

Malformed bodies rejected before the service do not consume its counter.
Return 429 with Retry-After when limited.

Provide preview and explicit bounded cleanup.
Retain expired counters for one day by default.

Select and lock bounded keys before deleting those exact records.
Cleanup preserves reports, login counters and current windows.
Applied cleanup is transactional.

Scheduling remains an operational responsibility.

## Pending queue

Expose a protected pending-report queue.

Require reports.read in the HTTP dependency and application service.
Return explicit staff-review fields, including narrative where authorized.

Order by submission time and report ID.
Use bounded pagination.

Queue responses are private management contracts.
Reading does not change report state.
Successful responses use Cache-Control: no-store.

## Verification and rejection

Review requests include expected report version and a nonempty reason.

Lock and refresh the report before checking pending state and version.
Reject stale or completed decisions with a conflict.

Verification requires explicit approved facts independently of hints.
Validate approved run/segment references.

Verification creates the linked incident and initial revision.
Rejection creates no incident.

Derive reviewer, decision time and request ID on the server.

Require a valid session, allowed Origin and session-bound CSRF token.
Recheck current account and role permissions in the business transaction.

Reject identified self-review and clocks earlier than report submission.

Increment report version after a successful decision.
Return resulting versions and applicable record references.

Concurrent verification/rejection allows one successful decision
and one version conflict.

## Approved scope and impact

Scope identifies a prepared dated run or ordered stop segment.

Station descriptions do not replace exact impact matching.

Effects are cancellation, restriction and estimated delay.

Cancellation requires whole-run scope.
Restriction and delay may use run or segment scope.

Segment endpoints must belong to the approved run.

Delay requires an explicit integer estimate from 1 to 1440 minutes
and a stated evidence basis.

This is a pilot validation bound, not a railway prediction.
Do not infer an approved delay from unverified narrative.

Require aware effective timestamps with end after start.
Normalize storage to UTC; display passenger times in Asia/Colombo.

The intended effect interval is:

effective_from <= timestamp < effective_until

Actual matching and journey effects belong to the disruption feature.

## Amendments

An authorized amendment directly approves complete replacement facts.
There is no separate draft-revision approval queue.

Each revision records verification actor, time, reason and evidence basis.

Amendments require expected incident version and incidents.edit.
Lock and refresh the incident before changing it.

Only active incidents can be amended.
Reject stale versions and changes to resolved incidents.

Create a new immutable revision.
Increment incident version and current revision number.
Preserve previous revisions and originating report review version.

Require authentication, allowed Origin and session-bound CSRF token.
Recheck current account and role permissions in the transaction.

## Resolution

Resolution requires expected incident version and incidents.resolve.

Only active incidents can be resolved.
No reopening workflow is implemented.

Record actor, reason, decision time and effective resolution time.

Decision time and operational effective time are separate.

Effective resolution cannot be later than the decision clock or earlier
than the current revision's effective start.
Backdating within these bounds is permitted.

Reject decision clocks earlier than incident creation/current verification.

Resolution increments incident version without replacing the revision.

Preserve previous facts and audit history.

The disruption feature must later end applicable effects at the effective
resolution time. Recording resolution does not implement that calculation.

## Transactions

Application services own business transactions.
Repositories use the supplied session and do not independently commit.

Verification atomically writes decision, incident, revision and audit.
Rejection atomically writes decision and audit without an incident.
Amendment atomically writes revision, incident changes and audit.
Resolution atomically writes lifecycle state and audit.

Audit insertion failure rolls back the associated business operation.

Authentication transactions remain separate.
A business failure does not imply authentication activity was rolled back.

Submission counters are also committed separately from report creation.

## Immutable history

Audit and revision storage have no ordinary update or delete operation.

Migration-installed database triggers reject updates, deletes and truncation.
Transaction rollback remains supported.

These protections apply to ordinary database writes.
Privileged administration and schema changes require operational controls.

## Protected audit history

Expose:

GET /api/v1/staff/reports/{report_id}/audit

Require audit.read in the dependency and current-staff service policy.

Return explicit event fields:

- Event, report, incident and revision references.
- Actor, action and reason.
- Request ID and resulting versions.
- Occurrence time.

These are private management fields.

Include rejected-report history even without an incident.
Pending reports may have empty history.
Missing reports return 404.

Order by occurrence time and event ID.
Event ID breaks ties for pagination; it is not causal ordering
when timestamps are equal.

Default limit/offset are 20/0.
Bounds are limit 1–100 and offset 0–10000.

Successful responses use Cache-Control: no-store.
Reads do not change incident/report business state.
Authentication may independently update session activity.

## Public incident responses

Expose:

- GET /api/v1/incidents?run_id={run_id}
- GET /api/v1/incidents/{incident_id}

Select incidents linked to verified reports and their current approved revision.

Return explicit public fields:

- Incident ID and version.
- Revision ID and number.
- Lifecycle status.
- Approved run and scope.
- Approved impact and estimated delay where applicable.
- Effective interval and approved public summary.
- Current revision verification time.
- Effective resolution time.
- Timetable source reference.

Exclude passenger narrative, submitting/reviewing staff identity,
private evidence basis, decision reasons and audit request IDs.

Pending and rejected reports are not public incident evidence.

Run-based listings require run_id and use bounded pagination.
They include approved active and resolved incidents.
Unknown runs return an empty list.
Missing incident details return 404.

Active lifecycle state alone does not establish current applicability.
Effective intervals and resolution must be considered by the disruption feature.

The timetable source reference identifies schedule provenance.
It is not proof of an incident or a live railway update.

Successful public reads use Cache-Control: no-store.

## Frontend contracts

Provide passenger reporting and permission-aware staff management panels.

Passenger forms collect narrative, title and Sri Lanka observation time.
The current form does not expose all optional API scope hints.

Check current staff session before submission and include CSRF when applicable.
Do not automatically retry an uncertain submission.

Staff review uses displayed report version and independently approved facts.
Refresh the queue after confirmed decisions.

Lifecycle forms load the current public approved revision and its incident version.
They do not retrieve private evidence basis.
Amendments require staff to enter a fresh evidence basis.

Refresh after confirmed lifecycle changes.
If the change succeeds but refresh fails, preserve the success message.

After a conflict or uncertain mutation, require reload before another decision.
Do not automatically replay mutations.

Hide controls without the corresponding permission.
The server remains the authorization boundary.

Abort pending requests when panels unmount.
Do not persist credentials or CSRF state in localStorage.

Audit history is visible only to permitted staff and loads on request.

## Journey integration

Preserve original scheduled timestamps.

Represent future estimated timestamps separately with evidence references.

The disruption feature must handle:

- Dated-run and segment matching.
- Effective-time and resolution boundaries.
- Downstream delays.
- Cancellation and restriction eligibility.
- Overlapping-effect rules.
- Feasible alternatives.
- Affected-journey refresh.

At this checkpoint, reports and verified incidents do not change journey results.

## Validation

Validated behavior includes:

- Submission validation, server-owned-field rejection and scope checks.
- Anonymous versus staff-cookie submission.
- Login/report limits remain separate.
- Concurrent admission and transactional cleanup.
- Protected queue pagination and ordering.
- Staff authentication, current permissions and self-review prevention.
- Version conflicts and four review/lifecycle race combinations.
- Atomic decisions and rollback on audit failure.
- Preserved approved revisions.
- Resolution bounds and rejection of further changes.
- Audit allowlists, pagination and permissions.
- Public current-revision selection and private-field exclusion.
- History update/delete/truncate rejection.
- Passenger, review, audit and lifecycle component behavior.
- Cancellation, duplicate prevention and reload after conflicts.
- Full lifecycle and rejection API scenarios, each repeated twice.
- Unchanged scheduled run-stop timestamps across lifecycle changes.

Remaining release/disruption validation includes browser automation,
journey impact boundaries, affected-journey refresh, responsive/accessibility
review and two release demonstrations from reset fixtures.

## Implementation checkpoint

As of 2026-10-18:

- Incident-reporting stages 1–6 implemented and pushed through c36ae1a.
- Stage 6 browser workflow manually verified.
- Backend: 585 tests passed without skips.
- Frontend: 122 tests passed.
- Four repeatable complete API scenario cases passed.
- Stage 7 finalization and branch CI verification remain in progress.
- Checkbox confirmation layout is deferred.
- Journey impact integration remains for the disruption feature.
- No incident-reporting merge into main has been performed.

Concurrency fixtures use temporary schemas built from metadata.
Migration-installed triggers are tested separately.

Repeated API fixtures are not browser automation or release reset-fixture runs.

## Consequences

This requires more records and workflows than a single status table.

It preserves accountable decisions and avoids presenting passenger claims
as verified operational facts.

Anonymous reporting cannot guarantee person-level self-review prevention.

Record UUID lookup is functional but remains a usability limitation.

The pilot is a demonstration and does not publish official railway announcements.
