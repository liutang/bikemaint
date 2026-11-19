---
description: "Task list for 081 exact mile conversion"
---

# Tasks: Exact Mile Conversion

**Input**: `specs/081-exact-mile-conversion/`. **Tests**: TDD. Write each test first and see it fail.

## Phase 1: Setup

- [ ] T001 Confirm the branch (master merged in) and `.specify/feature.json`, and run the full suite as the baseline.

## Phase 2: User Story 1 - New Strava rides use the exact mile (P1)

- [ ] T002 [US1] Test first in `tests/services/test_sync_service.py`: syncing an activity with `distance` 16093.44 stores `distance_miles == 10.0` (to 1e-9). Re-import does the same.
- [ ] T003 [US1] Set `METERS_PER_MILE = 1609.344` in `app/services/sync_service.py`. Update any test that hard-coded 1609.34 results (for example `16093.4 m` giving 10.0 mi becomes `pytest.approx`).

## Phase 3: User Story 2 - Rides already synced are corrected once (P1)

- [ ] T004 [P] [US2] Tests first in `tests/db/test_typed_times.py` for `exact_miles(conn)`:
  - These are rescaled by 1609.34/1609.344: an unedited Strava ride, one deleted by you, one deleted upstream, and one filtered out.
  - These are unchanged: an edited Strava ride, a manual ride, `bike.manual_baseline_mileage`, `mileage_adjustment.delta_miles`, and `maintenance_log_entry.mileage_at_service`.
  - It returns `{"ride_activity": n}`.
- [ ] T005 [US2] Implement `exact_miles(conn)` in `app/db/typed_times.py` as one parameterized UPDATE.
- [ ] T006 [P] [US2] Test first in `tests/db/test_typed_times.py`:
  - `run_migrations` on a database without `0022_exact_miles` in `schema_version` rescales once and records it.
  - A second run changes nothing.
  - No `-before-` copy is made.
  - Part totals are recomputed at startup (`app/main.py` already does it); assert through a bike total.
- [ ] T007 [US2] Add `("0022_exact_miles", typed_times.exact_miles, False)` to `connection.DATA_STEPS`.

## Phase 4: Polish

- [ ] T008 [P] Amend `specs/001-bike-maintenance-tracker/spec.md`: an Amendments line saying Strava distances use 1,609.344 m/mi since 081.
- [ ] T009 [P] `CLAUDE.md`: an "Exact miles (feature 081)" line.
- [ ] T010 Run the full suite, then run `quickstart.md` on a copy of an old-style database and record the result.
- [ ] T011 Run `/speckit-analyze` and resolve any CRITICAL or HIGH finding.

## Dependencies

T002–T003 and T004–T007 are independent. Polish comes last.
