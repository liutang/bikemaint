# Implementation Plan: Store Typed Times in UTC

**Branch**: `075-typed-times-utc` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)

## Summary

Every time the rider types (manual rides, install and removal moments, timed maintenance entries) is read in the saved zone and stored as UTC, like Strava rides. Display uses one filter (`local_time`) everywhere.

- **Maintenance entries** keep their local date and time columns for date-based uses, and gain a UTC `performed_instant` for comparisons with rides.
- **Comparisons**: the zone-aware SQL helpers `ride_wall`/`period_wall` are removed, and every comparison becomes a plain comparison of UTC text.
- **Existing data**: a one-time Python data step, run by `run_migrations` after a copy of the database, converts it. A format-1 backup is converted the same way on restore.
- **Today**: "today" becomes the saved zone's date.

Design decisions are in [research.md](research.md), storage in [data-model.md](data-model.md), and the rules in [contracts/stored-times.md](contracts/stored-times.md).

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, Jinja2, HTMX, standard-library `zoneinfo` + `tzdata` (already a dependency), `sqlite3` (online backup API for the pre-update copy)
**Storage**: SQLite. One new column (migration 0018) and one Python data step (`0019_typed_times_utc`) recorded in `schema_version`.
**Testing**: pytest. Tests that need a zone save New York. The default zone in tests stays UTC, where the conversion is the identity, so most existing tests are unaffected. Tests that pin "now" or "today" replace `clock_service._utc_now`.
**Target Platform**: self-hosted Linux container (UTC server clock)
**Project Type**: web service (server-rendered)
**Performance Goals**: the conversion is one pass over a single rider's rows (thousands at most), and the zone-change re-derivation is one pass over maintenance entries. Both are negligible.
**Constraints**:
- all-or-nothing conversion;
- copy before converting;
- never run twice;
- totals unchanged (spec FR-007).

**Scale/Scope**: about 12 app modules, 8 templates, their tests, and amendments to 7 older specs.

## Constitution Check

- **Fixed stack (Technology Stack)**: no new library. Zone math uses the standard library. PASS
- **Layout (Project Structure)**:
  - Zone math and the conversion live in `app/db/` (`frames.py`, new `typed_times.py`), because migrations run there and must not import services.
  - Services wrap them (`clock_service`).
  - Routers only pass form values through.
  - New tests mirror the files: `tests/db/test_frames.py`, `tests/db/test_typed_times.py`.

  PASS
- **I. Simplicity**: one explicit `DATA_STEPS` list instead of loading migration files dynamically. Two SQL functions are removed. PASS
- **III. TDD**: every task starts with a failing test. The conversion is tested per stored form (US3 table) and for run-once, rollback and copy. PASS
- **IV. Security**: no new input. Form fields are already validated by Pydantic, and all SQL stays parameterized. PASS
- **V. Observability**: the data step logs one info line with counts per table, the copy path, and an error naming the path if the copy fails. No ride notes or tokens are logged. PASS
- **Git**: one branch, one PR; atomic commits per phase. PASS

Re-checked after design: PASS. Nothing to track under Complexity.

## Project Structure

### Documentation (this feature)

```text
specs/075-typed-times-utc/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/stored-times.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

Amended outside this folder during implementation (spec FR-014):

| Spec | What changes |
|---|---|
| 015 | FR-013, the comparison clock |
| 023 | FR-008 and the Time zone card copy, display |
| 036 | Typed times without a zone |
| 038 | Mileage at service uses the instant |
| 039 | Manual moving-time rides are UTC |
| 040 | Today's date; usage since the starting point |
| 044 | Order of untimed entries |
| 051 | Its branch notes |
| 067 | Backup format 2 |

`CLAUDE.md` is updated too.

### Source Code

```text
app/db/frames.py                 # remove ride_wall, period_wall; add STORED_FORMAT, to_utc, from_utc, end_of_day_utc
app/db/typed_times.py            # NEW: convert(conn, zone), convert_database(conn) (zone from account), has_rows(conn)
app/db/connection.py             # DATA_STEPS after .sql migrations; pre-update copy; one transaction per step
app/db/migrations/0018_maintenance_performed_instant.sql   # NEW
app/db/mileage.py                # _WINDOWS and period filter use raw columns
app/db/maintenance.py            # _ENTRY_AT = performed_instant; past windows raw; insert/update take performed_instant; follow_zone rows
app/services/clock_service.py    # to_utc/keep_or_convert/to_local/today(); remove format_wall, _wall_moment, now_in_zone_moment
app/services/ride_service.py     # _occurred_at via clock_service; edit keeps unchanged instant
app/services/component_history_service.py  # moment() via clock_service; check_not_future in UTC; clash dates local; edit keeps unchanged
app/services/maintenance_service.py        # entry_moment = performed_instant; write instant on log/edit; follow_zone; _sort_key local created time
app/services/schedule_service.py           # _today = clock_service.today(); UTC fallbacks; local install and created dates; pace window local midnight
app/services/notification_service.py       # today = clock_service.today()
app/services/settings_service.py           # set_timezone calls maintenance_service.follow_zone
app/services/backup_service.py             # FORMAT 2; accept 1 and convert with the backup's zone
app/main.py                                # filters: drop wall_time/to_wall, add to_local
app/templates/rides/log.html, rides/form.html
app/templates/components/install_period_form.html, components/install_history.html, bikes/install_history.html
app/templates/maintenance/history_list.html
app/templates/settings/cards/timezone.html # FR-013 copy
tests/db/test_frames.py (NEW), tests/db/test_typed_times.py (NEW), tests/db/test_connection.py,
tests/db/test_mileage_period_frames.py (rewritten to UTC inputs), tests/db/test_mileage_at.py, tests/db/test_mileage_usage.py,
tests/services/test_clock_service.py, test_ride_service.py, test_component_history_service.py, test_maintenance_service.py,
test_schedule_service.py, test_notification_service.py, test_backup_service.py, test_settings_service.py,
tests/routers/ (Rides, Install History, Maintenance history, Settings display)
```

**Structure Decision**:

- Pure zone math and the one-time conversion sit in `app/db/` beside the migration runner.
- Everything rider-facing goes through `clock_service`.
- No new router or route.

## Phases (for /speckit-tasks)

1. **Foundation**: `frames` zone functions, then `clock_service` wrappers (`to_utc`, `to_local`, `keep_or_convert`, `today`). Pure, tested first.
2. **US1, typed times stored as UTC**: rides, install periods and part-add install dates write UTC. Edit forms prefill local and keep unchanged instants. One display filter. Comparisons drop `ride_wall`/`period_wall`.
3. **US2, maintenance dates**: migration 0018, `performed_instant` written on log and edit, `entry_moment`, `_ENTRY_AT`, history display and sort.
4. **US3, conversion**: `typed_times.convert`, the data step with copy, transaction and run-once, a test for unchanged totals on a seeded mixed database, and restore of format 1.
5. **US4, zone change**: `follow_zone` from `set_timezone`.
6. **US5, today**: `clock_service.today()` in schedules, notifications and Mark done; local dates in `_baseline_for`.
7. **Polish**:
   - Settings card copy;
   - spec amendments (FR-014) and `CLAUDE.md`;
   - full suite;
   - quickstart against a copy of the real database.

## Risks

- **Order of steps at startup**: the data step must run after migration 0018 and before `recompute_all_component_totals`. `run_migrations` already runs before the recompute in `main._lifespan`.
- **Older tests assume the mixed clock**: `test_mileage_period_frames.py` builds data with typed local times next to Strava UTC on purpose. It is rewritten with UTC inputs, keeping each case's expectation.
- **Deploying is one-way**: an older image misreads converted data. The pre-update copy is the way back (spec Edge Cases). The PR description says so.
