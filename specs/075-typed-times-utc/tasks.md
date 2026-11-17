---
description: "Task list for 075 store typed times in UTC"
---

# Tasks: Store Typed Times in UTC

**Input**: `specs/075-typed-times-utc/` (spec.md, plan.md, research.md, data-model.md, contracts/stored-times.md, quickstart.md)

**Tests**: required by the constitution (TDD). Write each test first and watch it fail before changing code. Tests that need a zone save `America/New_York` on the account. Tests that need "now" or "today" pin `clock_service._utc_now`.

## Phase 1: Setup

- [x] T001 Confirm the branch `075-typed-times-utc` and that `.specify/feature.json` points at `specs/075-typed-times-utc`. Run the full suite once as the baseline (`.venv/bin/python -m pytest -q`).

## Phase 2: Foundational (blocks every story)

**Purpose**: pure zone math and the service wrappers everything else calls (research §1, §2, §11, §12).

- [x] T002 [P] Tests first in new `tests/db/test_frames.py`:
  - **`to_utc`**:
    - `to_utc("2026-11-16", "17:39", "America/New_York")` returns `"2026-11-16T22:39:00.000000Z"`.
    - In July, `"09:00"` returns `13:00` UTC.
    - The nonexistent `2026-03-08 02:30` returns `07:30` UTC, which is 3:30 AM EDT.
    - The repeated `2026-11-01 01:30` returns `05:30` UTC, the first (EDT) occurrence.
    - With zone `UTC` it is the identity.
  - **`from_utc`**: returns the aware local `datetime`. It accepts `…Z` with or without microseconds.
  - **`end_of_day_utc("2026-11-16", "America/New_York")`** returns `"2026-11-17T04:59:59.999999Z"`.
  - **`STORED_FORMAT`** is `"%Y-%m-%dT%H:%M:%S.%fZ"`.
- [x] T003 Implement T002 in `app/db/frames.py`: add `STORED_FORMAT`, `to_utc`, `from_utc` and `end_of_day_utc` using `zoneinfo` with `fold=0`. Leave `ride_wall`/`period_wall` in place for now; T013 removes them.
- [x] T004 [P] Tests first in `tests/services/test_clock_service.py`:
  - **`clock_service.to_utc(day, hhmm)`** uses the saved zone.
  - **`to_local(value)`** returns `"YYYY-MM-DDTHH:MM"` in the saved zone, or `""` for blank.
  - **`today()`**: with `_utc_now` pinned to `2026-11-17T01:00Z` and the zone set to New York, it returns `2026-11-16`.
  - **`keep_or_convert(stored, day, hhmm)`**:
    - The same local date and minute returns `stored` unchanged. This includes a Strava value with seconds (`…T19:26:41.000000Z` stays).
    - A stored value in the second `01:30` of 2026-11-01 (EST, `06:30Z`) stays when `01:30` is submitted.
    - A changed minute returns `to_utc(...)`.
- [x] T005 Implement T004 in `app/services/clock_service.py`. `today()` uses `_utc_now()`. Do not remove the old functions yet; T013 removes them.

**Checkpoint**: the new helpers are tested, and the app's behavior hasn't changed yet.

## Phase 3: User Story 1 - Typed times are recorded like Strava times (P1) 🎯 MVP

**Goal**: rides, install and removal moments, and part-add install dates are stored as UTC and shown with the zone abbreviation. Edit forms prefill local time, and an unchanged save keeps the instant.

**Independent test**: zone New York, add a manual ride at 2026-11-16 5:39 PM. It is stored as `2026-11-16T22:39:00.000000Z`, and the Rides list shows `2026-11-16 5:39PM EST` in the same format as Strava rows.

- [x] T006 [P] [US1] Tests first in `tests/services/test_ride_service.py`:
  - Zone New York:
    - A manual ride on 2026-11-16 at 17:39 is stored as `…T22:39:00.000000Z`.
    - A blank time is stored as noon local (`…T17:00:00.000000Z`).
    - A July date uses EDT.
  - **`update_ride`**:
    - Unchanged date and time keep the stored text, including a Strava ride's seconds.
    - A changed time converts.
- [x] T007 [US1] Implement T006 in `app/services/ride_service.py`:
  - `_occurred_at(day, time)` calls `clock_service.to_utc(day, time or "12:00")`.
  - `update_ride` uses `clock_service.keep_or_convert` against the stored `occurred_at`.
- [x] T008 [P] [US1] Tests first in `tests/services/test_component_history_service.py`:
  - **`moment(day, time)`**, zone New York:
    - `2026-11-16` at `08:00` returns `…T13:00:00.000000Z`.
    - A blank time returns local midnight in UTC (`…T05:00:00.000000Z`).
    - Both blank returns now (unchanged).
  - **`check_not_future`**: rejects a UTC instant later than now and accepts one a minute ago, with `_utc_now` pinned.
  - **Overlap error**: the message shows local dates.
  - **Editing a period**: unchanged installed and removed fields keep their stored text.
  - **Adding a part** with an install date via `/builder/add` stores UTC.
- [x] T009 [US1] Implement T008 in `app/services/component_history_service.py`:
  - `moment()` goes through `clock_service.to_utc`.
  - `check_not_future` compares with the current UTC instant in `STORED_FORMAT`, not `now_in_zone_moment`.
  - The clash message uses `clock_service.to_local(...)[:10]`.
  - The period edit applies `keep_or_convert` to installed and removed.
- [x] T010 [P] [US1] Tests first in `tests/routers/test_rides.py`:
  - Zone New York: a manual row and a Strava row both render as `date time EST`.
  - A Strava ride's Edit form prefills the local date and time, not UTC (US1 scenario 6).
  - A manual ride's Edit form prefills what was typed.
- [x] T011 [P] [US1] Tests first in `tests/routers/test_component_history.py`:
  - Zone New York: a part's and a bike's Install History show typed and recorded moments with `EST`/`EDT`.
  - The Log/Edit period form prefills local date and time.
  - The period Rides page header shows `local_time` values.
- [x] T012 [US1] Implement T010 and T011:
  - `app/templates/rides/log.html`: every row uses `local_time`; the period header too.
  - `app/templates/rides/form.html`: prefill `(ride.occurred_at|to_local)[:10]` and `[11:16]`.
  - `app/templates/components/install_period_form.html`: `to_local` instead of `to_wall`.
  - `app/templates/components/install_history.html` and `app/templates/bikes/install_history.html`: `local_time` instead of `wall_time`.
  - `app/main.py`: register `to_local`.
- [x] T013 [P] [US1] Tests first in `tests/db/test_mileage_period_frames.py`, `tests/db/test_mileage_at.py` and `tests/db/test_mileage_usage.py`:
  - Rewrite the mixed-clock cases (015 FR-013, 051) with UTC inputs for typed times, keeping each case's expected rides and miles.
  - Add a regression case for the Background bug: zone New York, a Strava ride at `19:26Z` (2:26 PM EST) and a schedule starting at 3:00 PM local stored as `20:00Z`. `usage_since` must not count the ride, and `bike_mileage_at` at `20:00Z` must include it.
  - Assert that `ride_wall` and `period_wall` are no longer registered SQL functions.
- [x] T014 [US1] Implement T013:
  - `app/db/mileage.py`: `_WINDOWS` and the period ride filter use `installed_at`, `COALESCE(removed_at, '9999')` and `occurred_at` directly.
  - `app/db/maintenance.py`: the past-part windows use the raw columns.
  - `app/db/frames.py`: delete `ride_wall` and `period_wall` and their registration.
  - `app/services/clock_service.py`: delete `format_wall`, `to_wall`, `_wall_moment` and `now_in_zone_moment`, and remove the `wall_time`/`to_wall` filters in `app/main.py`.
  - Update both module docstrings to the new rule.

**Checkpoint**: new typed times are UTC everywhere they're typed, shown with an abbreviation, and compared plainly. Existing data isn't converted yet (US3).

## Phase 4: User Story 2 - Maintenance entries keep the date the rider typed (P1)

**Goal**: timed entries have a UTC instant for comparisons and keep their local date for display, order and date-based schedules.

**Independent test**: zone New York, log 2026-11-16 at 9:00 PM and an untimed entry on 2026-11-17. The first reads `2026-11-16 9:00PM EST`, sorts below the second, and a months schedule from it counts from 2026-11-16.

- [x] T015 [US2] Add `app/db/migrations/0018_maintenance_performed_instant.sql` (`ALTER TABLE maintenance_log_entry ADD COLUMN performed_instant TEXT;`). Add a test in `tests/db/test_connection.py` that the column exists after `run_migrations`.
- [x] T016 [P] [US2] Tests first in `tests/db/test_maintenance.py`:
  - `create` and `update` store `performed_instant`, and the model exposes it (`app/models/rows.py`).
  - `list_past_for_bike` and `list_past_for_component` place an entry by `performed_instant` against UTC windows.
- [x] T017 [P] [US2] Tests first in `tests/services/test_maintenance_service.py`, zone New York:
  - **`log_maintenance`** at 2026-11-16 21:00 stores `performed_at = "2026-11-16"`, `performed_time = "21:00"` and `performed_instant = "2026-11-17T02:00:00.000000Z"`.
  - **Untimed entry**: stores `end_of_day_utc`.
  - **`entry_moment`** returns `performed_instant`.
  - **Mileage at service**: a Strava ride at 2:26 PM EST counts before a 3:00 PM entry (spec Background).
  - **Editing**: an unchanged date and time keeps the instant.
  - **History order**: an untimed entry sorts by the local time of `created_at`.
- [x] T018 [US2] Implement T016 and T017:
  - `app/db/maintenance.py`: `create`/`update` take `performed_instant`, and `_ENTRY_AT = "m.performed_instant"`.
  - The `MaintenanceLogEntry` model in `app/models/rows.py` gains `performed_instant`.
  - `app/services/maintenance_service.py`:
    - `log_maintenance` and `update_entry` compute the instant with `clock_service.to_utc` or `frames.end_of_day_utc`, and use `keep_or_convert` on edit.
    - `entry_moment` returns `performed_instant`.
    - The mileage-at moment uses it.
    - `_sort_key` uses `clock_service.to_local(entry.created_at)[11:16]` for untimed entries.
- [x] T019 [P] [US2] Tests first in `tests/routers/test_maintenance.py`: a timed entry renders `performed_instant|local_time` (`2026-11-16 9:00PM EST`), and an untimed one renders the date alone.
- [x] T020 [US2] Implement T019 in `app/templates/maintenance/history_list.html`.
- [x] T021 [P] [US2] Tests first in `tests/services/test_schedule_follow_maintenance.py` and `tests/services/test_schedule_intervals.py`:
  - A months schedule created after a 9 PM entry gets `baseline_date` of the local date and a `baseline_at` equal to the entry's instant.
  - A schedule with no `baseline_at` counts from local midnight of `baseline_date` in UTC.
- [x] T022 [US2] Implement T021 in `app/services/schedule_service.py` and `app/services/maintenance_service.py`: replace every `f"{baseline_date}T00:00:00.000000Z"` fallback with `clock_service.to_utc(baseline_date, "00:00")`.

**Checkpoint**: maintenance compares by instant and stays on its local date.

## Phase 5: User Story 3 - Existing typed times are converted once (P1)

**Goal**: one all-or-nothing conversion after a database copy, never repeated. Old backups are converted on restore.

**Independent test**: a seeded database with every stored form from the US3 table, zone New York. After `run_migrations`:
- each value matches the table;
- totals and histories are identical (SC-002);
- a copy file exists;
- running again changes nothing (SC-007).

- [x] T023 [P] [US3] Tests first in new `tests/db/test_typed_times.py` (`convert(conn, zone)`), one case per US3 table row:
  - A manual ride converts, deleted ones too.
  - A Strava ride, edited or not, is unchanged.
  - Whole-minute install and removal moments convert, and ones with seconds are unchanged.
  - A timed entry gets its instant and an untimed one `end_of_day_utc`, with `performed_at`/`performed_time` unchanged.
  - **`baseline_at`**:
    - NULL is unchanged, and so is the 1970 marker.
    - `…T23:59:59.999999Z` becomes the end of that local day.
    - A whole minute converts.
    - Other values are unchanged.
  - Created, updated, synced, completed and notified columns are unchanged.
  - Zone `UTC` changes no value.
- [x] T024 [US3] Implement T023 in new `app/db/typed_times.py`:
  - `convert(conn, zone)` does parameterized `UPDATE`s, row by row.
  - `convert_database(conn)` reads the zone from `account`, else UTC.
  - `has_rows(conn)` reports whether anything needs converting.
- [x] T025 [P] [US3] Tests first in `tests/db/test_connection.py`:
  - `run_migrations` records `0019_typed_times_utc` in `schema_version` after the `.sql` files.
  - A second run converts nothing (SC-007).
  - A failure inside the step (monkeypatched `convert` raising) leaves every row and `schema_version` unchanged, and the next run converts.
  - With rows present, a copy `<stem>-before-075-<YYYY-MM-DD><suffix>` appears beside `DATABASE_PATH` and opens as a valid database with the old values.
  - An empty database gets no copy.
  - A copy that cannot be written (read-only folder) raises, logs an error naming the path, and converts nothing.
- [x] T026 [US3] Implement T025 in `app/db/connection.py`:
  - Add `DATA_STEPS = [("0019_typed_times_utc", typed_times.convert_database)]`, run after the SQL migrations.
  - Each step runs in one transaction with its `schema_version` insert.
  - The pre-update copy uses `sqlite3.Connection.backup`.
  - Log one info line with counts per table and the copy path.
- [x] T027 [P] [US3] Test for unchanged totals in `tests/db/test_typed_times.py`. Seed New York data:
  - Strava rides near typed period boundaries and maintenance times;
  - nested part periods (064);
  - past-part maintenance (066).

  Then:
  - Record before the step: every bike and part total, every period's Miles and Rides (053), and each maintenance history's rows in order.
  - Run `run_migrations` and `recompute_all_component_totals`.
  - Assert they are identical (FR-007, SC-002).
- [x] T028 [P] [US3] Tests first in `tests/services/test_backup_service.py`:
  - A new backup has `"format": 2` and includes `performed_instant`.
  - Restoring a format-1 file with `timezone = "America/New_York"` converts its typed times by the US3 table and recomputes totals.
  - Restoring format 2 converts nothing.
  - Other formats are refused, as today.
- [x] T029 [US3] Implement T028 in `app/services/backup_service.py`: set `FORMAT = 2`, accept `{1, 2}`, and on 1 call `typed_times.convert(conn, <backup timezone or "UTC">)` inside the restore transaction before recomputing totals.

**Checkpoint**: the update is safe to deploy against the real database.

## Phase 6: User Story 4 - Changing the zone later (P2)

**Goal**: a zone change shifts every instant's display, and untimed entries keep their date.

**Independent test**: switch New York to Los Angeles. The manual ride reads `2:39PM PST`, the 9 PM entry `6:00PM PST`, untimed entries keep their dates, and totals are unchanged.

- [ ] T030 [P] [US4] Tests first in `tests/services/test_settings_service.py`: `set_timezone` to Los Angeles:
  - recomputes a timed entry's `performed_at`/`performed_time` from its instant;
  - recomputes an untimed entry's instant as the end of its day in Los Angeles;
  - leaves rides, periods and schedules untouched;
  - leaves bike and part totals unchanged.
- [ ] T031 [US4] Implement T030:
  - `maintenance_service.follow_zone(zone)` loops over entries, using a `maintenance_db` update function.
  - `settings_service.set_timezone` calls it after saving the zone.
- [ ] T032 [P] [US4] Route test in `tests/routers/test_settings.py` (or `test_rides.py`): after saving Los Angeles, the Rides list and Maintenance history show `PST` times three hours earlier (SC-004).

## Phase 7: User Story 5 - "Today" is the rider's date (P2)

**Goal**: due dates, notifications and Mark done use the saved zone's date.

**Independent test**: `_utc_now` pinned to `2026-11-17T01:00Z`, zone New York. Today is 2026-11-16 everywhere.

- [ ] T033 [P] [US5] Tests first in `tests/services/test_schedule_service.py` and `tests/services/test_notification_service.py`, with `_utc_now` pinned to `2026-11-17T01:00Z` and zone New York:
  - Days left and late use 2026-11-16.
  - `complete_schedule` logs `performed_at = "2026-11-16"` and sets `baseline_date` to it.
  - `check_due_schedules` uses 2026-11-16.
  - `_baseline_for` with no entry uses the local date of `created_at`, and the local date of the earliest `installed_at`.
  - The trailing pace window starts at local midnight 90 days back.
- [ ] T034 [US5] Implement T033:
  - `app/services/schedule_service.py`: `_today` returns `today or clock_service.today()`; local dates in `_baseline_for`; `_trailing_pace`/`_trailing_usage_pace` use `clock_service.to_utc(start_day, "00:00")`.
  - `app/services/notification_service.py`: `today or clock_service.today()`.

## Phase 8: Polish & Cross-Cutting

- [ ] T035 [P] Settings copy (FR-013): a test in `tests/routers/test_settings.py` that the Time zone card no longer says typed times are shown as typed, and says times are recorded in UTC and shown in this zone. Then edit `app/templates/settings/cards/timezone.html`.
- [ ] T036 [P] Amend the older specs (FR-014), each with an Amendments line pointing to 075:
  - `specs/015-component-install-history/spec.md` (FR-013)
  - `specs/023-settings-sync-and-timezone/spec.md` (FR-008, card copy)
  - `specs/036-twelve-hour-clock/spec.md`
  - `specs/038-maintenance-mileage-at-date/spec.md`
  - `specs/039-ride-moving-time/spec.md`
  - `specs/040-schedule-types-and-intervals/spec.md` (today, usage)
  - `specs/044-maintenance-history-order/spec.md`
  - `specs/067-backup-restore/spec.md` (format 2)

  Also add 075 notes where 049 and 051 are referenced (`CLAUDE.md` "Period boundaries" paragraph), and correct `specs/023-settings-sync-and-timezone/contracts/routes.md` if it describes typed-time display.
- [ ] T037 [P] Update `CLAUDE.md`:
  - Replace the typed-times wording in the Settings (023), Clock (036), Period boundaries (051) and Maintenance history paragraphs.
  - Append a "Typed times in UTC (feature 075)" paragraph covering `frames.to_utc`, `performed_instant`, `typed_times`/`DATA_STEPS`, the pre-update copy, backup format 2, `clock_service.today()` and `follow_zone`.
- [ ] T038 Grep `app/` and `tests/` for `wall_time`, `to_wall`, `period_wall`, `ride_wall`, `now_in_zone_moment`, `date.today()` (schedules and notifications) and `T00:00:00.000000Z` fallbacks. Each must be gone or justified.
- [ ] T039 Run the full suite (`.venv/bin/python -m pytest -q`). It must be green with no skipped new tests.
- [ ] T040 Quickstart sections 1–6 against a copy of the real database on the local check server (`scratchpad/proto/run.py`, `REAL=1`). Never against the live database or a local Docker container.

## Dependencies & Execution Order

| Phase | Depends on |
|---|---|
| Setup (T001) | nothing |
| Foundational (T002–T005) | Setup. Blocks every story. |
| US1 (T006–T014) | Foundational |
| US2 (T015–T022) | Foundational. T018 also needs T014, since both edit the past-window SQL in `app/db/maintenance.py`. |
| US3 (T023–T029) | US1 and US2. Converted data must be read by UTC-only code, and `performed_instant` must exist. |
| US4 (T030–T032) | US2 |
| US5 (T033–T034) | Foundational only. Can run beside US1 and US2. |
| Polish (T035–T040) | all stories |

Within each story, tests go before the code they cover, and services before templates.

## Parallel Opportunities

- T002 and T004 (different test files).
- US1: T006, T008, T010, T011 and T013 tests together; T007 and T009 together.
- US2: T016, T017, T019 and T021 tests together.
- US3: T023, T025, T027 and T028 tests together.
- US5 can run beside US2, since both touch `schedule_service.py` but in different functions. Do the edits one after the other.
- Polish: T035, T036 and T037 together.

## Implementation Strategy

1. **MVP**: Foundational, then US1 and US2 (new times are right).
2. **Required before deploying**: US3. Without it, existing typed times would be read as UTC and shift by 4–5 hours.
3. Add US4 and US5, then Polish.
4. One PR for the whole feature. Its description says the update is one-way and names the pre-update copy as the way back.
