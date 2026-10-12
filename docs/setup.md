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

The `.env` file is ignored by Git.
Environment variables override values from `.env`.
Run backend commands from the repository root so configuration is found.

## Start PostgreSQL

Open Docker Desktop and wait for its engine to start.

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
python scripts/seed_timetable.py
python scripts/seed_timetable.py
python scripts/materialize_demo_runs.py --start-date 2026-10-12 --end-date 2026-10-18
python scripts/materialize_demo_runs.py --start-date 2026-10-12 --end-date 2026-10-18
```

On a fresh database, the first station seed inserts 30 stations.
The second reports 0 inserted and 30 already present.

The first timetable seed inserts 12 demonstration services and 42 stops.
Repeated seeding inserts nothing and verifies existing records.
Conflicting data causes an error and rolls back the seed transaction.

For demonstration imports, omitted boarding and alighting permissions
follow the presence of departure and arrival times respectively.
Explicit permission values are preserved.

Dated runs must be prepared before journey search can return them.
On a fresh run table, the example above creates 70 runs.
Repeating it verifies 70 existing runs and inserts nothing.
The 14 skipped service dates reflect weekday and weekend operating rules.

The materialization command supports at most 31 days per invocation
and requires a development or test environment.
Prepare other date ranges explicitly.
All writes in one invocation are committed together or rolled back.

Run stops store scheduled timestamps in UTC.
Search and display use the passenger's boarding date in Asia/Colombo.
An overnight run may have started on the previous date.
Search does not create runs.

Timetable schedules are fictional and include daily, weekday, weekend,
reverse-direction and overnight examples.

These are selected demonstration stations, not the complete railway network.
Codes beginning with `DEMO_` are project identifiers.
The data does not provide live timetables or service updates.

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

Request logs appear as JSON in the backend terminal.
Stop the server with Ctrl+C.

## Frontend installation and startup

In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173.

Vite forwards `/api` requests to the local backend during development.
The backend must be running to load stations.
Deployment requires its own API routing configuration.

## Backend checks

From the repository root, with the backend environment active:

```powershell
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" pip check --python backend/.venv/Scripts/python.exe
python -m ruff check --config backend/pyproject.toml backend/src backend/tests backend/migrations scripts
python -m ruff format --check --config backend/pyproject.toml backend/src backend/tests backend/migrations scripts
python -m mypy --config-file backend/pyproject.toml backend/src/railconnect
python -m pytest -c backend/pyproject.toml
```

Run PostgreSQL and apply migrations before running repository tests.

## Frontend checks

From the frontend directory:

```powershell
npm run lint
npm run build
npm test
```

Frontend interaction tests substitute API responses.
They do not require the backend or PostgreSQL.

## Dependency changes

Declare backend dependencies in `backend/pyproject.toml`.
After an intentional dependency change:

```powershell
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" lock --project backend
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" sync --project backend --extra dev --locked
```

Run checks and commit the updated `pyproject.toml` and `uv.lock`.

Use npm from the frontend directory to change frontend dependencies.
Commit both `package.json` and `package-lock.json`.

## Continuous integration

`.github/workflows/ci.yml` runs on pushes and pull requests.

Backend checks use the committed uv lockfile and a temporary PostgreSQL database.
Frontend checks use `npm ci` and the committed npm lockfile.

CI runs lint, formatting where configured, type checking, builds,
migrations, schema checks, seeding, and automated tests.
