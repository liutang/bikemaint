# Implementation Plan: 023 Strava Sync Settings and Time Zone

**Branch**: `023-settings-sync-and-timezone` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

## Summary

Store three settings on the account (automatic sync on/off, sync interval in minutes, time zone name), let the rider change them in Settings, apply the sync settings to the running scheduler at once, and show UTC-recorded times in the chosen zone through one server-side filter. Stored times are not touched.

## Technical Context

**Language/Version**: Python 3 (CPython 3.13)

**Primary Dependencies**: FastAPI, Jinja2, HTMX, APScheduler (unchanged); standard-library `zoneinfo`; **new**: `tzdata` (pure-data package) so zone names resolve inside the slim container image

**Storage**: SQLite; migration `0011_account_sync_and_timezone.sql` adds three columns to `account`

**Testing**: pytest (`tests/db`, `tests/models`, `tests/services`, `tests/routers`, `tests/test_ui_*`)

**Target Platform**: Self-hosted container (python:3.13-slim; `pip install .` picks up `tzdata`)

**Project Type**: web-service

**Performance Goals**: Zone lookups are cached in memory per process; one query only when the setting changes or at first use

**Constraints**: Single rider/account; no stored time changes; mileage results unchanged

**Scale/Scope**: One account

## Constitution Check (v1.3.0)

| Principle | Result | Notes |
|---|---|---|
| I Simplicity | Pass | One small `clock_service`; scheduler reschedules one job; no new framework |
| II Modular design | Pass | Routes thin (`settings.py`), logic in `settings_service`/`clock_service`/`scheduler`, queries in `app/db/accounts.py`, validation in request models |
| III TDD | Pass (planned) | Each task test-first |
| IV Security | Pass | New routes use `require_account`; input validated by Pydantic (hours/minutes bounds, zone name via `zoneinfo`); SQL parameterised; no secrets logged |
| V Observability | Pass | Info line when sync scheduling changes (`sync enabled=… interval_minutes=…`), no secrets |
| Stack / layout | Pass with note | One new dependency (`tzdata`), data only, required for IANA zones on slim images; no new directory |

## Project Structure

### Documentation (this feature)

```text
specs/023-settings-sync-and-timezone/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/routes.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
pyproject.toml                       # + tzdata
app/
├── db/
│   ├── migrations/0011_account_sync_and_timezone.sql
│   └── accounts.py                  # update_sync_settings, update_timezone
├── models/
│   ├── rows.py                      # Account gains strava_sync_enabled, strava_sync_interval_minutes, timezone
│   └── requests.py                  # SyncSettingsRequest, TimezoneSettingsRequest
├── services/
│   ├── clock_service.py             # zone name cache, format_utc (with abbreviation), now_in_zone_moment
│   ├── settings_service.py          # set_sync_settings, effective sync interval, set_timezone
│   ├── scheduler.py                 # apply_sync_settings(enabled, minutes); start() reads the account
│   └── component_history_service.py # check_not_future uses the zone
├── routers/settings.py              # POST /settings/strava/sync, POST /settings/timezone
├── templates/
│   ├── settings/index.html          # sync panel in the Strava section; Time zone section; connected-since in zone
│   ├── rides/log.html, maintenance/history_list.html  # local_time filter, no data-local
│   └── layout.html                  # drop localtime.js
├── static/localtime.js              # removed
└── main.py                          # register the local_time filter
tests/                                # mirrors app/
```

## Design Decisions (detail in research.md)

1. Interval stored as total minutes (`NULL` = never saved → environment default, 30 if unset); on/off stored separately (default on).
2. Scheduler job `strava_sync` is added, rescheduled or removed in place; startup reads the saved settings.
3. One Jinja filter `local_time` converts a stored UTC string to `YYYY-MM-DD HH:MM ABBR` in the saved zone; used only for values that are UTC by construction.
4. The future check compares typed values with the current wall-clock time in the zone; blank "now" keeps UTC.
