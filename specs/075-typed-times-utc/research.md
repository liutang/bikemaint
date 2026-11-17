# Research: 075 Store Typed Times in UTC

## 1. Where the zone arithmetic lives

- **Decision**: pure functions in `app/db/frames.py`, which already holds the "one clock" rules. The module keeps `part_ride_ok` and loses `ride_wall` and `period_wall`. It gains:
  - `to_utc(day, hhmm, zone)`: a local date and minute to stored UTC text;
  - `from_utc(value, zone)`: stored UTC text to a local `datetime`;
  - `end_of_day_utc(day, zone)`: the last microsecond of a local day, as stored UTC text;
  - `STORED_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"`.

  `clock_service` wraps them with the saved zone for services and templates.
- **Rationale**:
  - The one-time conversion runs from `app/db/connection.run_migrations`, so it can't import a service. `clock_service` imports `app.db.connection`, which would make the import circular.
  - `frames.py` imports nothing from services.
- **Alternatives considered**:
  - A new `app/services/time_service.py`. Rejected: the db layer would import a service.
  - Keeping the math inside `clock_service`. Rejected for the same import cycle.

## 2. Daylight-saving rules

- **Decision**: build the local time with `datetime(..., tzinfo=ZoneInfo(zone))` and the default `fold=0`, then convert with `.astimezone(timezone.utc)`.
- **Rationale**: Python's `zoneinfo` with `fold=0` reads a nonexistent time (2:30 AM on the spring-forward day) with the offset before the change, which gives 3:30 AM daylight time. It reads a repeated time (1:30 AM on the fall-back day) as the first occurrence, daylight time. Both are what the spec's Edge Cases ask for, with no extra code.

## 3. One stored text format

- **Decision**: every instant is written as `YYYY-MM-DDTHH:MM:SS.ffffffZ` (UTC). The conversion rewrites every value it touches in that format. Strava times already use it (`sync_service._normalize_strava_timestamp`), and so do "now" values.
- **Rationale**: once the SQL helper functions are gone, comparisons are plain text comparisons. Text compares in time order only when every value has the same shape. For example, `…:00Z` sorts after `…:00.000000Z` for the same instant, because `Z` > `.`.
- **Alternative considered**: a SQL `utc()` function that parses both sides. Rejected: it keeps a special rule in every query, which FR-010 retires.

## 4. Maintenance entries: date as typed, plus one instant

- **Decision**:
  - Keep `performed_at` (local date) and `performed_time` (local `HH:MM`, or NULL).
  - Add `performed_instant`, UTC text:
    - for an entry with a time, the typed local date and time converted to UTC. This is the truth for that entry;
    - for an entry without a time, `end_of_day_utc(performed_at, zone)`. This is derived from the date.
  - Saving a zone calls `maintenance_service.follow_zone()`:
    - entries with a time get `performed_at`/`performed_time` recomputed from their instant;
    - entries without a time get their instant recomputed from their date.
- **Rationale**:
  - Every date-based use already reads `performed_at`/`performed_time` and keeps working unchanged: history order (`_sort_key`, the SQL `ORDER BY`), `latest_for_owner_and_type`, `baseline_date`, and the edit form prefill. This gives US2 with no change to those paths.
  - Every comparison with rides and periods reads `performed_instant`: `entry_moment`, `_ENTRY_AT`, mileage at service.
  - After a zone change, a timed entry shifts like any other time (US4 scenario 1), and an untimed one keeps its date (US4 scenario 3).
- **Spec note**: an untimed entry's instant is derived, not recorded, so it moves with the zone. US4 scenario 2 is reworded to "no ride, install or timed maintenance instant changes".
- **Alternatives considered**:
  - Converting the entry's date to UTC. Rejected: a 9 PM entry would move to the next day (the review finding).
  - Deriving the instant in SQL on read. Rejected: that needs a zone-aware SQL function, which is the kind of special rule being retired.

## 5. Schedule starting points

- **Decision**: `baseline_at` holds UTC from now on.
  - New values come from `entry_moment()`, which returns `performed_instant`, from `_now_stored()`, or from the 1970 marker.
  - The fallback `f"{baseline_date}T00:00:00.000000Z"`, used by schedules with no `baseline_at`, becomes `to_utc(baseline_date, "00:00", zone)`.
  - The conversion recognises the existing forms as in the spec's US3 table:

    | Form | Example | Conversion |
    |---|---|---|
    | NULL | | left |
    | 1970 marker | `1970-01-01T00:00:00.000000Z` | left |
    | Last moment of a day | `…T23:59:59.999999Z` | `end_of_day_utc(date)` |
    | Whole minute | `…T17:00:00.000000Z` | `to_utc` |
    | Anything else | | left (recorded "now") |

- **Rationale**: these are the only writers (`schedule_service._baseline_for`, `create_schedule`, `complete_schedule`, `maintenance_service._rebase_matching_schedules`).

## 6. Running the conversion once

- **Decision**:
  - Migration `0018_maintenance_performed_instant.sql` adds the column, as a plain SQL migration.
  - `run_migrations` then runs a short, explicit list of Python data steps, `DATA_STEPS = [("0019_typed_times_utc", typed_times.convert_database)]`. Each is recorded in `schema_version` under its name, the same way `.sql` files are.
  - Each step runs in one transaction with its `schema_version` row, so a failure rolls both back and the step runs again at the next start.
- **Rationale**:
  - The conversion needs zone data, so it can't be SQL.
  - An explicit list is plainer than loading `.py` files by path (Principle I).
  - `executescript` commits on its own, so the data step stays out of it.
- **Alternative considered**: a separate marker column on `account`. Rejected, because `schema_version` already means "ran once".

## 7. Copy before converting

- **Decision**: before the data step, if any row would be converted, copy the database with SQLite's online backup API (`sqlite3.Connection.backup`). The copy goes beside the database file, as `<stem>-before-075-<YYYY-MM-DD><suffix>` (for example `bikemaint-before-075-2026-11-17.db`).
  - If the copy fails, log an error naming the path and raise, so startup stops with nothing converted.
  - An empty database (fresh install, most tests) gets no copy; the step is just recorded.
- **Rationale**:
  - A whole-file copy can be put back over the database for an older image.
  - It works whether or not `BACKUP_DIR` is set.
  - The backup API copies safely while the connection is open.
- **Alternative considered**: a JSON backup into `BACKUP_DIR`. Rejected: `BACKUP_DIR` is optional, and a JSON restore needs a running app.

## 8. What the conversion touches

- **Decision**: `typed_times.convert(conn, zone)`:
  - `ride_activity` where `source = 'manual'`: `occurred_at` converted with `to_utc` (all of them, deleted ones included).
  - `component_installation_period.installed_at` and `removed_at`: whole-minute values converted; values with seconds left alone.
  - `maintenance_log_entry.performed_instant`: filled as in §4.
  - `maintenance_schedule.baseline_at`: converted as in §5.
  - Nothing else.
  - With zone `UTC` the conversion is the identity, so it only rewrites formats.
- **Rationale**: these are the only columns the rider types into (spec US3 table). Strava rides, edited or not, stay as they are; the rider confirmed none were edited.

## 9. Backups

- **Decision**:
  - `backup_service.FORMAT = 2`, and restore accepts 1 and 2.
  - For format 1, rows are inserted as today, then `typed_times.convert(conn, <timezone in the backup's account settings, else UTC>)` runs in the same transaction, before totals are recomputed.
  - `performed_instant` is a column of `maintenance_log_entry`, so the schema-driven export carries it.
- **Rationale**: a format-1 file holds unconverted typed times. Converting with the backup's own zone matches what the update did.

## 10. Comparisons after the change

- **Decision**:
  - `mileage._WINDOWS` uses `installed_at` and `COALESCE(removed_at, '9999')` directly.
  - The period ride filter compares `ride_activity.occurred_at` directly.
  - `maintenance._ENTRY_AT` becomes `m.performed_instant`, and the past-parts windows in `maintenance.py` use the raw columns.
  - `bike_mileage_at`, `component_mileage_at` and `usage_since` are unchanged in SQL. They now receive UTC (`entry.performed_instant`, `baseline_at`), which fixes the mixed comparison.
- **Results**:
  - Bike, part and period totals are identical, because local-to-UTC keeps order.
  - The one exception is the repeated hour on a fall-back day, where a ride and a typed boundary in that same hour can now land on the correct side. The rider declined to chase such cases, so it is noted, not handled.

## 11. "Today"

- **Decision**: `clock_service.today()` returns `datetime.now(saved zone).date()`. It replaces:
  - `date.today()` in `schedule_service._today` and `notification_service.check_due_schedules`;
  - the server-local `astimezone()` in `_baseline_for`.

  The trailing pace window starts at local midnight (`to_utc(day, "00:00")`). Earliest install dates use the local date of `installed_at`.
- **Left alone**:
  - `requests.py` (the newest bike model year is server year + 1, harmless).
  - The distinct-ride-day count `substr(occurred_at, 1, 10)`, which only feeds projection confidence. Using the UTC date there moves at most a day's count on evening rides.

## 12. Edit forms and unchanged saves

- **Decision**: `clock_service.keep_or_convert(stored, day, hhmm)`. The submitted minute is the date plus the time, or the default time when blank (noon for rides, 00:00 for installs).
  - If the stored instant's local date and minute equal the submitted minute, it returns the stored text unchanged.
  - Otherwise it returns `to_utc(...)`.
  - Rides, install periods and timed maintenance edits all use it.
  - Prefill uses a `to_local` filter (UTC to `YYYY-MM-DDTHH:MM` local), replacing `to_wall`. The maintenance form already prefills its local columns.
- **Rationale**: this covers Strava seconds and the repeated hour (FR-003, SC-003) without hidden form fields.

## 13. Display

- **Decision**:
  - Every stored instant renders through `local_time` (`format_utc`).
  - `wall_time`, `format_wall`, `_wall_moment` and `now_in_zone_moment` are removed.
  - An untimed maintenance entry still shows `performed_at`.
  - A timed one shows `performed_instant|local_time`.
- **Rationale**: one display rule (FR-002, SC-001, SC-004).
