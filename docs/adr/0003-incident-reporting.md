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

Staff identity is implemented and merged into main through ADR 0005.
Reuse that module for authenticated actors, sessions and permissions.

Use individual staff accounts with expiring, revocable sessions.
Derive actor identity and permissions on the server.

Require explicit permissions for reading and reviewing reports,
editing incidents, resolving incidents and reading audit records.

Queue access requires reports.read.
Verification and rejection require reports.review.

A shared reviewer credential does not replace staff identity.

Submitters cannot assign verification status, reviewer identity,
approved impact values or review timestamps.

## Submission and rate limiting

Submission accepts a title, narrative, timezone-aware observation time
and optional station, run or segment hints.

Require both segment endpoints when either is supplied.
The arrival stop sequence must follow the departure stop sequence.
Both endpoints must belong to the specified prepared dated run.

Station hints must identify active stations.
When combined with a run or segment, the station must belong to that scope.

Reject future observation times and invalid scope references.
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

Malformed request bodies are rejected before the submission service.
These requests do not consume the service-level counter.

Return 429 with Retry-After when the submission limit is exceeded.

Anonymous submission is permitted.
Require JSON and an explicitly configured browser Origin.

When a staff cookie is present, require valid authentication and CSRF
protection, and derive the submitting staff identity on the server.

An invalid or expired staff cookie must not silently fall back
to anonymous access.

Identified staff submitters cannot review their own reports.
This restriction covers recorded staff identity.
Anonymous submission does not establish a person's identity.

Return a pending receipt without narrative or private review fields.

Provide read-only counter cleanup preview and explicit bounded deletion.
Retain expired counters for one day by default.

Select and lock a bounded set of keys before deleting those exact records.
Cleanup preserves current windows and does not delete reports or login counters.
Applied cleanup is transactional.

Deployment must arrange an operator procedure or cleanup schedule.

## Protected report queue

Expose a staff-only pending-report queue with bounded pagination.

Order reports by submission time and report ID, oldest first.
Reading the queue does not change report state.

Require reports.read in both the HTTP dependency and application service.
Return only explicitly selected staff-review fields.

The queue may include the unverified narrative for authorized review.
It is not a public incident response.

Prevent caching of successful queue responses.

## Report review

A controller may verify or reject a pending report with a reason.

Verification creates the linked incident and its initial approved revision.
Rejection records the decision without creating a verified incident.

Require explicit approved facts when verifying.
Validate the approved run and segment independently of passenger hints.

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
Recheck the current account and role assignments inside the business transaction.

Reject identified self-review.
Reject a review clock earlier than report submission.

Increment the report version after a successful decision.
Return the resulting report version and applicable incident/revision references.

Prevent caching of successful decision responses.

## Incident scope and impact

Approved scope identifies the affected dated service run or ordered
stop segment.

Station references may help describe the scope but do not replace
precise impact matching.

Supported effects include cancellation, restriction and estimated delay.

Cancellation applies to a whole dated run.
Restriction and delay may apply to a whole run or an ordered segment.

Segment endpoints must belong to the specified dated run.
The approved run must have prepared stops.

An estimated delay requires an explicit controller-entered value
and a stated evidence basis.

Approved delay values are integer minutes between 1 and 1440.
This is a pilot validation bound, not a predicted railway delay.

Do not infer an approved delay from an unverified narrative.

Store timezone-aware effective start and end times.
Normalize approved timestamps to UTC when storing them.
Display passenger times in Asia/Colombo.

Effective intervals include their start and exclude their end:

effective_from <= timestamp < effective_until

The effective end must follow the effective start.

Apply effects only to matching runs or segments during the relevant
effective interval.

Journey effect calculation remains a subsequent implementation.

## Revisions and resolution

Changes to approved scope or impact create a new revision and require
staff verification before becoming public operational evidence.

Each revision records its verification actor, time, reason and evidence basis.

Keep the previously verified revision identifiable.
Do not overwrite historical evidence.

Incident version controls concurrent lifecycle changes.
Revision number identifies the approved operational facts.

Initial verification creates incident version 1 and revision number 1.

Amendment requests include the expected incident version.
Selecting the new approved revision and recording its audit event
must occur atomically.

Resolution records the actor, reason, decision time and effective resolution time.

The recorded decision time and operational effective time are separate fields.

Resolution ends the incident's effect at the effective resolution time
while preserving its approved revisions and audit history.

Resolution requests include the expected incident version.

Amendment and resolution workflows remain pending after the initial
verification/rejection implementation.

## Transactions

The application service owns the review transaction.

Write the report decision, incident, initial revision and audit event atomically.
A failure rolls back the complete operation.

Rejection writes its report decision and audit event atomically.
It must not create an incident.

Incident amendments and resolution must also update lifecycle state,
versions and audit history in one transaction.

Repositories use the supplied session and do not commit independently.

Keep authentication transactions separate from incident business transactions.
A failed business decision does not imply authentication activity was rolled back.

Report submission uses separate counter and report transactions.
This preserves submission limits when report creation fails.

## Public responses

Expose only approved public fields.

Exclude submitter identity, private review notes, verification reasons
and unapproved narrative.

Pending and rejected reports are not public operational evidence.

Return incident and approved revision references with verified
disruption information, together with relevant source references.

A pending submission receipt confirms receipt only.
It does not claim that the reported disruption is verified.

Staff queue and decision responses are protected management contracts.
They do not replace the planned public incident responses.

## Journey integration

Preserve original scheduled timestamps.

Represent estimated timestamps separately with their evidence basis.

Apply segment delays to relevant downstream stops.
Cancelled runs are not feasible alternatives.

Use a documented rule for overlapping effects rather than blindly
adding reported delays.

Resolution and effective-time boundaries must be considered when
determining whether an incident still affects a journey.

Refresh affected journey views after verification, edits and resolution.

Implement journey impact calculation in the subsequent disruption feature.
Unverified report submission must not change journey results.

At the current checkpoint, verified incident records also remain
separate from journey-result calculations.

## Module boundaries

Separate models, schemas, repositories, services, policies and routes.

Staff authentication belongs to the identity module.
Journey impact calculation uses an explicit application interface.

Audit storage has no ordinary application update or delete operation.

Database triggers reject updates, deletes and truncation of incident
revisions and audit events. Transaction rollback remains supported.

Create additional files only when their responsibilities are implemented.

## Validation

Cover:

- Pending reports cannot affect public journeys.
- Submission rejects server-owned review and approval fields.
- Observation timestamps require a timezone and cannot be in the future.
- Invalid run, station and segment hints are rejected.
- Cancelled and restricted runs can still be reported.
- Identified staff submitters cannot review their own reports.
- Missing, expired or revoked sessions are denied on protected operations.
- Staff without the required permission are denied.
- Disabled accounts and removed reviewer roles cannot use earlier actor snapshots.
- Staff-cookie submissions and review mutations require CSRF protection.
- Missing or untrusted browser origins are rejected.
- Report limits remain separate from staff-login limits.
- Concurrent submissions do not exceed the configured admission limit.
- Failed report creation preserves its committed attempt counter.
- Cleanup preserves current windows and obeys its batch limit.
- Cleanup changes roll back with the caller's transaction.
- The queue returns pending reports with stable ordering and bounded pagination.
- Queue reads do not change report state.
- Concurrent review attempts produce one decision and one version conflict.
- Failed verification leaves no partial decision, incident, revision or audit event.
- Failed rejection leaves no partial decision or audit event.
- Audit events use the authenticated actor and server-generated request ID.
- Amendments create new revisions rather than overwrite previous facts.
- Revision and audit updates, deletes and truncation are rejected.
- Off-route and out-of-window incidents have no effect.
- Resolution ends the effect and preserves history.
- Public responses omit private fields.

Some validation items concern planned lifecycle and disruption features.
Their presence here does not claim they have already been implemented.

## Implementation checkpoint

As of 2026-10-18:

- Report, incident, revision and audit database models are implemented.
- Database constraints and immutable-history protections are validated.
- Passenger submission, separate rate limits and counter cleanup are implemented.
- Protected pending queue and verify/reject endpoints are implemented.
- Verification and rejection produce transactional audit records.
- Current reviewer permissions and identified self-review are checked.
- Expected-version conflicts and simultaneous review are validated.
- Audit insertion failures roll back verification and rejection.
- Complete backend suite: 512 passed without skips.
- Amendment, resolution and their lifecycle audit writes remain pending.
- Public incident responses and passenger/staff interfaces remain pending.
- Journey disruption integration belongs to the subsequent feature.
- Stage 3 documentation and commit remain pending.
- GitHub CI for the latest branch changes has not yet been verified.

The review concurrency test uses independent transactions in a temporary
schema created from model metadata and removes that schema afterward.
Migration-installed history triggers are tested separately.

Acceptance of this decision does not mean every workflow is implemented.

## Consequences

This requires more records and workflow code than a single status table.

It preserves accountable decisions and supports future disruption
handling without treating passenger claims as verified facts.

Anonymous reporting does not establish submitter identity.
The system cannot guarantee person-level self-review prevention
for submissions without recorded identity.

Database immutability protects ordinary application writes.
Privileged database administration and schema changes require
separate operational controls.

The pilot remains a demonstration and does not publish official
railway announcements.
