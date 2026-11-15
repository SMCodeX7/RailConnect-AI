# Development setup

## Install dependencies

Use Git, Python 3.13, Node.js 22.20.0 and Docker Compose. On Windows, open
Docker Desktop with Linux containers. Run backend commands from the
repository root.

For a fresh Windows checkout:

```powershell
python -m venv "$env:LOCALAPPDATA\RailConnectTools\uv"
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\python.exe" -m pip install "uv==0.13.0"
python -m venv --prompt RailConnect-AI backend\.venv
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" sync --project backend --extra dev --locked
.\backend\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` and retry.
Stop the backend before syncing dependencies on Windows.

On Linux or macOS:

```bash
python3.13 -m venv ~/.local/share/railconnect-tools/uv
~/.local/share/railconnect-tools/uv/bin/python -m pip install "uv==0.13.0"
python3.13 -m venv --prompt RailConnect-AI backend/.venv
~/.local/share/railconnect-tools/uv/bin/uv sync --project backend --extra dev --locked
source backend/.venv/bin/activate
```

## Start PostgreSQL and apply migrations

For a fresh checkout, copy `.env.example` to `.env` and set a private
`POSTGRES_PASSWORD`. Keep the existing database URL template. A PostgreSQL
volume retains the password used to initialise it.

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d db
docker compose --env-file .env -f infra/compose.yaml ps
```

Once the database is healthy:

```powershell
python scripts/check_database.py
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
```

The local PostgreSQL port is `5433`. Migration `8b42c6f3a9d1` adds optional
staff attribution to timetable import summaries.

## Prepare demo data

```powershell
python scripts/seed_stations.py
python scripts/preview_timetable.py
python scripts/seed_timetable.py
python scripts/materialize_demo_runs.py --start-date 2026-10-12 --end-date 2026-10-18
```

For a first-time staff import on a fresh database, seed the stations, import
through the staff panel, then materialise dated runs. Prepare the intended
search dates explicitly, up to 31 days per invocation. See the [data card](data-card.md).

## Run the app

In the backend terminal, from the repository root:

```powershell
.\backend\.venv\Scripts\Activate.ps1
python -m uvicorn railconnect.app:create_app --factory --reload --reload-dir backend/src --host 127.0.0.1 --port 8000
```

Check [backend readiness](http://127.0.0.1:8000/health/ready). In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Run `npm ci` on a fresh checkout or after dependency changes. Keep both
terminals running and open [RailConnect](http://127.0.0.1:5173). Vite proxies
`/api` to the backend. Use a trusted origin for staff actions.

## Staff access

Provision staff accounts from the repository root:

```powershell
python scripts/provision_staff.py --username local_controller --display-name "Local Controller" --role controller
python scripts/provision_staff.py --username local_admin --display-name "Local Administrator" --role administrator
```

Enter a private password of 15–128 characters when prompted. Provisioning
rejects existing usernames. Sign in through **Staff access**. Controllers
review reports and manage incidents. Administrators also have `audit.read`
and `timetable.manage`.

The server checks permissions on protected operations. Staff authentication
uses an HTTP-only cookie. Protected POST requests require an allowed Origin
and the session-bound `X-CSRF-Token` returned by login or session restoration.
See [ADR 0005](adr/0005-staff-identity-and-sessions.md) for session policy.

## Staff timetable import

1. As administrator, select `data/processed/demo_timetable.json` as the
   dataset and `data/processed/demo_timetable.source.json` as the source metadata.
2. Click **Preview import** and review the counts, service codes and conflicts.
3. Click **Confirm import** when the preview is ready.
4. To check preview invalidation, preview again and change either selected
   file. The preview and confirmation should disappear.

On a seeded database, the demo repeat verifies 12 existing services and inserts
zero services and stops. It retains the original summary. A CLI-created summary
can show **No staff account recorded**. After an uncertain import response,
preview again to check the current state before retrying.

Both endpoints require `timetable.manage`, a session, allowed Origin and CSRF.

| POST endpoint | Behaviour |
| --- | --- |
| `/api/v1/staff/timetable/imports/preview` | Reports planned changes and conflicts without writing timetable records. |
| `/api/v1/staff/timetable/imports` | Rechecks and imports in one transaction. |

Send JSON with `dataset_base64` and `metadata_base64`. The file limits are
5 MiB and 64 KiB respectively. SHA-256 uses the exact dataset bytes. A valid
preview with conflicts returns `200` and `can_import: false`. An import
conflict returns `409`. Prepare dated runs separately.

## Journey and incident workflows

Use the local [API reference](http://127.0.0.1:8000/docs) for request and
response schemas.

- [ADR 0004](adr/0004-dated-runs-and-timetable-provenance.md) documents journey
  dates, scheduled stops and provenance.
- [ADR 0003](adr/0003-incident-reporting.md) documents report submission,
  staff review, lifecycle changes, public responses and audit.
- [Incident workflow verification](incident-workflow-check.md) covers browser
  replay and repeatable API tests.

## Cleanup

Run without `--apply` to preview. Use `--help` for retention and batch options.

```powershell
python scripts/cleanup_identity.py
python scripts/cleanup_identity.py --apply
python scripts/cleanup_report_limits.py
python scripts/cleanup_report_limits.py --apply
```

## Validation

From the repository root with the backend environment active:

```powershell
& "$env:LOCALAPPDATA\RailConnectTools\uv\Scripts\uv.exe" pip check --python backend/.venv/Scripts/python.exe
python -m ruff check --config backend/pyproject.toml backend/src backend/tests backend/migrations scripts
python -m ruff format --check --config backend/pyproject.toml backend/src backend/tests backend/migrations scripts
python -m mypy --config-file backend/pyproject.toml backend/src/railconnect
python -m alembic -c backend/alembic.ini check
python -m pytest -c backend/pyproject.toml --tb=short
```

Use a migrated development or test database. The test database account needs
permission to create temporary schemas.

From `frontend`:

```powershell
npm run lint
npm run build
npm test
```

For dependency changes, commit the changed manifest and lockfile together.
In GitHub Actions, verify both CI jobs against the pushed commit.
