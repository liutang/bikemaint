# Research: 076 Four-Digit Years, Two-Digit Typing

## 1. Where the year rule lives

- **Decision**: a pure function `full_year(text: str) -> str` in `app/models/typed_dates.py`.
  - It takes `YYYY-MM-DD` as a date field sends it.
  - Years 0 to 99 become 2000 + year.
  - Years 100 to 1899 raise `PydanticCustomError("date", "Enter a valid date")`.
  - Anything else is returned unchanged, with the year zero-padded to four digits.

  It runs as a `mode="before"` validator on `RideRequest.ride_date`, `MaintenanceLogRequest.performed_at`, `InstallPeriodRequest.installed_date`/`removed_date` and `BuilderAddRequest.installed_date`.
- **Rationale**:
  - **Before, not after:** the browser sends `0000-07-17` for a typed `0`, which Python's `date` (year 1 and up) refuses, so the year must be fixed before Pydantic parses it.
  - **One function:** it covers every form with no per-router code.
  - **`PydanticCustomError`:** the message reads exactly "Enter a valid date", without Pydantic's "Value error, " prefix.
- **Alternatives considered**:
  - Fixing the year in each service. Rejected: the services receive parsed dates, after year 0 has already failed.
  - A browser script that rewrites the field. Rejected: the constitution allows no script for this.

## 2. Showing the four-digit year on a refused form

- **Decision**: `form_errors.error_context` and `message_context` pass the form's date fields (`ride_date`, `performed_at`, `installed_date`, `removed_date`) through `full_year` when building `values`. A value it refuses is left as typed.
- **Rationale**: every re-rendered form already gets its values from these two helpers, so one change covers them all (spec FR-005).

## 3. The bike's model Year

- **Decision**: `BikeDetailsRequest._plausible_year` adds 2000 to a value from 0 to 99 before its 1900-to-next-year check. The field's hint becomes "For example 2022 or 22."
- **Rationale**: the field is a text input read as an int, so `23` arrives as 23.

## 4. Writing four-digit years

- **Decision**: `frames.stored(dt)` formats a UTC datetime as `f"{dt.year:04d}-" + dt.strftime("%m-%dT%H:%M:%S.%fZ")`. `to_utc` and `end_of_day_utc` use it.
- **Rationale**:
  - glibc's `strftime("%Y")` writes `21` for year 21; macOS writes `0021`.
  - The other "now" writers (`datetime.now(...).strftime`) always have the current year, so they're unaffected and stay as they are.
- **Alternative considered**: `isoformat()`. Rejected: it drops `.000000` when microseconds are zero and writes `+00:00` rather than `Z`, which breaks the one stored shape.

## 5. Repairing stored short years

- **Decision**: `typed_times.repair_short_years(conn, zone)` and the data step `repair_database(conn)`, which uses the saved zone.
  - **What counts as short:** a value whose year is below 100, written as `21-…` or `0021-…`.
  - **Instants:**
    - parse the year, month, day, time and microseconds by hand, since `fromisoformat` refuses `21-…`;
    - read the result as UTC, convert it to the zone (zoneinfo gives that year's local mean time, the offset 075 used);
    - change the year to 20yy, keeping the local month, day, time and microseconds;
    - convert back with `to_utc` rules for that real date.
  - **Local dates (`performed_at`):** change the year only.
  - **Columns:**
    - `ride_activity.occurred_at` where `source = 'manual'`;
    - `component_installation_period.installed_at` and `removed_at`;
    - `maintenance_log_entry.performed_at` and `performed_instant`;
    - `maintenance_schedule.baseline_at`.
  - **A value that can't be repaired** (for example, a 20yy date that doesn't exist): it's left unchanged and logged as a warning with its table and id.
- **Example**: `21-04-18T04:56:02.000000Z` in New York is local 0021-04-18 00:00 (LMT −4:56:02). As 2021-04-18 00:00 EDT, it becomes `2021-04-18T04:00:00.000000Z`.
- **Rationale**:
  - Re-reading in the zone keeps what the rider typed (spec FR-008).
  - The columns are the ones 075 converted, plus `performed_at`, which could hold `0021-…` from before 075.

## 6. Running the repair

- **Decision**:
  - `DATA_STEPS` entries become `(name, step, copy_first)`. 075's step keeps `copy_first=True`, and `0020_four_digit_years` has `copy_first=False`.
  - `_run_data_steps` copies only for steps that ask.
  - Totals are recomputed by the existing startup recompute (`app/main.py`).
- **Rationale**:
  - Without the flag, today's code would make a second `-before-075-` copy for the new step.
  - The spec asks for no copy.
- **Restore**: `restore_backup` calls `repair_short_years(conn, zone)` after the format-1 conversion (or straight away for format 2), in the same transaction, before totals are recomputed.

## 7. Future rides

- **Decision**: `ride_service.check_not_future(day, time)`, called by `create_ride` and `update_ride`. It raises `ValueError("The ride date cannot be in the future.")` when:
  - `day > clock_service.today()`, or
  - the day is today, a time was typed, and `clock_service.to_utc(day, time) > now`.

  The routers show it beside the date field (`field="ride_date"`).
- **Rationale**:
  - Using the saved zone's today keeps it right for evening rides.
  - A blank time on today is always allowed (spec US1 scenario 6).
- **Left alone**: Strava sync, and `occurred_at` values already in the future, until edited.
