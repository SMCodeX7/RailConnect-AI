# RailConnect AI

RailConnect AI is a portfolio pilot for searching direct railway journeys,
reporting disruptions, and reviewing them through a staff workflow. It uses
fictional schedules for selected Sri Lankan stations. Live railway updates
are unavailable.

## What you can do

- **Journey search** — Find prepared direct journeys by station and boarding
  date. Open a result to see scheduled stops, boarding and alighting
  permissions, and timetable provenance.
- **Disruption information** — See verified disruption effects, estimated
  arrivals when available, and feasible direct alternatives.
- **Passenger assistant** — Ask questions about the passenger guide or look
  up a demonstration journey or verified incident. Answers cite their
  guide excerpt or record when available.
- **Passenger reporting** — Submit an observation and receive a reference
  with a pending review status.
- **Staff access** — Review reports, manage verified incidents, and use
  timetable import or audit features when the account has permission.

## Run locally

The app uses React and TypeScript, a FastAPI backend, and PostgreSQL with
Alembic migrations. Follow the [development setup guide](docs/setup.md) to
install dependencies, configure the database, seed the timetable, prepare
dated runs, and start both servers.

Once the app is running, open <http://127.0.0.1:5173>. For the demo journey
below, prepare its date from the repository root with the backend environment
active:

```powershell
python scripts/materialize_demo_runs.py --start-date 2026-11-16 --end-date 2026-11-16
```

1. In **Journey search**, select **Jaffna** to **Colombo Fort** for
   **16 November 2026**. Open **Demo Northern Return** to see its scheduled stops.
2. In **Passenger assistant**, ask **How do I report a disruption?** The
   response should cite the RailConnect passenger guide.
3. In a local demo database, submit a clearly labelled synthetic disruption
   report and check that its receipt shows **Pending**. Use a provisioned
   staff account to open the report in the review queue.

All displayed journey times use Sri Lanka time (`Asia/Colombo`). Journey
search requires dated runs prepared for the selected date.

## Validation

Local pilot checks passed on 17 November 2026.

| Check | Result |
| --- | --- |
| Backend tests | 653 passed |
| Frontend tests | 135 passed |
| Playwright browser tests | 4 passed |
| Frontend lint and production build | Passed |
| Alembic schema check | No new upgrade operations detected |

The independent assistant evaluation passed 51 of 60 cases. It correctly
declined all 20 unsupported questions and returned its fallback for nine
supported questions. See the [evaluation results](evaluation/assistant/README.md)
for the breakdown.

## Project documentation

- [Development setup](docs/setup.md)
- [Demonstration timetable data card](docs/data-card.md)
- [Incident workflow verification](docs/incident-workflow-check.md)
- [Roadmap](docs/roadmap.md)
