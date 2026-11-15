# Project progress

## Current checkpoint

Updated 2026-11-15. The v1.0 portfolio pilot is in progress.

- `main` includes dated journey search and details, timetable provenance,
  staff sessions and incident reporting.
- `feat/timetable-management` adds protected preview and import, staff
  attribution and the administrator interface.
- The migration head is `8b42c6f3a9d1`.
- Local validation passed with 603 backend tests and 128 frontend tests across
  17 files. Lint, backend typing and schema checks, and the frontend build passed.
- Browser checks covered controller visibility, administrator preview,
  repeat import and preview clearing after the selected file changed.
- The browser repeat verified 12 services, inserted zero services and stops,
  and preserved the original CLI summary.
- The 18 timetable API tests cover permissions, exact-byte hashing, first-time
  attribution, repeat imports, stale preview conflicts and rollback.

## Next checkpoint

Commit the documentation and push `feat/timetable-management`. Verify both
GitHub CI jobs against the pushed commit before PR review. After merge and
local sync, start `feat/disruption-effects`.

See the [roadmap](roadmap.md) for the v1 plan.
