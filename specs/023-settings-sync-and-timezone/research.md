# Research: 023 Strava Sync Settings and Time Zone

## 1. Where sync settings live

- **Decision**: Columns on `account` (`strava_sync_enabled` default 1, `strava_sync_interval_minutes` NULL until saved). Unsaved → `STRAVA_SYNC_INTERVAL_MINUTES` (30 if unset).
- **Rationale**: Single account; survives restarts; the environment variable stays meaningful as a first-run default as the rider asked.
- **Alternatives**: A separate settings table (over-built for one row); only the environment variable (needs a restart, the current pain).

## 2. Applying a new interval without a restart

- **Decision**: `scheduler.apply_sync_settings(enabled, minutes)` removes the job when off, otherwise `add_job(..., replace_existing=True)` with the same id, so exactly one job exists. If the scheduler is not running (tests, startup order) it records nothing and `start()` reads the saved values.
- **Rationale**: APScheduler supports replace-in-place; avoids double syncs.
- **Alternatives**: Reschedule only (fails when the job was removed while off); restart the scheduler (interrupts running jobs).

## 3. Interval input

- **Decision**: Hours and Minutes number fields; hours 0–168, minutes 0–59, total 5–10080 minutes, validated in the request model.
- **Rationale**: Matches the rider's wording; bounds stop accidental one-minute polling against Strava rate limits and absurd values.

## 4. Zone data

- **Decision**: Standard-library `zoneinfo` with the `tzdata` package as a dependency.
- **Rationale**: `python:3.13-slim` is not guaranteed to ship system zone files; `tzdata` makes `zoneinfo` work everywhere, including CI.
- **Alternatives**: `apt install tzdata` in the Dockerfile (a second place to maintain); `pytz` (older API, extra dependency).

## 5. Which times convert

- **Decision**: Only values that are UTC by construction: Strava rides (`source = 'strava'`), `maintenance_log_entry.created_at` shown for completed tasks, `account.strava_connected_at`. Typed values and "now" install moments render as stored.
- **Rationale**: Display-only decision (rider, 2026-11-12): stored times stay as they are so mileage comparisons stay exact.
- **Consequence**: An install recorded with a blank date shows in UTC in Install History; documented in the spec.

## 6. Future check

- **Decision**: `check_not_future` compares the typed value with the current wall-clock time in the saved zone. Blank installs never reach it (the builder passes `None`).
- **Rationale**: Typed times are local wall times; comparing them with UTC wrongly refused valid times east of UTC.

## 7. Browser-local conversion

- **Decision**: Remove `localtime.js` and the `data-local` markup.
- **Rationale**: Two conversions would disagree; the rider asked for one saved zone on every device.
