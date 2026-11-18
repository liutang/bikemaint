# Implementation Plan: Four-Digit Years, Two-Digit Typing

**Branch**: `076-four-digit-years` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

## Summary

There are five parts:

- **Reading typed years:** one pure function, `app/models/typed_dates.py: full_year(text)`, reads a typed `YYYY-MM-DD`.
  - Years 0 to 99 become 20yy, and the result is returned four-digit.
  - Years 100 to 1899 are refused with "Enter a valid date".
  - It backs a `mode="before"` validator on every typed date field (rides, maintenance, Log/Edit period, builder add).
  - It also normalizes the date fields in the `values` that re-rendered forms show.
- **The bike's model Year** reads 0 to 99 as 20yy before its range check.
- **Writing instants:** `frames` writes every instant with an explicit four-digit year instead of `strftime("%Y")`.
- **Repairing old values:** a new data step, `0020_four_digit_years`, repairs stored short years once. `backup_service.restore_backup` runs the same repair on restored rows.
- **Future rides:** `ride_service` refuses a ride dated after today, or today with a typed time later than now.

Decisions are in [research.md](research.md), the repair in [data-model.md](data-model.md), and the amended rule in [contracts/stored-times.md](contracts/stored-times.md).

## Technical Context

**Language/Version**: Python 3.12 (the container runs 3.13-slim)
**Primary Dependencies**: FastAPI, Pydantic v2, Jinja2, `zoneinfo` + `tzdata`. Nothing new.
**Storage**: SQLite. No schema change. One Python data step (`0020_four_digit_years`) is recorded in `schema_version`.
**Testing**: pytest.
- The four-digit writer is tested with a year below 1000, asserting `0999-…`, so the test fails on Linux/glibc even though the Mac pads.
- The repair is tested with the real broken pads value, `21-04-18T04:56:02.000000Z` in New York.
- Future-ride tests pin `clock_service._utc_now`.

**Target Platform**: self-hosted Linux container (glibc, UTC clock)
**Project Type**: web service (server-rendered)
**Performance Goals**: the repair is one pass over typed columns, for a single rider. Negligible.
**Constraints**:
- no copy before the repair (spec Assumptions);
- the repair never touches Strava rides;
- the step runs once and is all or nothing.

**Scale/Scope**: about 8 app modules, 1 template hint, their tests, and amendments to 075 (FR-001 and the contract) and 006.

## Constitution Check

- **Fixed stack**: no new library. PASS
- **Layout**:
  - The year rule is input validation, so it lives in `app/models/` (`typed_dates.py`, used by `requests.py` and `form_errors.py`).
  - The instant writer and the repair live in `app/db/` (`frames.py`, `typed_times.py`), because data steps run in `connection.run_migrations` and must not import services.
  - The future-ride rule is business logic in `ride_service`.
  - Tests mirror the files: `tests/models/test_typed_dates.py`, `tests/db/test_frames.py`, `tests/db/test_typed_times.py`, `tests/services/test_ride_service.py`.

  PASS
- **I. Simplicity**:
  - One function decides the year for every form, instead of a check per router.
  - `DATA_STEPS` entries gain one flag, whether a step copies the database first, instead of a second mechanism.

  PASS
- **III. TDD**: every task starts with a failing test. The Linux padding bug gets a test that fails on every platform, because it uses a year below 1000. PASS
- **IV. Security**: input is validated at the boundary (Pydantic `before` validators). SQL stays parameterized. PASS
- **V. Observability**:
  - The data step logs one info line with counts per table.
  - An unrepairable value logs a warning with its table and id, never its contents beyond the id.

  PASS
- **Git**: one branch, one PR; atomic commits per story. PASS

Re-checked after design: PASS. Nothing to track under Complexity.

## Project Structure

### Documentation (this feature)

```text
specs/076-four-digit-years/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/stored-times.md   # the 075 contract's year rule, amended
├── checklists/requirements.md
└── tasks.md                    # /speckit-tasks
```

Amended outside this folder:

| Spec | What changes |
|---|---|
| `specs/075-typed-times-utc/spec.md` | FR-001 notes the four-digit year and the 20yy reading (Amendments line) |
| `specs/075-typed-times-utc/contracts/stored-times.md` | the year is always four digits, zero-padded |
| `specs/006-feedback-round-2/spec.md` (manual rides) | a ride date can't be in the future |
| `CLAUDE.md` | one paragraph for 076 |

### Source Code (repository root)

```text
app/models/typed_dates.py        # NEW: full_year(text), the 20yy and 1900 rules
app/models/requests.py           # before-validators on ride_date, performed_at, installed_date, removed_date; bike year 0-99
app/models/form_errors.py        # values: date fields normalized with full_year
app/db/frames.py                 # stored(dt): explicit four-digit year; to_utc/end_of_day_utc use it
app/db/typed_times.py            # repair_short_years(conn, zone), repair_database(conn)
app/db/connection.py             # DATA_STEPS gains ("0020_four_digit_years", ..., copy_first=False)
app/services/backup_service.py   # restore: repair after convert, before totals
app/services/ride_service.py     # refuse future rides on create and update
app/templates/bikes/form.html    # Year hint: "For example 2022 or 22."
tests/models/test_typed_dates.py # NEW
tests/models/test_requests.py, tests/models/test_form_errors.py
tests/db/test_frames.py, tests/db/test_typed_times.py, tests/db/test_connection.py
tests/services/test_backup_service.py, tests/services/test_ride_service.py
tests/routers/test_rides.py, tests/routers/test_component_history.py, tests/routers/test_maintenance.py, tests/routers/test_bikes.py
```

**Structure Decision**: the existing layout, plus one new model module and its test.

## Complexity Tracking

None.
