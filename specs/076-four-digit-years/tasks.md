---
description: "Task list for 076 four-digit years, two-digit typing"
---

# Tasks: Four-Digit Years, Two-Digit Typing

**Input**: `specs/076-four-digit-years/` (spec.md, plan.md, research.md, data-model.md, contracts/stored-times.md, quickstart.md)

**Tests**: required by the constitution (TDD). Write each test first and watch it fail before changing code.
- Tests that need a zone save `America/New_York`.
- Tests that need "now" or "today" pin `clock_service._utc_now`.

## Phase 1: Setup

- [ ] T001 Confirm the branch `076-four-digit-years` (master merged in) and that `.specify/feature.json` points at `specs/076-four-digit-years`. Run the full suite once as the baseline (`.venv/bin/python -m pytest -q`).

## Phase 2: Foundational (blocks every story)

**Purpose**: the year rule and the four-digit writer that every story uses (research §1, §4).

- [ ] T002 [P] Tests first in new `tests/models/test_typed_dates.py` for `full_year(text)`:
  - Short years become 20yy: `"0026-07-17"` → `"2026-07-17"`, `"0000-07-17"` → `"2000-07-17"`, `"0099-12-31"` → `"2099-12-31"`, `"0024-02-29"` → `"2024-02-29"`.
  - Normal years are unchanged: `"1900-01-01"` and `"2026-11-18"` stay as they are.
  - Years 100 to 1899 (`"0202-03-01"`, `"1899-12-31"`) raise `PydanticCustomError` with the message exactly "Enter a valid date".
  - Text that isn't `YYYY-MM-DD` is returned unchanged, so the field's own validation reports it.
- [ ] T003 Implement T002 in new `app/models/typed_dates.py`.
- [ ] T004 [P] Tests first in `tests/db/test_frames.py`:
  - `frames.stored(datetime(999, 1, 2, 3, 4, 5, tzinfo=timezone.utc))` returns `"0999-01-02T03:04:05.000000Z"`.
  - `to_utc("0021-04-18", "00:00", "UTC")` starts with `"0021-"`.
  - `end_of_day_utc("0021-04-18", "UTC")` starts with `"0021-"`.
  - These fail on Linux/glibc before the fix.
- [ ] T005 Implement T004 in `app/db/frames.py`: add `stored(dt)` (`f"{dt.year:04d}-" + dt.strftime("%m-%dT%H:%M:%S.%fZ")`) and use it in `to_utc` and `end_of_day_utc`.

**Checkpoint**: the helpers are tested; no form uses them yet.

## Phase 3: User Story 1 - A two-digit year means 20yy (P1)

**Goal**: every typed date reads 0 to 99 as 20yy, the bike's model Year does too, refused forms show four digits, and ride dates can't be in the future.

**Independent Test**: with New York saved, add a manual ride dated `0026-07-17` at 09:00. The Rides list shows `2026-07-17 9:00AM EDT`.

- [ ] T006 [P] [US1] Tests first in `tests/models/test_requests.py`:
  - `RideRequest(ride_date="0026-07-17", ...)` gives `date(2026, 7, 17)`.
  - The same for `MaintenanceLogRequest.performed_at`.
  - The same for `InstallPeriodRequest.installed_date` and `removed_date`, and `BuilderAddRequest.installed_date`, which give `"2026-07-17"`.
  - `"0202-03-01"` fails with the message "Enter a valid date" on each.
  - `BikeDetailsRequest(year="23", ...)` gives 2023, and `year="99"` fails with "Year must be between 1900 and …".
- [ ] T007 [US1] Implement T006 in `app/models/requests.py`:
  - a `mode="before"` validator calling `typed_dates.full_year` on those five fields (blank stays blank where it's optional);
  - in `BikeDetailsRequest._plausible_year`, a value from 0 to 99 gets 2000 added before the range check.
- [ ] T008 [P] [US1] Tests first in `tests/models/test_form_errors.py`:
  - `error_context` and `message_context` show `values["installed_date"] == "2026-03-01"` for a form that sent `"0026-03-01"`.
  - The same holds for `ride_date`, `performed_at` and `removed_date`.
  - A refused `"0202-03-01"` is shown as typed.
- [ ] T009 [US1] Implement T008 in `app/models/form_errors.py`: normalize those date keys in `values` with `full_year`, leaving refused text as typed.
- [ ] T010 [P] [US1] Tests first in `tests/services/test_ride_service.py`, with `_utc_now` pinned to `2026-11-18T15:00Z` and New York saved (10:00 AM EST):
  - `create_ride` refuses `day=2026-11-19` with "The ride date cannot be in the future.".
  - It refuses today at `11:00`, and accepts today at `09:30` and today with no time.
  - `update_ride` refuses the same, and nothing is saved.
  - A Strava upsert with a future date is unaffected (call `mileage_db.upsert_ride_activity` directly).
- [ ] T011 [US1] Implement T010 in `app/services/ride_service.py`: `check_not_future(day, time)` using `clock_service.today()` and `clock_service.to_utc`, called by `create_ride` and `update_ride` before saving.
- [ ] T012 [P] [US1] Route tests first:
  - `tests/routers/test_rides.py`:
    - posting `ride_date=0026-07-17` saves 2026-07-17;
    - a future date answers 422 with the message beside the date field;
    - a refused form shows the four-digit year.
  - `tests/routers/test_component_history.py`: Log a period with `installed_date=0025-03-01` saves 2025-03-01. An overlap refusal with typed `0025-…` re-renders `value="2025-03-01"`.
  - `tests/routers/test_maintenance.py`: Log maintenance with `performed_at=0026-01-05` saves 2026-01-05.
  - `tests/routers/test_bikes.py`:
    - Edit bike with `year=23` saves 2023;
    - the Edit form's Year hint reads "For example 2022 or 22.".
- [ ] T013 [US1] Make T012 pass:
  - in `app/routers/rides.py`, show the future-date `ValueError` on `field="ride_date"` (create and update);
  - change the Year hint in `app/templates/bikes/form.html`.

**Checkpoint**: US1 is complete; typed short years can't be stored any more.

## Phase 4: User Story 2 - Stored years always have four digits (P1)

**Goal**: every instant the app writes has a four-digit year (FR-004).

**Independent Test**: T004 passes on Linux.

- [ ] T014 [US2] Test first in `tests/db/test_frames.py`: `clock_service.keep_or_convert` and `component_history_service.moment` called for year 999 (calling `frames` directly, since forms now refuse it) return a `"0999-"` value. It passes after T005; it guards the other writers.
- [ ] T015 [US2] Audit every instant writer listed in plan.md (`grep -rn "strftime(" app`) and confirm each "now" writer uses the current year. Record the result in this task's note. No change is expected.

## Phase 5: User Story 3 - Short years already stored are repaired (P2)

**Goal**: stored years below 100 become 20yy, once at startup and on every restore (FR-006 to FR-010).

**Independent Test**: restore a backup whose period starts at `21-04-18T04:56:02.000000Z`, with New York saved. It starts at `2021-04-18T04:00:00.000000Z`.

- [ ] T016 [P] [US3] Tests first in `tests/db/test_typed_times.py` for `repair_short_years(conn, "America/New_York")`:
  - **Install moment:** `21-04-18T04:56:02.000000Z` becomes `2021-04-18T04:00:00.000000Z`, and `0021-04-18T04:56:02.000000Z` becomes the same.
  - **Manual ride:** `26-07-17T16:56:02.000000Z` becomes `2026-07-17T16:00:00.000000Z` (noon EDT).
  - **Maintenance entry:** `performed_at` `0021-04-18` becomes `2021-04-18`, and its `performed_instant` is repaired.
  - **Schedule start:** `baseline_at` is repaired, including the end-of-day form, which becomes `2021-04-19T03:59:59.999999Z`.
  - **Strava rides** with a short year are untouched.
  - **Normal values** are untouched.
  - **An unrepairable value** (forced into the table) stays unchanged and logs a warning with its table and id.
  - It returns counts per table.
- [ ] T017 [US3] Implement T016 in `app/db/typed_times.py`:
  - `repair_short_years(conn, zone)`, which parses short-year values by hand (research §5);
  - `repair_database(conn)`, which uses the saved zone.
- [ ] T018 [P] [US3] Tests first in `tests/db/test_connection.py`:
  - **Runs once:** `run_migrations` on a database holding a short year runs `0020_four_digit_years` once, records it in `schema_version`, and a second run changes nothing.
  - **No copy:** no `-before-` copy is made for it.
  - **Still copies for 075:** an older database still gets its 075 copy, once.
- [ ] T019 [US3] Implement T018 in `app/db/connection.py`:
  - `DATA_STEPS` entries become `(name, step, copy_first)`;
  - add `("0020_four_digit_years", typed_times.repair_database, False)`;
  - copy only when `copy_first`.
- [ ] T020 [P] [US3] Tests first in `tests/services/test_backup_service.py`:
  - A format-2 backup holding the old pads value restores with the period at `2021-04-18T04:00:00.000000Z`, and the part's total counts the rides since.
  - A format-1 backup with a `0021-…` typed date is converted and repaired.
  - A clean backup restores unchanged (the existing round-trip test still passes).
- [ ] T021 [US3] Implement T020 in `app/services/backup_service.py`: call `typed_times.repair_short_years(conn, zone)` after the format-1 conversion, or for every format, before totals are recomputed, in the same transaction.

**Checkpoint**: all stories complete.

## Phase 6: Polish and cross-cutting

- [ ] T022 [P] Amend `specs/075-typed-times-utc/spec.md`: an Amendments line for FR-001 (four-digit years; 0 to 99 mean 20yy, see 076).
- [ ] T023 [P] Amend `specs/075-typed-times-utc/contracts/stored-times.md`: in Storage, the year is always four digits, zero-padded (link to 076's contract).
- [ ] T024 [P] Amend `specs/006-feedback-round-2/spec.md`: an Amendments line saying a manual ride can't be dated in the future (076 FR-011).
- [ ] T025 [P] `CLAUDE.md`: a "Four-digit years (feature 076)" paragraph naming `typed_dates.full_year`, `frames.stored`, data step `0020_four_digit_years`, the restore repair, and the future-ride rule.
- [ ] T026 Run the full suite. Then run `quickstart.md` by hand on a local server with a copy of an old-style database, and record the result here.
- [ ] T027 Run `/speckit-analyze` for 076 and resolve any CRITICAL or HIGH finding.

## Dependencies

- Phase 2 (T002–T005) blocks every story.
- US1 (T006–T013) and US3 (T016–T021) are independent of each other once Phase 2 is done.
- US2 (T014–T015) needs only T005.
- Polish comes last.

## Parallel examples

- T002 and T004 (different files).
- T006, T008 and T010, after Phase 2.
- T016, T018 and T020, written together; implement them in order T017, T019, T021.

## Implementation strategy

Phase 2 and US1 first: they stop new short years and give two-digit typing (MVP). US3 then repairs anything older. US2 is a guard.
