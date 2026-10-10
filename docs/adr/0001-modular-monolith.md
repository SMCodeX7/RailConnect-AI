# ADR 0001: Start with a modular monolith

- Date: 2026-10-10
- Status: Accepted
- Initial release: v0.1 foundation

## Context

RailConnect AI starts as a portfolio pilot developed by one person.
It needs a manageable setup and clear boundaries that support later
journey, incident, booking, and maintenance features.

## Decision

Use:
- FastAPI with Python for the backend.
- React with TypeScript for the frontend.
- PostgreSQL for persistent data.
- Alembic for database migrations.

Start with one backend application organized into domain modules.
Each implemented module separates API routes, schemas, business
services, database models, and repositories where needed.

The frontend separates pages, components, API calls, and state handling
by feature.

Add modules when their features are implemented. Avoid empty scaffolding
for every future release.

## AI boundaries

AI coordinators interpret requests and explain authorized evidence.
Application services enforce permissions, state transitions, and
database transactions.

Models cannot independently approve incidents or confirm bookings.

## Consequences

Benefits:
- Simple local development and deployment.
- Clear code ownership and responsibilities.
- Critical workflows can use database transactions.

Tradeoffs:
- Backend modules deploy together.
- Module boundaries must be maintained during development.

## When to reconsider

Consider extracting a service only when measured scaling needs,
deployment requirements, or independent team ownership justify it.
Record that decision in a new ADR.