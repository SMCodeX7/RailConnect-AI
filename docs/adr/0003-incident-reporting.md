# ADR 0003: Incident reports, verified incidents and review

## Status

Accepted

## Context

The v1 handbook distinguishes a passenger report from a verified
operational incident.

A report is an unverified claim. A controller decision establishes
the approved scope, effective period and impact.

The implementation must preserve attribution, review history,
concurrency checks and public evidence boundaries.

## Decision

Implement reporting and review within the incidents module.

Keep separate records for:

- Incident reports: submitted narrative, scope hints and review state.
- Verified incidents: identity, originating report, current revision and lifecycle state.
- Incident revisions: immutable versions of approved operational facts.
- Audit events: actor, action, reason, time, request ID and affected records.

Link a verified incident to its originating report.
Store approved scope and impact in its revisions.

## Identity and permissions

Reuse the staff identity module recorded in ADR 0005.

Use individual staff accounts with expiring, revocable sessions.
Derive actor identity and permissions on the server.

Require these explicit permissions:

- reports.read for the pending queue.
- reports.review for verification and rejection.
- incidents.edit for amendments.
- incidents.resolve for resolution.
- audit.read for audit-history access.

Controllers lack audit.read by default.
Administrators have audit.read under the current role mapping.

A shared reviewer credential does not replace staff identity.

Submitters cannot assign verification status, reviewer identity,
approved impact values or review timestamps.

## Submission and rate limiting

Submission accepts a title, narrative, aware observation time
and optional station, run or segment hints.

Require both segment endpoints when either is supplied.
The arrival stop sequence must follow the departure stop sequence.
Both endpoints must belong to the specified prepared dated run.

Station hints must identify active stations.
When combined with a run or segment, the station must belong to that scope.

Reject future observations and invalid scope references.
Cancelled and restricted runs may still be reported.

Hints remain unverified until staff approval.
Report acceptance does not establish operational impact or journey feasibility.

New reports have server-forced pending status and version 1.
Public input cannot assign submission timestamps or staff identity.

Use separate PostgreSQL counters for passenger submissions.
The default limit is five attempts per client within one hour.

Update counters atomically across workers.
Use the server-observed client address, subject to correct deployment
proxy configuration.

Commit the attempt counter independently of report creation.
Report creation failure must not reset the counter.

Malformed bodies are rejected before the submission service.
They do not consume the service-level counter.

Return 429 with Retry-After when the limit is exceeded.

Anonymous submission is permitted.
Require JSON and an explicitly configured browser Origin.

When a staff cookie is present, require valid authentication and CSRF
protection, and derive submitting staff identity on the server.

An invalid or expired staff cookie must not silently become anonymous access.

Identified staff submitters cannot review their own reports.
This restriction covers recorded staff identity.
Anonymous submission does not establish a person's identity.

Return a pending receipt without narrative or private review fields.

Provide read-only counter cleanup preview and explicit bounded deletion.
Retain expired counters for one day by default.

Select and lock a bounded set of keys before deleting those exact records.
Cleanup preserves current windows, reports and login counters.
Applied cleanup is transactional.

Deployment must arrange an operator procedure or cleanup schedule.

## Protected report queue

Expose a staff-only pending queue with bounded pagination.

Order reports by submission time and report ID, oldest first.
Reading the queue does not change report state.

Require reports.read in the HTTP dependency and application service.
Return explicitly selected staff-review fields.

The queue may include the unverified narrative for authorized review.
It is not a public incident response.

Prevent caching of successful queue responses.

## Report review

A controller may verify or reject a pending report with a reason.

Verification creates the linked incident and initial approved revision.
Rejection records the decision without creating a verified incident.

Require explicit approved facts when verifying.
Validate approved run and segment references independently of passenger hints.

Store integer versions for concurrency control.
Review requests include the expected report version.

Lock the report and refresh its database state during the review transaction.
Reject stale versions and reports that are no longer pending.

A conflict must not overwrite another controller's decision.
Concurrent verification and rejection permit one successful decision.

Derive review actor, decision time and request ID on the server.

Require a valid session, allowed Origin and session-bound CSRF token
for review mutations.

Check permission in the HTTP dependency and decision service.
Recheck current account and role assignments inside the business transaction.

Reject identified self-review.
Reject a review clock earlier than report submission.

Increment report version after a successful decision.
Return resulting versions and applicable incident/revision references.

Prevent caching of successful decision responses.

## Incident scope and impact

Approved scope identifies an affected dated run or ordered stop segment.

Station references may describe scope but do not replace precise matching.

Supported effects are cancellation, restriction and estimated delay.

Cancellation applies to a whole dated run.
Restriction and delay may apply to a whole run or an ordered segment.

Segment endpoints must belong to the specified dated run.
The approved run must have prepared stops.

An estimated delay requires an explicit controller-entered value
and a stated evidence basis.

Approved delay values are integer minutes between 1 and 1440.
This is a pilot validation bound, not a predicted railway delay.

Do not infer approved delay values from unverified narrative.

Store aware effective start and end times.
Normalize approved timestamps to UTC.
Display passenger times in Asia/Colombo.

The intended effect interval includes its start and excludes its end:

effective_from <= timestamp < effective_until

The end must follow the start.

The disruption feature must apply effects only to matching runs or segments
during the relevant effective interval.

Journey effect calculation remains a subsequent implementation.

## Revisions and resolution

Changes to approved scope or impact create a new revision.

An authorized staff member explicitly approves replacement facts through
the amendment operation. There is no separate draft-revision approval queue
in the current implementation.

Each revision records verification actor, time, reason and evidence basis.

Keep previously approved revisions identifiable.
Do not overwrite historical evidence.

Incident version controls concurrent lifecycle changes.
Revision number identifies the approved operational facts.

Initial verification creates incident version 1 and revision number 1.

Amendment and resolution requests include the expected incident version.
Lock and refresh the incident before checking that version.

Only active incidents may be amended or resolved.
Reject stale versions and changes to resolved incidents with conflicts.
No reopening workflow is implemented.

Amendment creates a new approved revision, increments incident version
and selects the new current revision atomically with its audit event.

Resolution records actor, reason, decision time and effective resolution time.
Decision time and operational effective time are separate fields.

Resolution increments incident version without creating a replacement revision.
It preserves the selected revision and previous audit history.

Neither operation changes the originating report's completed review version.

Require valid authentication, allowed Origin and session-bound CSRF token.
Recheck current staff account and role permissions in the business transaction.

Reject decision clocks earlier than incident creation or current verification.

Resolution effective time cannot be later than the decision clock or earlier
than the current revision's effective start.

Backdating within those bounds is permitted.

The disruption feature must end an incident's effect at its effective
resolution time. Recording resolution does not itself implement journey
effect calculation.

## Transactions

The application service owns each business transaction.

Verification writes report decision, incident, initial revision and audit
atomically. A failure rolls back the complete operation.

Rejection writes report decision and audit atomically.
It must not create an incident.

Amendment and resolution update lifecycle state, versions and audit history
in one transaction.

Audit insertion failure must roll back the associated lifecycle change.

Repositories use the supplied session and do not commit independently.

Keep authentication transactions separate from incident business transactions.
A failed decision does not imply authentication activity was rolled back.

Submission uses separate counter and report transactions.
This preserves submission limits when report creation fails.

## Protected audit history

Expose:

GET /api/v1/staff/reports/{report_id}/audit

Require audit.read in the HTTP dependency and current-staff service policy.

Return explicit event fields:

- Event, report, incident and revision references.
- Authenticated actor.
- Action and reason.
- Request ID.
- Resulting report and incident versions.
- Occurrence time.

These are private management fields, not a public incident contract.

Include rejected-report history even when no incident was created.
A pending report may have empty history.
A missing report returns 404.

Order by occurrence time and event ID.
Event ID provides a stable pagination tie-breaker, not causal ordering
when timestamps are equal.

Use limits from 1 through 100 and offsets from 0 through 10000.
Defaults are limit 20 and offset 0.

Successful responses are non-cacheable.

Reading history does not alter report or incident business state.
Authentication may update session activity independently.

## Public responses

Expose approved public fields only.

Exclude submitter identity, private review notes, verification reasons
and unapproved narrative.

Pending and rejected reports are not public operational evidence.

Return incident and approved revision references with verified disruption
information, together with relevant source references.

A pending receipt confirms receipt only.
It does not claim that a disruption is verified.

Protected queue, decision and audit responses do not replace the planned
public incident responses.

Public incident responses remain a subsequent implementation stage.

## Journey integration

Preserve original scheduled timestamps.

Represent estimated timestamps separately with their evidence basis.

Apply segment delays to relevant downstream stops.
Cancelled runs are not feasible alternatives.

Use a documented rule for overlapping effects rather than blindly
adding reported delays.

Consider resolution and effective-time boundaries when determining
whether an incident affects a journey.

Refresh affected journey views after verification, edits and resolution.

Implement journey impact calculation in the subsequent disruption feature.

At this checkpoint, neither unverified reports nor verified incident records
change journey-result calculations.

## Module boundaries

Separate models, schemas, repositories, services, policies and routes.

Staff authentication belongs to the identity module.
Journey impact calculation uses an explicit application interface.

Audit storage has no ordinary application update or delete operation.

Database triggers reject updates, deletes and truncation of incident
revisions and audit events. Transaction rollback remains supported.

Create additional files only when their responsibilities are implemented.

## Validation

Implemented validation covers:

- Submission rejects server-owned review and approval fields.
- Observation timestamps require a timezone and cannot be in the future.
- Invalid run, station and segment hints are rejected.
- Cancelled and restricted runs can still be reported.
- Identified staff submitters cannot review their own reports.
- Missing, expired or revoked sessions are denied on protected operations.
- Staff without required permission are denied.
- Disabled accounts and removed reviewer roles cannot use earlier snapshots.
- Staff-cookie submissions and mutations require CSRF protection.
- Missing or untrusted browser origins are rejected.
- Report limits remain separate from login limits.
- Concurrent submissions respect the configured admission limit.
- Failed report creation preserves committed attempt counters.
- Cleanup preserves current windows and obeys its batch limit.
- Cleanup changes roll back with the caller's transaction.
- The queue returns pending reports with bounded pagination and stable ordering.
- Queue reads do not change report state.
- Concurrent review permits one decision and one version conflict.
- Failed verification/rejection leaves no partial business decision or audit.
- Audit events use authenticated actors and server-generated request IDs.
- Amendments create new revisions and preserve earlier facts.
- Resolution preserves the approved revision and records its effective time.
- Invalid lifecycle timestamps and scope references are rejected.
- Resolved incidents reject further lifecycle changes.
- Audit failure rolls back amendment and resolution.
- Lifecycle races permit one successful change and one conflict.
- Audit access requires audit.read.
- Audit pagination, response fields and missing-report behavior are tested.
- Revision/audit updates, deletes and truncation are rejected.

Remaining public-response and disruption validation includes:

- Public responses omit private fields.
- Pending and rejected claims never become public operational evidence.
- Off-route and out-of-window incidents have no journey effect.
- Resolution ends journey effects at the effective resolution time.
- Journey views refresh after operational changes.

These remaining items are requirements, not claims of completed integration.

## Implementation checkpoint

As of 2026-10-18:

- Database models, constraints and immutable-history protections are validated.
- Passenger submission, separate rate limits and cleanup are implemented.
- Protected queue and verify/reject endpoints are implemented.
- Amendments and resolution are implemented with transactional audit writes.
- Protected report audit history is implemented.
- Review and lifecycle expected-version conflicts are validated.
- Audit failures roll back the associated business operations.
- Four review/lifecycle concurrency cases are validated.
- Complete backend suite: 566 passed without skips.
- Stage 3 is committed locally as 71bc123.
- Stage 4 checkpoint commit remains pending.
- Public incident responses and passenger/staff interfaces remain pending.
- Journey disruption integration belongs to the subsequent feature.
- Latest branch GitHub CI has not yet been verified.

Concurrency tests use independent transactions in temporary schemas created
from model metadata and remove those schemas afterward.

Migration-installed history triggers are tested separately.

Acceptance of this decision does not mean every workflow is implemented.

## Consequences

This requires more records and workflow code than a single status table.

It preserves accountable decisions and supports disruption handling
without treating passenger claims as verified facts.

Anonymous reporting does not establish submitter identity.
Person-level self-review prevention cannot be guaranteed for reports
without recorded identity.

Database immutability protects ordinary application writes.
Privileged administration and schema changes require separate controls.

The pilot remains a demonstration and does not publish official
railway announcements.
