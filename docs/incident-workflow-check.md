# Synthetic incident workflow verification

Use a local demonstration database and fictional observations. Follow the
[setup guide](setup.md) to start both services and provision a controller and
an administrator. For a release rehearsal, start from reset demo fixtures
so an earlier synthetic delay cannot affect the expected results.

## Prepare the demo journey

From the repository root with the backend environment active:

```powershell
python scripts/materialize_demo_runs.py --start-date 2026-11-16 --end-date 2026-11-16
```

In **Journey search**, select **Jaffna → Colombo Fort** for **16 November
2026**. **Demo Northern Return** is scheduled to depart at **07:00** and
arrive at **16:00** in Sri Lanka time.

To find the dated run ID without opening DevTools, run this in PowerShell
while the backend is running:

```powershell
$apiBase = 'http://127.0.0.1:8000/api/v1'
$stations = (Invoke-RestMethod "$apiBase/stations?limit=100").items
$departure = ($stations | Where-Object { $_.name -eq 'Jaffna' }).id
$arrival = ($stations | Where-Object { $_.name -eq 'Colombo Fort' }).id

$journeys = Invoke-RestMethod "$apiBase/journeys?departure_station_id=$departure&arrival_station_id=$arrival&travel_date=2026-11-16"
$journeys.items |
    Where-Object { $_.service_name -eq 'Demo Northern Return' } |
    Select-Object service_name, run_id
```

Copy the `run_id` from the result. Keep the staff and passenger views in
separate browser sessions if you want to refresh the passenger view while
signed in as staff.

## Submit and verify

1. While signed out, open **Report a disruption**. Use the title
   `Synthetic release demo - delayed train` and the description
   `Fictional observation for the release rehearsal. Demo Northern Return
   departed Jaffna 15 minutes after its scheduled time in this test scenario.`
   Enter an observation time five minutes before the current Sri Lanka time.
2. Click **Submit report**. Confirm the receipt shows **Pending** and save
   the report reference as `report_id`.
3. Sign in as a controller. Load pending reports, open the report you just
   submitted, and choose the verification decision.
4. Enter the approved facts below. Tick the independent review checkbox and
   click **Verify report** once.

| Field | Sample value |
| --- | --- |
| Approved dated run ID | The `run_id` obtained from journey search |
| Approved scope | Whole run |
| Approved impact | Delay |
| Approved estimated delay | `15` minutes |
| Effective start | `16 November 2026, 06:00` |
| Effective end | `16 November 2026, 17:00` |
| Approved public summary | `Synthetic 15-minute delay for the RailConnect release rehearsal.` |
| Private evidence basis | `Controlled demo fixture for staff review and journey refresh.` |
| Decision reason | `Verify the delay specified by the synthetic release fixture.` |

Enter the effective times in Sri Lanka time. Save the incident reference as
`incident_id`. If needed, use the public list from PowerShell to find the
incident by its synthetic public summary:

```powershell
$runId = 'PASTE_RUN_ID_HERE'
(Invoke-RestMethod "$apiBase/incidents?run_id=$runId").items |
    Select-Object incident_id, status, public_summary
```

Refresh **Journey results** or **Journey details**. On reset fixtures, the
scheduled arrival should still be **16:00**, with an estimated arrival of
**16:15**.

## Amend and resolve

1. In **Manage a verified incident**, enter the `incident_id` and click
   **Load current incident**.
2. Choose **Amend approved facts**. Keep the same run, whole-run scope,
   delay impact, and effective window. Change the delay to `30` minutes.
   Use the public summary `Synthetic delay estimate revised to 30 minutes.`,
   the private evidence `Controlled demo fixture for amendment verification.`,
   and the reason `Update the delay specified by the synthetic release fixture.`
   Confirm independent review and click **Save approved amendment**.
3. Refresh the passenger journey. On reset fixtures, expect scheduled arrival
   **16:00** and estimated arrival **16:30**.
4. Load the current incident again and select **Resolve incident**. Use the
   reason `Complete the synthetic incident lifecycle rehearsal.` Enter a
   resolution time at or after the revision start and no later than the
   current time, then submit the resolution.
5. While signed out, open `/api/v1/incidents?run_id=YOUR_RUN_UUID` on port
   `8000`. Confirm the incident is resolved and that the public response
   shows approved facts. Check that private narrative, evidence, decision
   reasons, and staff identities are absent.

| Action | Incident version | Approved revision |
| --- | ---: | ---: |
| Verify | 1 | 1 |
| Amend | 2 | 2 |
| Resolve | 3 | 2 |

A resolved record can retain historical delay facts. The journey retains
its scheduled timestamps throughout the workflow.

## Audit and rejection

- Confirm the controller cannot access private audit history. Sign in as
  administrator, look up the audit using `report_id`, and check the actions,
  actor, reasons, revision references, and request IDs.
- While signed out, submit a second fictional report titled
  `Synthetic release demo - rejection check`. Use the description
  `Fictional report for checking rejection and the staff audit trail.`
  Enter a recent observation time in Sri Lanka time.
- As controller, reject it with the reason
  `Synthetic report submitted to test rejection. No disruption to publish.`
  Confirm it leaves the pending queue.
- As administrator, look up the second report's audit. Expect one rejection
  event with no incident or revision reference.

Use fresh reports for each rehearsal. If a submission or decision has an
uncertain result, reload the relevant view and check its state before retrying.

## Automated replay

Run the focused API scenarios from the repository root:

```powershell
python -m pytest -c backend/pyproject.toml backend/tests/test_report_review_api.py -k "repeatable_synthetic" -x --tb=short
```

The four isolated API cases check lifecycle and rejection, revision and audit
references, private fields, and scheduled timestamps. The
[Playwright suite](setup.md#browser-tests) also verifies a controller-approved
delay and refreshes the existing passenger journey.

Record the date, commit, and outcome of each release rehearsal. The two
demonstrations from reset fixtures remain a release requirement.
