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
- Verified incidents: approved scope, effective period and impact.
- Incident revisions: immutable versions of approved operational facts.
- Audit events: actor, action, reason, time, request ID and affected records.

Link a verified incident to its originating report.

## Identity and permissions

Implement staff identity before protected incident review.

Use individual staff accounts with expiring, revocable sessions.
Derive actor identity and permissions on the server.

Require explicit permissions for reviewing reports, editing incidents,
resolving incidents and reading audit records.

A shared reviewer credential does not replace staff identity.

Public report submission is rate limited.
Submitters cannot assign verification status, reviewer identity,
approved impact values or review timestamps.

## Report review

New reports are pending.

A controller may verify or reject a pending report with a reason.
Verification creates the linked incident and its initial revision.

Store an integer version for concurrency control.
Review requests include the expected version.

A stale version returns a conflict rather than overwriting another
controller's decision.

## Incident scope and impact

Approved scope identifies the affected dated service run or ordered
stop segment. Station references may help describe the scope but do
not replace precise impact matching.

Supported effects include cancellation, restriction and estimated delay.

An estimated delay requires an explicit controller-entered value
and a stated basis. Do not infer a delay from an unverified narrative.

Store timezone-aware effective start and end times.
Display passenger times in Asia/Colombo.

Apply effects only to matching runs or segments during the relevant
effective interval.

## Revisions and resolution

Changes to approved scope or impact create a new revision and require
verification before becoming public operational evidence.

Keep the previously verified revision identifiable.
Do not overwrite historical evidence.

Resolution records the actor, reason and effective resolution time.
It ends the incident's effect while preserving its history.

## Transactions

The application service owns the review transaction.

Write the report decision, incident, revision and audit event atomically.
A failure rolls back the complete operation.

Repositories use the supplied session and do not commit independently.

## Public responses

Expose only approved public fields.

Exclude submitter identity, private review notes and unapproved narrative.
Pending and rejected reports are not public operational evidence.

Return source and revision references with verified disruption information.

## Journey integration

Preserve original scheduled timestamps.

Represent estimated timestamps separately with their basis.

Apply segment delays to relevant downstream stops.
Cancelled runs are not feasible alternatives.

Use a documented rule for overlapping effects rather than blindly
adding reported delays.

Refresh affected journey views after verification, edits and resolution.

## Module boundaries

Separate models, schemas, repositories, services, policies and routes.

Staff authentication belongs to the identity module.
Journey impact calculation uses an explicit application interface.
Audit storage has no ordinary application update or delete operation.

Create additional files only when their responsibilities are implemented.

## Validation

Cover:

- Pending reports cannot affect public journeys.
- Submitters cannot verify their own reports.
- Missing, expired or revoked sessions are denied.
- Staff without the required permission are denied.
- Concurrent review attempts produce a version conflict.
- Failed review transactions leave no partial incident or audit record.
- Off-route and out-of-window incidents have no effect.
- Resolution ends the effect and preserves history.
- Public responses omit private fields.

## Consequences

This requires more records and workflow code than a single status table.

It preserves accountable decisions and supports future disruption
handling without treating passenger claims as verified facts.

The pilot remains a demonstration and does not publish official
railway announcements.
