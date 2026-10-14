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

If PowerShell blocks activation, allow scripts for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\backend\.venv\Scripts\Activate.ps1
```

## Local configuration

For a fresh checkout, create the local configuration file once:

```powershell
Copy-Item .env.example .env
```

Do not overwrite an existing configured `.env`.

Generate a local database password:

```powershell
python -c "import secrets; print(secrets.token_hex(24))"
```

Open `.env` and assign that generated value to `POSTGRES_PASSWORD`.

Keep this database URL:

```dotenv
RAILCONNECT_DATABASE_URL=postgresql+psycopg://railconnect:${POSTGRES_PASSWORD}@127.0.0.1:5433/railconnect
```

Keep development settings:

```dotenv
RAILCONNECT_ENVIRONMENT=development
RAILCONNECT_DEBUG=false
```

For local HTTP staff authentication, include:

```dotenv
RAILCONNECT_SESSION_COOKIE_NAME=railconnect_session
RAILCONNECT_SESSION_COOKIE_SECURE=false
RAILCONNECT_SESSION_TTL_SECONDS=28800
RAILCONNECT_SESSION_IDLE_TIMEOUT_SECONDS=1800
RAILCONNECT_TRUSTED_ORIGINS='["http://127.0.0.1:5173","http://localhost:5173"]'
RAILCONNECT_LOGIN_RATE_WINDOW_SECONDS=300
RAILCONNECT_LOGIN_RATE_CLIENT_LIMIT=30
RAILCONNECT_LOGIN_RATE_ACCOUNT_LIMIT=5
```

The `.env` file is ignored by Git.
Environment variables override values from `.env`.
Run backend commands from the repository root so configuration is found.

Restart the backend after changing configuration.

PostgreSQL uses the configured password when initializing a new data volume.
Changing `.env` alone does not change the password in an existing database.

Production requires HTTPS, Secure cookies and explicitly configured HTTPS
origins. Local HTTP settings must not be reused as production configuration.
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

On a fresh database, the first station seed inserts 30 stations.
The second reports 0 inserted and 30 already present.

The first timetable seed inserts 12 demonstration services and 42 stops.
Repeated seeding inserts nothing and verifies existing records.
Conflicting data causes an error and rolls back the import transaction.

Timetable preview validates the dataset and compares database records
without writing changes. Conflicts produce a nonzero exit status.

The timetable seed command registers source provenance and a successful
import summary in the same transaction as timetable verification/seeding.
Repeated imports preserve the original summary.

When registering a timetable that was already seeded, the first summary
records the matching services as existing rather than newly inserted.

Source metadata is stored in `data/processed/demo_timetable.source.json`.
The content hash identifies the exact timetable file bytes.
Changed content or metadata under an existing source reference is rejected.

Both preview and import require the dataset and source metadata files.
The seed command requires a development or test environment.

Processed JSON files use LF line endings through `.gitattributes`.
Preserve those line endings to keep content hashes consistent.

For demonstration imports, omitted boarding and alighting permissions
follow the presence of departure and arrival times respectively.
Explicit permission values are preserved.

Dated runs must be prepared before journey search can return them.
On a fresh run table, the example above creates 70 runs.
Repeating it verifies 70 existing runs and inserts nothing.
The 14 skipped service dates reflect weekday and weekend operating rules.

The materialization command supports at most 31 days per invocation
and requires a development or test environment.
Prepare other date ranges explicitly within the timetable's validity period.
All writes in one invocation are committed together or rolled back.

Run stops store scheduled timestamps in UTC.
Search uses the passenger's boarding date in Asia/Colombo.
An overnight run may have started on the previous date.
Search does not create runs.

Timetable schedules are fictional and include daily, weekday, weekend,
reverse-direction and overnight examples.

These are selected demonstration stations, not the complete railway network.
Codes beginning with `DEMO_` are project identifiers.
The data does not provide live timetables or service updates.

See `docs/data-card.md` for coverage, limitations and update procedures.

## Start the backend

In a dedicated terminal with the backend environment active:

```powershell
python -m uvicorn railconnect.app:create_app --factory --reload --reload-dir backend/src --host 127.0.0.1 --port 8000
```

Keep that terminal running.

- Liveness: http://127.0.0.1:8000/health/live
- Database readiness: http://127.0.0.1:8000/health/ready
- API documentation: http://127.0.0.1:8000/docs
- Stations: http://127.0.0.1:8000/api/v1/stations

Liveness returns `{"status":"ok"}`.
Database readiness returns `{"status":"ready"}` when its checks succeed.

Request logs appear as JSON in the backend terminal.
Stop the server with Ctrl+C.

## Frontend installation and startup

In another terminal, starting from the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173.

Use `npm ci` after a fresh checkout or dependency changes.
An existing installed environment only needs `npm run dev`.

Vite forwards `/api` requests to the local backend during development.
The backend must be running to load stations, journeys and staff sessions.
Deployment requires its own API routing configuration.

## Journey search and details

Journey search uses:

- departure_station_id
- arrival_station_id
- travel_date
- Optional arrive_before and arrival_date
- Optional limit and offset

`travel_date` is the passenger's boarding date in Asia/Colombo.
It may differ from the run's starting `service_date`.

`arrive_before` is a local time without a timezone suffix.
Without `arrival_date`, its deadline applies on `travel_date`.
For an overnight arrival, supply the intended arrival date explicitly.

The deadline is inclusive.
An arrival date requires an arrival time and cannot precede the travel date.

Search returns persisted run IDs and departure/arrival stop sequences.
Cancelled runs and disallowed boarding/alighting choices are excluded.
Restricted runs carry an explicit status; detailed disruption eligibility
rules belong to the later disruption workflow.

The detail endpoint is:

```text
GET /api/v1/journeys/{run_id}
```

Optional segment query parameters must be supplied together:

- departure_stop_sequence
- arrival_stop_sequence

Details include ordered scheduled stops, passenger permissions, run status,
version and registered source metadata.

Cancelled runs remain viewable in details with their status.
Viewing a cancelled schedule does not make it a feasible journey.

Unregistered provenance returns `source: null`.
The UI explains that missing metadata does not establish freshness.

Source registration and retrieval times are not live railway update times.

## Staff identity and local testing

Apply the database migrations before provisioning staff accounts.

From the repository root, with the backend environment active:

```powershell
python scripts/provision_staff.py --username local_controller --display-name "Local Controller" --role controller
```

Enter and confirm a password containing 15 to 128 characters.
Password input is hidden in the terminal.
Store the password privately; do not put it in Git or shared screenshots.

The command creates an individual account and role assignment.
It rejects an existing username rather than replacing its password or role.

Supported initial roles are controller and administrator.
Administrator permissions are explicitly mapped.

To create a separate local test account:

```powershell
python scripts/provision_staff.py --username local_controller_test --display-name "Local Test Controller" --role controller
```

Use a new username if that account already exists.
Provisioning does not provide a password-reset workflow.

Open http://127.0.0.1:5173 and select Staff access.
Sign in using the account and password you provisioned.

Staff access displays the account, roles, permissions and absolute expiry.
Browser refresh and reopening Staff access restore a valid session.
Refresh session checks the current account and session against the backend.

The default absolute lifetime is eight hours.
The default idle timeout is thirty minutes.
The server enforces both limits.

Sign out revokes the session and clears its cookie.
An unconfirmed sign-out displays an error rather than reporting success.

Journey search remains public.
Incident and timetable management interfaces are implemented separately.

Authentication endpoints are:

- POST /api/v1/auth/login
- GET /api/v1/auth/me
- POST /api/v1/auth/logout

Login requires JSON and a configured browser Origin.
Authenticated mutations require an allowed Origin and the session CSRF token.
The frontend sends cookies through same-origin API requests via the Vite proxy.

Session tokens are delivered through HTTP-only cookies.
The database stores their hashes.
The frontend does not persist session or CSRF state in localStorage.

## Identity-record cleanup

Preview eligible records:

```powershell
python scripts/cleanup_identity.py
```

The default preview does not delete records.

Apply one bounded cleanup batch explicitly:

```powershell
python scripts/cleanup_identity.py --apply
```

Default retention is seven days for expired or revoked sessions and one day
for expired login-rate windows.

The default batch limit is 500 records per table.
For supported options, run:

```powershell
python scripts/cleanup_identity.py --help
```

Cleanup preserves users, role assignments, current sessions and current
rate-limit windows. Applied changes are transactional.

Authentication rejects expired and revoked sessions even before cleanup.
Cleanup is operator-run; deployment scheduling remains to be configured.

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

Run PostgreSQL and apply migrations before running database tests.

Most database tests use isolated fixtures and roll back their changes.
Concurrency tests use independent connections and committed test records,
then remove their own generated records.

Never configure tests to use a deployed production database.

## Frontend checks

From the frontend directory:

```powershell
npm run lint
npm run build
npm test
```

The build includes TypeScript checking.
Frontend component tests substitute API responses.
They do not require the backend or PostgreSQL.

## Linux and macOS differences

Use a compatible Python 3.13 installation, Node and Docker Compose.

Install uv in a separate tool environment:

```bash
python3.13 -m venv "$HOME/.local/share/railconnect-tools/uv"
"$HOME/.local/share/railconnect-tools/uv/bin/python" -m pip install "uv==0.13.0"
```

From the repository root, create and sync the backend environment:

```bash
python3.13 -m venv --prompt RailConnect-AI backend/.venv
"$HOME/.local/share/railconnect-tools/uv/bin/uv" sync --project backend --extra dev --locked
source backend/.venv/bin/activate
```

Create local configuration only for a fresh checkout:

```bash
cp .env.example .env
```

Generate and configure the database password as described above.
Configure staff session settings for the intended environment.

Python, Docker Compose and npm commands otherwise follow the same workflow.
Use `/` path separators and `backend/.venv/bin/python` for explicit
interpreter paths.

Check dependency compatibility with:

```bash
"$HOME/.local/share/railconnect-tools/uv/bin/uv" pip check --python backend/.venv/bin/python
```

This documents platform differences; it does not claim that a separate
macOS clean-checkout verification has been performed.

## Dependency changes

Declare backend dependencies in `backend/pyproject.toml`.
After an intentional dependency change on Windows:

```powershell
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" lock --project backend
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" sync --project backend --extra dev --locked
```

Run checks and commit the updated `pyproject.toml` and `uv.lock`.

Use npm from the frontend directory to change frontend dependencies.
Commit both `package.json` and `package-lock.json`.

## Continuous integration

`.github/workflows/ci.yml` runs on pushes and pull requests.

Backend checks use the committed uv lockfile and a temporary PostgreSQL
database. Frontend checks use `npm ci` and the committed npm lockfile.

CI runs lint, formatting where configured, type checking, migrations,
schema checks, station seeding, timetable preview/import, dated-run
materialization, backend tests, frontend tests and the frontend build.

CI does not establish that deployment or assistant evaluation is complete.
