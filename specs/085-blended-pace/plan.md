# Implementation Plan: Blended Riding Pace

**Branch**: `085-blended-pace` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

## Summary

- **The pace:** `schedule_service._trailing_pace` and `_trailing_usage_pace` become one `_pace(conn, bike_id, today, unit)`. It returns `(pace, trusted)`, where the pace is the mean of:
  - **the 90-day pace:** the existing window queries, unchanged;
  - **the whole-history pace:** the bike's totals since its first counted ride, divided by the days from that ride's local date to today, inclusive. For hours, it runs from the first ride with a moving time.
- **Trust:** `trusted` means the bike has at least 5 counted rides and at least 30 days since its first one. This replaces `ride_days >= MIN_RIDE_DAYS_FOR_CONFIDENCE`.
- **New queries:** `mileage_db.lifetime_ride_stats_for_bike(conn, bike_id)` gives the first ride instant, ride count and miles. A separate first-timed-ride instant and total seconds serve hours. Both use the same live-ride filters as today: not deleted, not filtered out.
- **Unchanged:** the rest of `_project` (earliest of usage and time, the fallback to the time side, overdue).

## Technical Context

**Language/Version**: Python 3.12 (container 3.13-slim)
**Primary Dependencies**: none new
**Storage**: no schema change; two read-only aggregate queries.
**Testing**: pytest.
- The spec's US1 example as a unit test, with a pinned today.
- The blend for each unit, the hours start rule, and no rides in 90 days.
- Trust thresholds (4 rides, 5 rides, 29 days, 30 days).
- Existing projection tests updated where they pinned the old pace or confidence.

**Constraints**:
- computed on read (001 research §4);
- "today" is the saved zone's date (075);
- one query per pace (single rider, negligible).

**Scale/Scope**: `schedule_service`, `app/db/mileage.py`, their tests, and amendments to 001 research §4, 040 and 054.

## Constitution Check

- **Fixed stack, layout, simplicity:** the pace stays in `schedule_service` and the aggregates in `app/db/mileage.py`, parameterized. PASS
- **III. TDD**: failing tests first. PASS
- **IV/V**: no new input or logs. PASS
- **Git**: one branch, one PR. PASS

## Design notes

- **Whole-history days** = (today − local date of the first ride) + 1, so a bike first ridden today has 1 day and no division by zero.
- **Constants:** `PACE_WINDOW_DAYS` stays at 90. New `MIN_RIDES_FOR_CONFIDENCE = 5` and `MIN_HISTORY_DAYS_FOR_CONFIDENCE = 30` replace `MIN_RIDE_DAYS_FOR_CONFIDENCE`.
- **A bike with no counted rides:** pace 0, not trusted. That's no usage date, and "Low confidence" when there's no time side, as today.
- **Where the old 90-day pace shows up:** the attention board and the notification job both call `_project`, so both follow the change with no extra work.

## Project Structure

```text
app/services/schedule_service.py   _pace(), constants, _project uses it
app/db/mileage.py                  lifetime_ride_stats_for_bike(), lifetime_usage_for_bike()
tests/services/test_schedule_service.py, tests/db/test_mileage_usage.py
```

## Complexity Tracking

None.
