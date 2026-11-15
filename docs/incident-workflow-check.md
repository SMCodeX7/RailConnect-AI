# Synthetic incident workflow verification

Use a local development database and fictional claims. Follow [setup](setup.md)
to start both services and provision a controller and an administrator.

```powershell
python scripts/materialize_demo_runs.py --start-date 2026-10-19 --end-date 2026-10-19
```

Search Jaffna to Colombo Fort on 2026-10-19. Demo Northern Return is scheduled
07:00–16:00 Asia/Colombo. Open journey details and copy the actual `run_id`
from the browser Network request `/api/v1/journeys/{run_id}`.

## Lifecycle

1. While signed out, submit a fictional disruption report with a recent
   observation time. Save its `report_id`.
2. As controller, verify the report using the prepared `run_id`, whole-run
   scope, a 15-minute delay, a public summary, private evidence and a reason.
   Use an effective start in the past and an end after the start. Confirm
   independent review and save the resulting `incident_id`.
3. Load the incident and amend the delay to 30 minutes. Supply an updated
   summary, fresh private evidence and a reason. Confirm independent review.
4. Resolve with a reason and an effective time at or after the revision start
   and no later than now. The browser form uses Asia/Colombo.
5. Verify that the controller has no private audit panel. As administrator,
   look up the audit using `report_id` and check the actions, actor, reasons,
   revision references and request IDs.
6. Sign out and open `/api/v1/incidents?run_id=YOUR_RUN_UUID` on port 8000.
   Confirm resolved status and approved public facts. Private narrative,
   evidence, reasons and staff identities must be absent.

| Action | Incident version | Approved revision |
| --- | ---: | ---: |
| Verify | 1 | 1 |
| Amend | 2 | 2 |
| Resolve | 3 | 2 |

A resolved record can retain historical delay facts. The journey's scheduled
timestamps remain unchanged.

## Rejection

Submit a second fictional report while signed out. Reject it as controller
with a reason. Check that it leaves the pending queue. As administrator,
verify that its audit has one rejection event and no incident or revision
reference.

Use fresh reports for repeats. After an uncertain result, reload before
retrying. Recover the report ID from its receipt and the incident ID from
the run-filtered public list.

## Automated replay

```powershell
python -m pytest -c backend/pyproject.toml backend/tests/test_report_review_api.py -k "repeatable_synthetic" -x --tb=short
```

Four API cases repeat lifecycle and rejection with isolated fixtures. They
check revisions, audit references, private fields and scheduled timestamps.
The incident browser checkpoint was completed on 2026-10-18. The two release
demonstrations from reset fixtures remain a v1 requirement.
