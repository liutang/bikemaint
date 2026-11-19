---
description: "Task list for 085 blended riding pace"
---

# Tasks: Blended Riding Pace

**Input**: `specs/085-blended-pace/`. **Tests**: TDD. Pin "today" with `clock_service._utc_now`.

## Phase 1: Setup

- [x] T001 Confirm the branch (master merged in) and `.specify/feature.json`, and run the suite as the baseline.

## Phase 2: Foundational

- [x] T002 [P] Tests first in `tests/db/test_mileage_usage.py` for `lifetime_ride_stats_for_bike(conn, bike_id)`, which returns (first ride instant, ride count, miles), and `lifetime_usage_for_bike(conn, bike_id)`, which returns (first timed ride instant, total seconds):
  - deleted, filtered-out and upstream-deleted rides are left out;
  - a bike with no rides gives `(None, 0, 0.0)`.
- [x] T003 Implement T002 in `app/db/mileage.py`, parameterized.

## Phase 3: User Story 1 - Due dates use the blended pace (P1)

- [x] T004 [P] [US1] Tests first in `tests/services/test_schedule_service.py`:
  - **The spec's example:** 28.7 mi in 90 days and 1,353.5 mi over 2,040 days, with 23.3 mi left, is due in 48 days.
  - **Rides and hours schedules** blend the same way.
  - **Hours** whole history starts at the first timed ride.
  - **No rides in 90 days** gives half the whole-history pace.
  - **A part in storage** has no usage date.
- [x] T005 [US1] Implement `_pace(conn, bike_id, today, unit)` in `app/services/schedule_service.py`, replacing `_trailing_pace` and `_trailing_usage_pace` in `_project`.

## Phase 4: User Story 2 - "Low confidence" means too little history (P2)

- [x] T006 [P] [US2] Tests first: 4 rides is low confidence and 5 isn't; 29 days of history is low confidence and 30 isn't. Whatever the last 90 days held doesn't matter. The time-side fallback is unchanged.
- [x] T007 [US2] Implement the `trusted` rule with `MIN_RIDES_FOR_CONFIDENCE = 5` and `MIN_HISTORY_DAYS_FOR_CONFIDENCE = 30`, and remove `MIN_RIDE_DAYS_FOR_CONFIDENCE`.
- [x] T008 [US2] Update existing projection, attention and notification tests that pinned the old 90-day pace or confidence. Each change must be explained by the new rule; record any surprises here. *Result: `_steady_bike` now spreads its 10 rides over 90 days, so both paces are equal and the old expected dates still hold. Two interval tests (10 rides in the last 10 days) now expect the blended 40 and 10 days. The local-midnight window test asserts the blended pace. No surprises.*

## Phase 5: Polish

- [x] T009 [P] Amend 001 research §4, 040 and 054 (Amendments), and update the CLAUDE.md "Schedules" paragraph. *054 was a change to 040, not its own folder, so 040's Amendments line covers it.*
- [x] T010 Run the full suite, run `quickstart.md` on a copy of live-shaped data (the Revolt chain should be due about 2027-01-05), and record the result. *Result (2026-11-18): suite 1,727 passed. The Revolt case is the spec's SC-001 test, built from the rider's live figures (28.7 mi in 90 days, 1,353.5 mi over 2,040 days, 23.3 mi left), giving 48 days and no low confidence. To confirm on the live instance after deploy.*
- [x] T011 Run `/speckit-analyze` and resolve any CRITICAL or HIGH finding. *Result: none.*
