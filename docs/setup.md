# Development setup

## Prerequisites

- Git
- Python 3.13
- Node.js 22.20.0
- Docker Desktop with Linux containers
- PowerShell on Windows

Run commands from the repository root unless another directory is specified.

## Install uv

Install the tool separately from the project's Python environment:

```powershell
python -m venv "$env:LOCALAPPDATA\RailConnectTools\uv"
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\python.exe" -m pip install "uv==0.13.0"
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" --version
```

## Backend installation

For a fresh checkout, create the named environment:

```powershell
python -m venv --prompt RailConnect-AI backend\.venv
```

Install dependencies from the committed lockfile:

```powershell
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" sync --project backend --extra dev --locked
.\backend\.venv\Scripts\Activate.ps1
```

The sync command installs the backend package in editable mode.
Stop the backend server before syncing dependencies on Windows.

Select `backend\.venv\Scripts\python.exe` through
`Python: Select Interpreter` in VS Code.

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\backend\.venv\Scripts\Activate.ps1
```

Activate the backend environment in each terminal running backend commands.

## Local configuration

For a fresh checkout, create local configuration once:

```powershell
Copy-Item .env.example .env
```

Do not overwrite an existing configured `.env`.

Generate a local database password:

```powershell
python -c "import secrets; print(secrets.token_hex(24))"
```

Open `.env` and assign the generated value to `POSTGRES_PASSWORD`.

Keep this database URL:

```dotenv
RAILCONNECT_DATABASE_URL=postgresql+psycopg://railconnect:${POSTGRES_PASSWORD}@127.0.0.1:5433/railconnect
```

Keep these development settings:

```dotenv
RAILCONNECT_APP_NAME="RailConnect AI"
RAILCONNECT_ENVIRONMENT=development
RAILCONNECT_DEBUG=false
```

For local HTTP authentication and reporting, include:

```dotenv
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

Use the same non-secret setting names in `.env.example`.
Leave its database password blank.
Keep the actual password only in ignored local configuration.

The `.env` file is ignored by Git.
Environment variables override values from `.env`.
Run backend commands from the repository root so configuration is found.

Restart the backend after changing configuration.

PostgreSQL uses the configured password when initializing a new volume.
Changing `.env` alone does not change an existing database password.

Production requires HTTPS, Secure cookies and configured HTTPS origins.
Local HTTP settings must not be reused as production configuration.
Deployment must configure trusted proxies correctly.

## Start PostgreSQL

Open Docker Desktop and wait for its Linux engine to start.

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d db
docker compose --env-file .env -f infra/compose.yaml ps
```

Wait until the database container reports healthy.

Verify the application connection:

```powershell
python scripts/check_database.py
```

Expected database and user: `railconnect`.

The local database listens on `127.0.0.1:5433`.
Its data persists in a Docker volume.

If tests stop with a connection timeout, check Docker Desktop,
container health and the application connection before changing code.

## Migrations and demonstration data

With the backend environment active:

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

On a fresh database, station seeding inserts 30 stations.
The second invocation reports 0 inserted and 30 already present.

The first timetable seed inserts 12 demonstration services and 42 stops.
Repeated seeding inserts nothing and verifies existing records.
Conflicting data causes an error and rolls back the import transaction.

Preview validates the dataset and compares database records without writing.
Conflicts produce a nonzero exit status.

Timetable seeding registers provenance and a successful import summary
in the same transaction as timetable verification/seeding.

Repeated imports preserve the original summary.
When registering an already-seeded timetable, the summary records matching
services as existing rather than newly inserted.

Source metadata is in `data/processed/demo_timetable.source.json`.
The timetable source reference is `demo-timetable-v1`.

For this demonstration importer, omitted boarding and alighting permissions
follow the presence of departure and arrival times respectively.
Explicit values are preserved.

Dated runs must be prepared before journey search can return them.
On a fresh run table, the example creates 70 runs.
Repeating it verifies 70 existing runs and inserts nothing.
Fourteen service dates are skipped according to operating rules.

Materialization supports at most 31 days per invocation.
It requires a development or test environment.
Prepare other ranges explicitly within timetable validity.
Writes in one invocation commit together or roll back.

Run-stop scheduled timestamps are stored in UTC.
Search uses the passenger's boarding date in Asia/Colombo.
An overnight run may have started on the previous date.
Search does not create runs.

Schedules are fictional and include daily, weekday, weekend,
reverse-direction and overnight examples.

These are selected stations, not the complete railway network.
Codes beginning with `DEMO_` are project identifiers.
The data does not provide live timetables or service updates.

See `docs/data-card.md` for coverage and limitations.

## Start the backend

In a dedicated terminal, from the repository root:

```powershell
.\backend\.venv\Scripts\Activate.ps1
python -m uvicorn railconnect.app:create_app --factory --reload --reload-dir backend/src --host 127.0.0.1 --port 8000
```

Keep that terminal running.

- Liveness: http://127.0.0.1:8000/health/live
- Database readiness: http://127.0.0.1:8000/health/ready
- API documentation: http://127.0.0.1:8000/docs
- Stations: http://127.0.0.1:8000/api/v1/stations

Liveness returns `{"status":"ok"}`.
Readiness returns `{"status":"ready"}` when checks succeed.

Request logs appear as JSON in the backend terminal.
Stop the server with Ctrl+C.

## Frontend installation and startup

In another terminal, from the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173.

Use `npm ci` after a fresh checkout or dependency changes.
An existing installed environment only needs `npm run dev`.

Vite forwards `/api` requests to the local backend during development.
The backend must be running for stations, journeys and staff sessions.
Deployment requires its own API routing configuration.

## Journey search and details

Search endpoint:

```text
GET /api/v1/journeys
```

Parameters:

- departure_station_id
- arrival_station_id
- travel_date
- Optional arrive_before and arrival_date
- Optional limit and offset

`travel_date` is the passenger's boarding date in Asia/Colombo.
It may differ from the run's starting `service_date`.

`arrive_before` is a local time without a timezone suffix.
Without `arrival_date`, the deadline applies on `travel_date`.
For overnight arrival, supply the intended arrival date explicitly.

The deadline is inclusive.
An arrival date requires an arrival time and cannot precede travel date.

Search returns persisted run IDs and departure/arrival stop sequences.
Cancelled runs and disallowed boarding/alighting choices are excluded.

Restricted runs carry explicit status.
Detailed disruption eligibility belongs to the disruption feature.

Detail endpoint:

```text
GET /api/v1/journeys/{run_id}
```

Optional segment parameters must be supplied together:

- departure_stop_sequence
- arrival_stop_sequence

Details include ordered scheduled stops, passenger permissions,
run status, version and registered source metadata.

Cancelled runs remain viewable with their status.
Viewing their schedule does not make them feasible journeys.

Unregistered provenance returns `source: null`.
Missing metadata does not establish freshness.

Registration and retrieval times are not live railway update times.

## Staff identity and local testing

Apply migrations before provisioning accounts.

From the repository root, with the environment active:

```powershell
python scripts/provision_staff.py --username local_controller --display-name "Local Controller" --role controller
```

Enter and confirm a password containing 15 to 128 characters.
Input is hidden.
Keep the password private and out of Git and shared screenshots.

Provisioning creates an individual account and role assignment.
It rejects an existing username rather than replacing password or role.

Initial roles are controller and administrator.
Administrator permissions are explicitly mapped.

To create a separate local test account:

```powershell
python scripts/provision_staff.py --username local_controller_test --display-name "Local Test Controller" --role controller
```

Choose another username if it already exists.
Provisioning does not provide a password-reset workflow.

Open http://127.0.0.1:5173 and select Staff access.
Sign in with the account and password you provisioned.

Staff access displays account, roles, permissions and absolute expiry.
Refreshing the browser or reopening Staff access restores a valid session.
Refresh session checks the current account/session against the backend.

Default absolute lifetime is eight hours.
Default idle timeout is thirty minutes.
The server enforces both.

Sign out revokes the session and clears its cookie.
Unconfirmed sign-out displays an error rather than claiming success.

Journey search remains public.
Incident management APIs are protected.
Incident management and timetable management interfaces remain pending.

Authentication endpoints:

- POST /api/v1/auth/login
- GET /api/v1/auth/me
- POST /api/v1/auth/logout

Login requires JSON and a configured browser Origin.
Authenticated mutations require an allowed Origin and session-bound CSRF token.

The frontend sends cookies through same-origin requests via the Vite proxy.

Authentication tokens are delivered through HTTP-only cookies.
The database stores their hashes.
The frontend does not persist session or CSRF state in localStorage.

Default login limits are 30 attempts per client and 5 per account
within a five-minute window.

## Identity-record cleanup

Preview eligible records:

```powershell
python scripts/cleanup_identity.py
```

Default preview does not delete records.

Apply one bounded batch explicitly:

```powershell
python scripts/cleanup_identity.py --apply
```

Default retention is seven days for expired/revoked sessions
and one day for expired login-rate windows.

Default batch limit is 500 records per table.

```powershell
python scripts/cleanup_identity.py --help
```

Cleanup preserves users, role assignments, current sessions and current windows.

Deletion selects and locks bounded keys before deleting those exact records.
Applied changes are transactional.

Authentication rejects expired/revoked sessions before cleanup.
Deployment scheduling remains to be configured.

## Passenger report submission

Endpoint:

```text
POST /api/v1/reports
```

Requires JSON and a configured browser Origin.

Required fields:

- title: 1 to 160 characters after boundary whitespace removal.
- narrative: 1 to 4000 characters after boundary whitespace removal.
- observed_at: timezone-aware timestamp.

Optional scope hints:

- run_hint_id
- station_hint_id
- departure_stop_sequence_hint
- arrival_stop_sequence_hint

Segment endpoints must be supplied together and belong to the hinted run.
Arrival sequence must follow departure sequence.

Station hints must identify active stations.
When combined with a run or segment, the station must belong to that scope.

Cancelled and restricted runs can still be reported.
Acceptance does not establish journey feasibility.

Observation time cannot be in the future.
Hints remain unverified until staff review.

Passengers cannot supply status, reviewer identity, review reasons,
approved delay values or submission timestamps.

Successful submission returns HTTP 201 with:

- report_id
- status
- submitted_at
- message

The pending receipt excludes narrative and private review fields.
Submission does not create approved operational evidence or change journeys.

Anonymous submission is permitted.

When a staff cookie is present, valid authentication and the session-bound
CSRF token are required. Staff identity is derived on the server.

Invalid or expired staff cookies do not silently become anonymous access.

Report limits use:

```dotenv
RAILCONNECT_REPORT_RATE_WINDOW_SECONDS=3600
RAILCONNECT_REPORT_CLIENT_MAX_ATTEMPTS=5
```

The default is five attempts per client within one hour.
These counters are separate from login counters.
Rate rejection returns 429 with Retry-After.

Attempts reaching the service are counted separately from report creation.
Failed report creation does not reset the counter.
Malformed bodies are rejected before the service.

The submission API is implemented.
The passenger reporting interface remains pending.

## Protected staff report queue

Endpoint:

```text
GET /api/v1/staff/reports?limit=20&offset=0
```

Requires a valid staff session and reports.read.
The queue service also checks permission.

Only pending reports are returned.
Ordering is oldest submission first, then report ID.

Pagination defaults to limit 20 and offset 0.
Limit must be 1 through 100.
Offset must be 0 through 10000.

Response fields:

- items
- total
- limit
- offset

Each item includes report ID, narrative, timestamps, scope hints,
pending status and current report version.

Narrative is an unverified claim.
This is a protected staff response, not a public incident response.

Reading the queue does not change report state.
Successful responses use Cache-Control: no-store.

## Protected verification and rejection

Endpoints:

```text
POST /api/v1/staff/reports/{report_id}/verify
POST /api/v1/staff/reports/{report_id}/reject
```

Both require:

- Valid staff session cookie.
- reports.review permission.
- Allowed Origin.
- Session-bound CSRF token in X-CSRF-Token.
- JSON request body.

Use `csrf_token` returned by login or the current-session endpoint.
It is separate from the HTTP-only authentication cookie.

The service rechecks current account and role permissions.
Identified staff submitters cannot review their own reports.

Reviewer identity, decision time and audit request ID are server-derived.
Do not supply reviewer IDs, review timestamps or status fields.

### Rejection

```json
{
  "expected_version": 1,
  "reason": "Insufficient evidence to verify the reported disruption."
}
```

Reasons are nonempty after boundary whitespace removal and limited
to 2000 characters. Versions must be positive integers.

Rejection increments report version and records an audit event.
It does not create an incident.

### Verification

Supply expected_version, reason and approved.

The approved object contains:

- run_id: existing prepared dated run.
- scope_kind: run or segment.
- departure_stop_sequence and arrival_stop_sequence for segment scope.
- impact_kind: cancellation, restriction or delay.
- estimated_delay_minutes for delay impact.
- effective_from and effective_until as aware timestamps.
- public_summary: 1 to 1000 characters.
- evidence_basis: 1 to 2000 characters.

Whole-run scope omits endpoints or sets both to null.
Segment scope requires ordered endpoints belonging to the run.

Cancellation requires whole-run scope.
Delay requires integer minutes between 1 and 1440.
Cancellation and restriction must not contain estimated delay minutes.

Effective end must follow effective start.
Approved timestamps are normalized to UTC.

Staff explicitly approve facts independently of passenger hints.
Narrative is not an approved delay estimate.

### Results and errors

Successful decisions return HTTP 200 with:

- report_id
- status
- report_version
- incident_id
- revision_id
- incident_version

Rejection returns null incident and revision references.
Verification returns the new incident and initial revision.

Verification writes decision, incident, revision and audit atomically.
Rejection writes decision and audit atomically.

Audit records include actor, reason, versions and server-generated request ID.
Business failure rolls back the complete decision.
Authentication uses a separate transaction.

Errors use the safe error envelope:

- 401: missing or invalid authentication.
- 403: insufficient permission, invalid Origin/CSRF or identified self-review.
- 404: report does not exist.
- 409: stale version or report already reviewed.
- 422: invalid input or approved scope references.

Concurrent review permits one successful decision and one conflict.
Successful responses use Cache-Control: no-store.

## Protected incident amendments

Endpoint:

```text
POST /api/v1/staff/incidents/{incident_id}/amend
```

Requires a valid staff cookie, incidents.edit, allowed Origin
and session-bound CSRF token in X-CSRF-Token.

Supply JSON containing:

- expected_version: current incident version.
- reason: nonempty reason, limited to 2000 characters.
- approved: complete replacement approved facts.

The approved object uses the verification contract.
Do not send only the changed field.

Example:

```json
{
  "expected_version": 1,
  "reason": "Updated synthetic evidence supports this estimate.",
  "approved": {
    "run_id": "REPLACE_WITH_PREPARED_RUN_UUID",
    "scope_kind": "run",
    "impact_kind": "delay",
    "estimated_delay_minutes": 30,
    "effective_from": "2026-10-18T10:00:00+05:30",
    "effective_until": "2026-10-18T14:00:00+05:30",
    "public_summary": "Synthetic demonstration delay.",
    "evidence_basis": "Controller-reviewed synthetic test evidence."
  }
}
```

Replace the UUID placeholder before sending.
The example is synthetic, not a live railway update.

The service rechecks current account and permission, locks the incident
and checks active state and expected version.

Success creates a new immutable approved revision, increments incident version
and current revision number, and writes an audit event in one transaction.

Previous revisions are preserved.
The originating report's completed review version is unchanged.

## Protected incident resolution

Endpoint:

```text
POST /api/v1/staff/incidents/{incident_id}/resolve
```

Requires a valid staff cookie, incidents.resolve, allowed Origin
and session-bound CSRF token in X-CSRF-Token.

Example JSON:

```json
{
  "expected_version": 1,
  "reason": "The synthetic disruption has ended.",
  "resolution_effective_at": "2026-10-18T11:00:00+05:30"
}
```

Use the actual current incident version and an appropriate aware timestamp.

Effective resolution time cannot be in the future relative to the server's
decision clock or earlier than the current revision's effective start.

Backdating within those bounds is permitted.

Resolution records actor, reason, decision time and effective resolution time.
It increments incident version, preserves the current revision and writes
its audit event atomically.

Only active incidents may be amended or resolved.
Resolved incidents reject further changes.
No reopening workflow is implemented.

Audit insertion failure rolls back the complete business operation.

Successful amendment and resolution responses contain:

- incident_id
- originating_report_id
- status
- incident_version
- current_revision_number
- current_revision_id

Successful responses use Cache-Control: no-store.

Lifecycle errors:

- 401: missing or invalid authentication.
- 403: insufficient permission or invalid Origin/CSRF.
- 404: incident does not exist.
- 409: stale version or incident already resolved.
- 422: invalid input, scope references or lifecycle timestamps.
- 503: required originating report or current revision history is inconsistent.

Concurrent changes using the same version permit one successful change
and one conflict.

Tested races are amendment/amendment, amendment/resolution
and resolution/resolution.

Lifecycle operations preserve original scheduled run-stop timestamps.
Their journey effects remain a later integration.

## Protected report audit history

Endpoint:

```text
GET /api/v1/staff/reports/{report_id}/audit?limit=20&offset=0
```

Requires a valid staff session and audit.read.

Administrators have audit.read under the current mapping.
Controllers do not have it by default.

For local testing, provision an administrator interactively:

```powershell
python scripts/provision_staff.py --username local_audit_admin --display-name "Local Audit Administrator" --role administrator
```

Choose another username if it already exists.
Keep the password private.

This creates a test account, not an audit frontend.

History is retrieved by report ID.
It includes rejected reports without incidents.
Pending reports may have empty history.
Missing reports return 404.

Response fields:

- report_id
- items
- total
- limit
- offset

Each item includes:

- event_id
- report_id
- incident_id
- revision_id
- actor_id
- action
- reason
- request_id
- report_version
- incident_version
- occurred_at

These are private management fields, not a public incident response.

Events are ordered by occurrence time and event ID.
For equal timestamps, event ID is a stable tie-breaker rather than causal order.
Use versions and references when interpreting lifecycle changes.

Pagination defaults to limit 20 and offset 0.
Limits are 1 through 100.
Offsets are 0 through 10000.
Unknown query fields are rejected.

Successful responses use Cache-Control: no-store.

Missing authentication returns 401.
Insufficient permission returns 403.
Removing the user's only staff role invalidates authentication and returns 401.

## Incident storage and history

Migration 5c23c99becea adds:

- incident_reports
- incidents
- incident_revisions
- incident_audit_events

Migration af88e86de607 adds report_rate_limits.

Current migration head: af88e86de607.

Protected review, lifecycle and audit-read workflows require no
additional migration.

Passenger claims are separate from approved operational facts.

Revision records identify approved run/segment, effective interval,
impact, evidence basis and verification actor.

Database triggers reject revision/audit updates, deletes and truncation.
Transaction rollback remains supported.

Verification creates incident version 1 and revision number 1.
Amendment creates another approved revision.
Resolution preserves the selected revision and increments incident version.

Public incident responses and passenger/staff incident interfaces remain pending.

Verified incident records do not yet change journey results.
That integration belongs to the disruption feature.

## Report-limit cleanup

Preview old counters:

```powershell
python scripts/cleanup_report_limits.py
```

Apply one bounded batch:

```powershell
python scripts/cleanup_report_limits.py --apply
```

Default retention is one day after window expiry.
Default batch limit is 500 records.

```powershell
python scripts/cleanup_report_limits.py --help
```

Options include --retention-days and --batch-limit.
Retention must be 1 through 365 days.
Batch limit must be 1 through 1000.

Cleanup preserves current windows, reports and login counters.
Deletion keys are selected, locked and bounded before deletion.
Applied changes are transactional.

Deployment must arrange an operator procedure or cleanup schedule.

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

Run PostgreSQL and apply migrations before database tests.

Most database tests use fixtures that roll back changes.
Rate-limit concurrency tests use independent connections and committed
test records, then remove their own generated records.

Review/lifecycle concurrency tests create uniquely named temporary schemas
from model metadata, use independent transactions and remove those schemas.

The development/test database account needs CREATE permission on the database.

Four cases cover verification/rejection, amendment/amendment,
amendment/resolution and resolution/resolution.

Migration-installed history triggers are checked separately by
incident immutability tests.

Cleanup tests use rollback-isolated transactions.

Never configure tests against a deployed production database.

## Frontend checks

From the frontend directory:

```powershell
npm run lint
npm run build
npm test
```

The build includes TypeScript checking.
Component tests substitute API responses.
They do not require the backend or PostgreSQL.

## Linux and macOS differences

Use compatible Python 3.13, Node and Docker Compose installations.

Install uv separately:

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

Create configuration only for a fresh checkout:

```bash
cp .env.example .env
```

Generate and configure the password as described above.
Configure session and rate-limit settings for the intended environment.

Python, Docker Compose and npm commands otherwise follow the same workflow.
Use `/` separators and `backend/.venv/bin/python` for explicit interpreter paths.

Check dependencies with:

```bash
"$HOME/.local/share/railconnect-tools/uv/bin/uv" pip check --python backend/.venv/bin/python
```

These instructions document platform differences.
They do not claim separate macOS clean-checkout verification.

## Dependency changes

Declare backend dependencies in `backend/pyproject.toml`.

After an intentional change on Windows:

```powershell
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" lock --project backend
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" sync --project backend --extra dev --locked
```

Run checks and commit `pyproject.toml` and `uv.lock`.

Change frontend dependencies with npm from the frontend directory.
Commit both `package.json` and `package-lock.json`.

## Continuous integration

`.github/workflows/ci.yml` runs on pushes and pull requests.

Backend checks use the committed uv lockfile and temporary PostgreSQL.
Frontend checks use `npm ci` and the committed npm lockfile.

CI runs lint, configured formatting checks, type checking, migrations,
schema checks, station seeding, timetable preview/import, dated-run
materialization, backend tests, frontend tests and production build.

CI does not establish deployment or assistant evaluation completion.
