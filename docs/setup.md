# Development setup

## Current environment

- Windows with PowerShell
- Python 3.13.7
- Node.js 22.20.0
- npm 11.12.1

Run all commands from the repository root.

## Backend installation

```powershell
python -m venv --prompt RailConnect-AI backend\.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
python -m pip install --no-deps -e ./backend
python -m pip check
```

The requirements file records the Windows development environment.
Cross-platform dependency locking is pending.

## Local configuration

Create the local configuration file once:

```powershell
Copy-Item .env.example .env
```

Edit `.env` for local settings. It is ignored by Git.
`.env.example` is the tracked configuration template.

Environment variables override values in `.env`.
Run the backend from the repository root so it finds `.env`.
Production configuration rejects debug mode.

## Start the backend

```powershell
python -m uvicorn railconnect.app:create_app --factory --reload --reload-dir backend/src --host 127.0.0.1 --port 8000
```

- Liveness: http://127.0.0.1:8000/health/live
- API documentation: http://127.0.0.1:8000/docs

Stop the server with Ctrl+C.

## Development checks

```powershell
python -m ruff format --config backend/pyproject.toml backend/src backend/tests --check
python -m ruff check --config backend/pyproject.toml backend/src backend/tests
python -m mypy --config-file backend/pyproject.toml backend/src/railconnect
python -m pytest -c backend/pyproject.toml
```

## VS Code interpreter

Select backend\.venv\Scripts\python.exe using
Python: Select Interpreter in the Command Palette.
