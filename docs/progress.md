# Project progress

## Current checkpoint

Updated 2026-11-17. The v1.0 portfolio pilot is in release preparation on
`feat/pilot-release`. The UI polish is committed as `aeff9b0`.

- `main` includes dated journey search, staff access, timetable management,
  incident reporting and disruption effects, the passenger assistant, and
  pilot validation.
- `feat/pilot-release` updates the shared navigation, journey search and
  details, passenger assistant, report form and receipt, and staff review
  layout.
- The local browser walkthrough confirmed that a passenger can submit a
  synthetic report, receive a pending receipt, and have a controller review
  and reject it.

## Local validation

| Check | Result |
| --- | --- |
| Backend tests | 653 passed |
| Frontend tests | 135 passed across 18 files |
| Playwright browser tests | 4 passed |
| Frontend lint and production build | Passed |
| Alembic schema check | No new upgrade operations detected |

The independent passenger assistant evaluation passed 51 of 60 cases. All
20 unsupported questions were correctly declined. Nine supported questions
returned a fallback. See the [evaluation results](../evaluation/assistant/README.md).

## Known limitations

- The pilot uses fictional schedules and synthetic incidents. Live railway,
  fare, platform and seat availability data are unavailable.
- Journey search depends on dated runs prepared for the selected date.
- Some supported passenger guide questions return a fallback.
- Staff forms use report or incident references for some lookups.
- Incident reopening and self-service password recovery are outside the
  current pilot.

## Release work remaining

- [ ] Reconcile the roadmap with implemented and verified work.
- [ ] Finish the release notes and capture screenshots of the implemented UI.
- [ ] Verify the release candidate from a clean checkout and confirm CI
  against the pushed commit.
- [ ] Verify the HTTPS deployment, data persistence after restart, and
  backup restoration in a separate environment.
- [ ] Repeat the demo from reset fixtures and record the deployed commit.
- [ ] Tag the verified commit and publish the v1.0.0 release.

See the [roadmap](roadmap.md) for the release plan and the
[setup guide](setup.md) for local commands.
