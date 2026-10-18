# Development setup

## Prerequisites

- Git
- Python 3.13
- Node.js 22.20.0
- Docker Desktop with Linux containers
- PowerShell on Windows

Run commands from the repository root unless another directory is specified.

## Install uv

Install uv outside the project environment:

```powershell
python -m venv "$env:LOCALAPPDATA\RailConnectTools\uv"
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\python.exe" -m pip install "uv==0.13.0"
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" --version
```

## Backend installation

For a fresh checkout:

```powershell
python -m venv --prompt RailConnect-AI backend\.venv
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" sync --project backend --extra dev --locked
.\backend\.venv\Scripts\Activate.ps1
```

Sync installs the backend package in editable mode.
Stop the backend before syncing dependencies on Windows.

In VS Code, select `backend\.venv\Scripts\python.exe`
through Python: Select Interpreter.

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\backend\.venv\Scripts\Activate.ps1
```

Activate the environment in each terminal used for backend commands.

## Local configuration

Create configuration once for a fresh checkout:

```powershell
Copy-Item .env.example .env
```

Do not overwrite an existing configured file.

Generate a password:

```powershell
python -c "import secrets; print(secrets.token_hex(24))"
```

Assign it to POSTGRES_PASSWORD in `.env`.

Keep:

```dotenv
RAILCONNECT_DATABASE_URL=postgresql+psycopg://railconnect:${POSTGRES_PASSWORD}@127.0.0.1:5433/railconnect
```

Local development settings:

```dotenv
RAILCONNECT_APP_NAME="RailConnect AI"
RAILCONNECT_ENVIRONMENT=development
RAILCONNECT_DEBUG=false
RAILCONNECT_SESSION_COOKIE_NAME=railconnect_session
RAILCONNECT_SESSION_COOKIE_SECURE=false
RAILCONNECT_SESSION_TTL_SECONDS=28800
RAILCONNECT_SESSION_IDLE_TIMEOUT_SECONDS=1800
RAILCONNECT_TRUSTED_ORIGINS='["http://127.0.0.1:5173","http://localhost:5173"]'
RAILCONNECT_LOGIN_RATE_WINDOW_SECONDS=300
RAILCONNECT_LOGIN_CLIENT_MAX_ATTEMPTS=30
RAILCONNECT_LOGIN_ACCOUNT_MAX_ATTEMPTS=5
RAILCONNECT_REPORT_RATE_WINDOW_SECONDS=3600
RAILCONNECT_REPORT_CLIENT_MAX_ATTEMPTS=5
```

Keep the same non-secret names in `.env.example`.
Leave its password blank.
Actual passwords belong only in ignored local configuration.

Environment variables override `.env`.
Run backend commands from the repository root.
Restart the backend after configuration changes.

PostgreSQL uses the password when initializing a new volume.
Editing `.env` does not change an existing database password.

Production requires HTTPS, Secure cookies, explicit HTTPS origins
and correct trusted-proxy configuration.

## PostgreSQL startup

Open Docker Desktop and wait for its Linux engine.

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d db
docker compose --env-file .env -f infra/compose.yaml ps
```

Wait for healthy status, then:

```powershell
python scripts/check_database.py
```

Expected database/user: railconnect.
Local port: 127.0.0.1:5433.
Data persists in a Docker volume.

For connection timeouts, check engine, container health and application
connection before changing code.

## Migrations and demonstration data

```powershell
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini check

python scripts/seed_stations.py
python scripts/seed_stations.py
python scripts/preview_timetable.py
python scripts/seed_timetable.py
python scripts/seed_timetable.py

python scripts/materialize_demo_runs.py --start-date 2026-10-12 --end-date 2026-10-18
python scripts/materialize_demo_runs.py --start-date 2026-10-12 --end-date 2026-10-18
```

On a fresh database:

- First station seed inserts 30; repetition verifies 30 existing.
- First timetable seed inserts 12 services and 42 stops.
- Repeated timetable seeding verifies rather than duplicates records.
- Baseline materialization creates 70 runs and skips 14 combinations.
- Repeated materialization verifies existing runs and inserts none.

Preview validates and compares without writing.
Conflicts return a nonzero exit status.

Registration, timetable verification/seeding and successful summary creation
share one transaction. Failure rolls back the operation.

Repeated imports preserve the original summary.
Registering already-seeded data records services as existing.

Metadata: data/processed/demo_timetable.source.json.
Source reference: demo-timetable-v1.

For demonstration imports, omitted pickup/dropoff permissions follow
departure/arrival presence respectively. Explicit values are preserved.

Materialization:

- Requires development or test environment.
- Supports at most 31 days per invocation.
- Requires dates within timetable validity.
- Commits or rolls back all writes in the invocation.

Prepare another range explicitly when needed:

```powershell
python scripts/materialize_demo_runs.py --start-date 2026-10-19 --end-date 2026-10-19
```

Search reads prepared runs and does not create missing dates.

Run-stop timestamps are UTC.
Passenger boarding dates and displays use Asia/Colombo.
An overnight run may start on the previous date.

Schedules are fictional.
Selected stations and DEMO_ codes do not represent a complete official network.

See docs/data-card.md.

## Backend startup

In a dedicated terminal at the repository root:

```powershell
.\backend\.venv\Scripts\Activate.ps1
python -m uvicorn railconnect.app:create_app --factory --reload --reload-dir backend/src --host 127.0.0.1 --port 8000
```

Keep the terminal running.

- http://127.0.0.1:8000/health/live
- http://127.0.0.1:8000/health/ready
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/api/v1/stations

Liveness: {"status":"ok"}.
Readiness: {"status":"ready"} when checks succeed.

The backend root `/` has no application page.
Use the frontend address for the user interface.

JSON request logs appear in the terminal.
Stop with Ctrl+C.

## Frontend startup

In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173.

Use npm ci for a fresh checkout or dependency changes.
For an installed environment, npm run dev is sufficient.

Vite proxies /api to the backend.
Deployment requires separate API routing.

Use a configured development origin.
If Vite selects another port, resolve the port conflict or explicitly
configure the intended origin before testing protected operations.

Backend and PostgreSQL must be running for application data.

Frontend npm commands must run from frontend, where package.json exists.

## Restart after closing the laptop

Start Docker Desktop, activate the backend environment and start the database.
Check the application connection, then start backend and frontend separately.

No reinstall, reseeding or new Git commit is required merely because
the laptop or terminals closed.

Re-run materialization only if required dates have not been prepared.
The command is repeatable.

## Journey contracts

Search:

```text
GET /api/v1/journeys
```

Parameters:

- departure_station_id
- arrival_station_id
- travel_date
- Optional arrive_before and arrival_date
- Optional limit and offset

Travel date is the passenger boarding date in Asia/Colombo.
It may differ from run service_date.

arrive_before is a local time without a timezone suffix.
Without arrival_date, the deadline uses travel_date.
Overnight deadlines require the intended arrival date.
The deadline is inclusive.
An arrival date requires a time and cannot precede travel date.

Search excludes cancelled runs and disallowed boarding/alighting.
Restricted runs retain explicit status.

Detail:

```text
GET /api/v1/journeys/{run_id}
```

Optional departure_stop_sequence and arrival_stop_sequence must be paired.

Details expose ordered scheduled stops, permissions, status, version and source.
Cancelled schedules remain viewable without becoming feasible journeys.

Missing provenance returns source: null.
Registration/retrieval times are not live operational updates.

## Staff provisioning and access

Apply migrations before provisioning.

```powershell
python scripts/provision_staff.py --username local_controller --display-name "Local Controller" --role controller
```

Enter and confirm a private 15–128 character password.
Terminal input is hidden.

Provisioning creates an individual account and role assignment.
It rejects existing usernames rather than changing credentials or roles.

Supported roles: controller and administrator.

Optional separate test accounts:

```powershell
python scripts/provision_staff.py --username local_controller_test --display-name "Local Test Controller" --role controller
python scripts/provision_staff.py --username local_audit_admin --display-name "Local Audit Administrator" --role administrator
```

Use another username if necessary.
No self-service password-reset workflow is implemented.

In the frontend, choose Staff access and sign in.

The panel displays account, roles, permissions and absolute expiry.
Browser refresh/reopening restores a valid session.
Refresh session checks current account and session.

Default absolute lifetime: eight hours.
Default idle timeout: thirty minutes.
The server enforces both.

Logout revokes the session and clears the cookie.
Unconfirmed logout displays an error.

Authentication endpoints:

- POST /api/v1/auth/login
- GET /api/v1/auth/me
- POST /api/v1/auth/logout

Login requires JSON and allowed Origin.
Authenticated mutations require allowed Origin and session-bound CSRF token.

The csrf_token returned by login/me is sent in X-CSRF-Token.
It is separate from the HTTP-only authentication cookie.

Only the authentication token hash is stored in the database.
Session/CSRF state is not persisted in browser localStorage.

Default login limits: 30 client and 5 account attempts per five minutes.

## Permission-aware staff panels

- reports.read: pending report queue.
- reports.review: verification and rejection.
- incidents.edit: approved amendments.
- incidents.resolve: resolution.
- audit.read: private audit history.

Controllers have report/lifecycle permissions but not audit.read.
Administrators have audit.read under the explicit role mapping.

UI visibility is not the authorization boundary.
The backend independently checks every protected operation.

Timetable-management permission does not yet provide a protected import UI.

## Passenger reporting

Frontend: Report a disruption.

The form collects title, narrative and observation time in Sri Lanka time.
It converts the time to UTC.

It checks current staff session before submission and includes CSRF
when authenticated. Unexpected session-check failures stop submission.

The server rejects invalid staff-cookie submissions rather than treating
them as anonymous.

Endpoint:

```text
POST /api/v1/reports
```

Requires JSON and allowed Origin.

Required fields:

- title: 1–160 characters after boundary whitespace removal.
- narrative: 1–4000 characters after boundary whitespace removal.
- observed_at: aware timestamp, not in the future.

Optional API fields:

- run_hint_id
- station_hint_id
- departure_stop_sequence_hint
- arrival_stop_sequence_hint

The current passenger form does not expose these optional hint controls.
A narrative may describe known service or location details.

Paired endpoints must be ordered and belong to the prepared run.
Station hints must be active and match any supplied run/segment scope.

Cancelled/restricted runs may be reported.
Acceptance does not establish feasibility or disruption.

Reject server-owned status, actor and review fields.

HTTP 201 returns:

- report_id
- status
- submitted_at
- message

The receipt confirms pending submission, not verification.

The UI disables duplicate submission, preserves input after failures
and does not automatically retry uncertain submissions.

Default report limit: five attempts per client per hour.
429 responses include Retry-After.

Counters are independent from login limits and report creation.
Malformed bodies are rejected before the service-level counter.

## Pending queue and report review

Queue:

```text
GET /api/v1/staff/reports?limit=20&offset=0
```

Requires reports.read.
Returns pending reports ordered by submitted_at and report ID.

Response: items, total, limit, offset.
Default limit/offset: 20/0.
Bounds: limit 1–100, offset 0–10000.

Queue narrative is private unverified material.
Queue reads do not change report state.

Decisions:

```text
POST /api/v1/staff/reports/{report_id}/verify
POST /api/v1/staff/reports/{report_id}/reject
```

Require reports.review, valid session, allowed Origin and CSRF.

Both require positive integer expected_version and reason of 1–2000 characters.

Rejection example:

```json
{
  "expected_version": 1,
  "reason": "Insufficient evidence to verify the synthetic claim."
}
```

Verification also requires approved:

- run_id
- scope_kind: run or segment
- Paired departure_stop_sequence/arrival_stop_sequence for segment scope
- impact_kind: cancellation, restriction or delay
- estimated_delay_minutes for delay only
- Aware effective_from and effective_until
- public_summary: 1–1000 characters
- evidence_basis: 1–2000 characters

Whole-run scope has null/omitted segment endpoints.
Segment scope requires ordered endpoints belonging to the run.
Cancellation requires whole-run scope.
Delay must be integer minutes from 1–1440.
End must follow start.

Staff approve facts independently of hints.
Server derives actor, decision time and request ID.
Identified staff submitters cannot review their own reports.

Verification atomically writes report decision, incident, initial revision
and audit. Rejection writes report decision and audit without an incident.

Success returns report_id, status, report_version, incident_id,
revision_id and incident_version.

Rejection has null incident/revision references.

The frontend reloads the queue after confirmed decisions.
Conflicts and uncertain decisions require reload before another attempt.

Errors:

- 401: invalid/missing authentication.
- 403: permission, Origin/CSRF or identified self-review denial.
- 404: report missing.
- 409: stale version/already reviewed.
- 422: invalid input or approved scope.

## Incident management

Find incident references from verification success or:

```text
GET /api/v1/incidents?run_id={run_id}
```

Do not confuse run_id, report_id, incident_id or request_id.

The management panel loads current public approved facts and incident version.
Its reference field expects incident_id.

Amendment:

```text
POST /api/v1/staff/incidents/{incident_id}/amend
```

Requires incidents.edit, session, allowed Origin and CSRF.

Send expected_version, reason and the complete approved object.
Partial replacement facts are not supported.

The form prefills public facts but requires a fresh private evidence basis
and independent-review confirmation.

Amendment creates a new revision, increments incident version/current
revision number and writes audit atomically.

Resolution:

```text
POST /api/v1/staff/incidents/{incident_id}/resolve
```

Requires incidents.resolve, session, allowed Origin and CSRF.

Example:

```json
{
  "expected_version": 2,
  "reason": "Synthetic disruption ended.",
  "resolution_effective_at": "2026-10-18T17:55:00+05:30"
}
```

Use the actual current incident version and an appropriate timestamp.

Resolution effective time cannot be future or earlier than the current
revision's effective start. Backdating within these bounds is allowed.

Resolution increments incident version and preserves current revision.
No reopening is implemented.
Resolved incidents reject further changes.

Both operations return:

- incident_id
- originating_report_id
- status
- incident_version
- current_revision_number
- current_revision_id

Audit failure rolls back the business operation.

Lifecycle errors:

- 401: missing/invalid session.
- 403: permission or Origin/CSRF denial.
- 404: incident missing.
- 409: stale version or resolved incident.
- 422: input, reference or time validation.
- 503: inconsistent required report/current-revision history.

The panel refreshes after confirmed changes.
Confirmed success remains visible if refresh fails.
Conflicts/uncertain changes require reload.

Lifecycle changes do not overwrite scheduled run-stop timestamps.

## Public incident reads

Endpoints:

```text
GET /api/v1/incidents?run_id={run_id}&limit=20&offset=0
GET /api/v1/incidents/{incident_id}
```

No staff authentication is required.

Only incidents linked to verified reports and their current approved revision
are selected.

List requires run_id and uses the same pagination bounds.
Unknown runs return an empty list; missing incident details return 404.

Fields include:

- Incident ID/version and revision ID/number.
- Lifecycle status.
- Run ID and timetable_source_ref.
- Approved scope and segment endpoints.
- Impact and estimated_delay_minutes.
- Effective interval and public_summary.
- verified_at and resolution_effective_at.

Excluded fields include narrative, private evidence basis, decision reasons,
staff identities and audit request IDs.

Listings include active and resolved incidents.
They do not calculate current passenger-segment applicability.

A resolved incident may retain its former approved delay in history.
Do not present that value as a currently active delay.

Active status alone also does not establish applicability.
Journey effect matching remains unimplemented.

## Private audit history

Endpoint:

```text
GET /api/v1/staff/reports/{report_id}/audit?limit=20&offset=0
```

Requires audit.read.
Use report_id, not incident_id.

The administrator audit panel loads history on request.
It includes rejected reports without incidents.

Response: report_id, items, total, limit, offset.

Event fields:

- event_id, report_id, incident_id, revision_id
- actor_id, action, reason
- request_id, report_version, incident_version
- occurred_at

These are private management fields.

Ordering: occurred_at, event_id.
Use versions/references to interpret equal-time changes.

Missing report: 404.
Invalid session: 401.
Insufficient permission: 403.
Removing the only staff role invalidates authentication and returns 401.

Default pagination is 20/0, with limits 1–100 and offsets 0–10000.

Successful queue, decision, lifecycle, audit and public incident responses
use Cache-Control: no-store.

## Storage and migrations

Current migration head: af88e86de607.

Migration 5c23c99becea adds incident reports, incidents, revisions,
audit records and append-only history protections.

Migration af88e86de607 adds report_rate_limits.

Public/lifecycle/UI changes require no additional migration.

Verification creates incident version 1/revision 1.
Amendment creates another approved revision.
Resolution preserves that revision and increments incident version.

History triggers reject updates, deletes and truncation.
Rollback remains supported.

## Cleanup

Identity preview/apply:

```powershell
python scripts/cleanup_identity.py
python scripts/cleanup_identity.py --apply
python scripts/cleanup_identity.py --help
```

Default retention: seven days for expired/revoked sessions,
one day for expired login limits.
Default batch: 500 per table.

Report-limit preview/apply:

```powershell
python scripts/cleanup_report_limits.py
python scripts/cleanup_report_limits.py --apply
python scripts/cleanup_report_limits.py --help
```

Default retention: one day after window expiry.
Default batch: 500.
Report options include --retention-days and --batch-limit.
Bounds are retention 1–365 days and batch 1–1000.

Cleanup selects/locks bounded keys before deleting those exact records.
It preserves current windows, reports, users and role assignments.
Applied changes are transactional.

Authentication rejects expired sessions even without cleanup.
Scheduling remains an operational responsibility.

## Backend checks

From the repository root, with the backend environment active:

```powershell
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" pip check --python backend/.venv/Scripts/python.exe
python -m ruff check --config backend/pyproject.toml backend/src backend/tests backend/migrations scripts
python -m ruff format --check --config backend/pyproject.toml backend/src backend/tests backend/migrations scripts
python -m mypy --config-file backend/pyproject.toml backend/src/railconnect
python -m alembic -c backend/alembic.ini check
python -m pytest -c backend/pyproject.toml --tb=short
```

PostgreSQL and migrations are required.

Most database fixtures roll back their changes.
Rate-limit races use independent connections and remove their generated records.

Review/lifecycle races use temporary metadata schemas and independent
transactions, then remove those schemas.

The development/test database account requires CREATE permission
for temporary schemas.

Migration-installed triggers are tested separately.

Never configure tests against a deployed production database.

## Frontend checks

From frontend:

```powershell
npm run lint
npm run build
npm test
```

The build includes TypeScript checking.
Component tests substitute API responses and do not require PostgreSQL/backend.

## Repeatable incident workflow

See docs/incident-workflow-check.md for:

- Browser replay instructions.
- Version/revision expectations.
- Public/private boundary checks.
- Repeated isolated API scenario commands.
- Manual verification checkpoint and limitations.

The current automated checkpoint is 585 backend and 122 frontend tests.

These counts describe this checkpoint and may change with later features.

## Linux and macOS

Install compatible Python 3.13, Node and Docker Compose.

```bash
python3.13 -m venv "$HOME/.local/share/railconnect-tools/uv"
"$HOME/.local/share/railconnect-tools/uv/bin/python" -m pip install "uv==0.13.0"
```

From the repository root:

```bash
python3.13 -m venv --prompt RailConnect-AI backend/.venv
"$HOME/.local/share/railconnect-tools/uv/bin/uv" sync --project backend --extra dev --locked
source backend/.venv/bin/activate
```

For a fresh checkout only:

```bash
cp .env.example .env
```

Configure password and settings as described above.

Use `/` path separators and backend/.venv/bin/python for explicit paths.

```bash
"$HOME/.local/share/railconnect-tools/uv/bin/uv" pip check --python backend/.venv/bin/python
```

These instructions do not claim separate macOS clean-checkout verification.

## Dependency changes

Declare backend dependencies in backend/pyproject.toml.

After an intentional change:

```powershell
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" lock --project backend
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" sync --project backend --extra dev --locked
```

Run checks and commit pyproject.toml and uv.lock.

Use npm from frontend for frontend dependency changes.
Commit package.json and package-lock.json together.

## CI

.github/workflows/ci.yml runs on pushes, pull requests and manual dispatch.

Backend CI uses the committed uv lockfile and temporary PostgreSQL.
Frontend CI uses npm ci and the committed npm lockfile.

Checks include dependencies, lint, formatting, types, migrations,
schema checks, repeated seeding/materialization, tests and frontend build.

The complete backend suite includes the repeatable synthetic scenarios.
No separate workflow step is needed for those tests.

Final branch CI must be checked against the actual pushed commit.
Local success does not establish CI success, deployment or release completion.

## Current UI limitation

The independent-review checkbox confirmation can render with an oversized
layout and narrow label.

Correction is deferred to the final responsive/accessibility review.
Do not treat the current interface as release-polished.

Journey disruption calculations and protected timetable management
remain separate subsequent features.
