# Synthetic incident workflow verification

## Purpose

Replay the incident-reporting workflow against a local development system.

All reports, approved estimates and reasons in this procedure are synthetic.
They are not official railway information.

This document complements automated tests.
It is not browser automation or a production operating procedure.

## Preconditions

Follow docs/setup.md.

Required:

- Development/test database with migrations applied.
- Demonstration stations, timetable and dated runs.
- Backend running at http://127.0.0.1:8000.
- Frontend running at http://127.0.0.1:5173.
- Individually provisioned controller and administrator accounts.
- Privately saved passwords.

Do not reuse a production database for tests.

## References

Keep these identifiers distinct:

| Reference | Meaning |
| --- | --- |
| run_id | Prepared dated train service |
| report_id | Passenger claim and audit lookup |
| incident_id | Verified incident and lifecycle lookup |
| revision_id | Approved fact version |
| request_id | HTTP/audit request reference |

Use references returned by the current environment.
Do not assume UUIDs from another database will work.

## Prepare a journey

Materialize the intended date:

```powershell
python scripts/materialize_demo_runs.py --start-date 2026-10-19 --end-date 2026-10-19
```

Use another valid date when appropriate.

In Journey search, choose a covered station pair and the prepared date.
Leave arrival deadline empty for the initial check.

The validated example was:

- Jaffna to Colombo Fort.
- Travel/service date: 2026-10-19.
- Demo Northern Return.
- Scheduled departure: 07:00 Asia/Colombo.
- Scheduled arrival: 16:00 Asia/Colombo.
- Stops: Jaffna, Vavuniya, Anuradhapura, Colombo Fort.

Check ordered details, selected segment and permissions.

## Obtain run_id

Open browser developer tools before opening journey details.

Under Network, inspect the journey detail request:

```text
/api/v1/journeys/{actual-run-uuid}
```

Copy the actual run UUID.

Alternatively inspect the journey search JSON or the backend access-log URL.

The structured route value `/journeys/{run_id}` is a template,
not the actual UUID. The log request_id is also not the run ID.

## Scenario A: lifecycle

### Submit anonymously

Sign out through Staff access.

Open Report a disruption and enter:

- Title: Synthetic lifecycle workflow check.
- Narrative: Fictional observation created for portfolio workflow testing.
  No real railway incident is asserted.
- Observation: a few minutes before the current Sri Lanka time.

Submit once.

Expected:

- Pending receipt.
- Report reference.
- Submission time.
- Explicit wording that receipt does not establish verification.

Save report_id.

### Verify as controller

Sign in as controller.
Load pending reports and open the new report.

Select Verify approved incident.

Enter:

- Decision reason describing controlled synthetic evidence.
- Prepared run_id.
- Whole-run scope.
- Delay impact.
- Estimated delay: 15 minutes.
- A valid effective interval.
- Explicitly synthetic public summary.
- Private basis identifying the controlled demonstration.

For a same-day resolution check, ensure effective start is not in the future.
Choose an end after start. If testing a future run, the synthetic interval
may span the current time and that scheduled run.

Use the actual current date/time rather than blindly copying old timestamps.

Confirm independent review and verify once.

Expected:

- Success and incident_id.
- Automatic pending queue refresh.
- Report removed from pending results.
- Incident version 1 and revision 1.

Save incident_id.

### Amend

Load incident_id under Manage a verified incident.

Select Amend approved facts.

Keep run/scope/interval unless deliberately testing another valid scope.
Set:

- Delay: 30 minutes.
- Updated synthetic public summary.
- Nonempty amendment reason.
- Fresh private evidence basis.
- Independent-review confirmation.

Save once.

Expected after refresh:

- Active status.
- Incident version 2.
- Approved revision 2.
- New approved facts.

Earlier revision remains preserved in storage.

### Resolve

Select Resolve incident.

Enter a nonempty synthetic resolution reason.
Choose effective resolution time after the current revision's effective start
and not later than the current time.

Confirm once.

Expected:

- Resolved status.
- Incident version 3.
- Approved revision 2.
- Effective resolution displayed.
- Further lifecycle changes unavailable.

Resolution does not replace the approved revision.

### Audit as administrator

Confirm controller does not see Private report audit history.

Sign out and sign in as administrator.
Load audit history using report_id.

Expected:

| Action | Incident version |
| --- | ---: |
| Report verified | 1 |
| Incident amended | 2 |
| Incident resolved | 3 |

Check actor, reasons, revision references and request references.

Rows with equal timestamps have a stable ID tie-breaker.
Interpret lifecycle order using versions and references.

### Check public response

Sign out.

Open:

```text
http://127.0.0.1:8000/api/v1/incidents?run_id=YOUR_RUN_UUID
```

Locate the synthetic incident.

Expected:

- Resolved status.
- Incident version 3.
- Revision number 2.
- Approved delay retained as historical facts.
- Effective resolution time.
- No narrative, private evidence basis, decision reasons or staff identities.

A resolved record does not establish a currently active delay.

## Scenario B: rejection

While signed out, submit a separately labelled synthetic rejection report.
Save its report_id.

Sign in as controller.
Load the queue, open the report and choose Reject report.
Enter a reason identifying insufficient synthetic evidence.

Expected:

- Confirmed rejection.
- Removal from pending queue.
- No linked incident.

As administrator, load the rejected report's audit.

Expected:

- One Report rejected event.
- Incident ID/version and revision ID: Not applicable.

Rejected narrative must not appear as public incident evidence.

## Time handling

All form dates/times in these workflows mean Asia/Colombo.
The frontend converts them to UTC.

For reference:

- 17:30 Asia/Colombo equals 12:00Z.
- 17:55 Asia/Colombo equals 12:25Z.

Resolution effective time and decision time are separate.
Supported backdating may make effective time earlier than the decision clock.

## Recovery and repeatability

If a receipt or success reference was missed:

- Recover incident_id from the public run-filtered incident listing.
- Use the original report receipt for report_id.
- Do not submit another report merely to recover a reference.

If a mutation result is uncertain, reload before retrying.
Do not automatically replay decisions.

For another browser run, submit fresh uniquely titled synthetic reports.
New report/incident IDs are expected.
Do not erase immutable history to repeat the workflow.

Default report admission is five attempts per client per hour.
Respect Retry-After if limited.

Two browser repetitions from a reset release fixture remain a separate
release verification requirement.

## Automated repeated API scenarios

From the repository root with PostgreSQL running:

```powershell
python -m pytest -c backend/pyproject.toml backend/tests/test_report_review_api.py -k "repeatable_synthetic" -x --tb=short
```

Expected at this checkpoint: four selected cases.

Each lifecycle/rejection scenario is parameterized twice with fresh,
rollback-isolated fixtures.

Checks include versions, audit references, revision preservation,
private-field exclusion and unchanged scheduled timestamps.

Run the full suite:

```powershell
python -m pytest -c backend/pyproject.toml --tb=short
```

Checkpoint: 585 passed.

Concurrency cases use independent temporary-schema transactions.
Migration history protections are tested separately.

## Recorded manual checkpoint

Completed on 2026-10-18:

- Startup and database health.
- Jaffna to Colombo Fort search/details for 2026-10-19.
- Anonymous pending receipt.
- Controller verification.
- Amendment from 15 to 30 synthetic minutes.
- Resolution at version 3 with revision 2 retained.
- Administrator lifecycle audit.
- Controller audit panel restriction.
- Separate rejection and rejection audit.
- Signed-out approved public response.

The manual check was against the local development environment.
It does not establish deployed behavior or CI success.

## Deferred issues and boundaries

- Checkbox confirmation layout requires later UI correction.
- Responsive/accessibility release review remains outstanding.
- Staff record lookup currently uses UUIDs.
- Audit panels refresh on request.
- Approved incident effects are not connected to journey calculations.
- Scheduled times remain unchanged.
- No official railway information is asserted.
