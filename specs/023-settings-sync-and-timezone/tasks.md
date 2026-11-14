# Tasks: 023 Strava Sync Settings and Time Zone

**Input**: `specs/023-settings-sync-and-timezone/` (spec.md, plan.md, research.md, data-model.md, contracts/routes.md, quickstart.md)

**Tests**: Required and written first (constitution III).

Format: `- [ ] ID [P] [Story] Description (file paths)`.

## Phase 1: Foundational — settings storage

- [x] T001 Tests first: `tests/db/test_accounts.py` (new columns default to enabled, NULL interval, `UTC`; `update_sync_settings` and `update_timezone` persist), `tests/models/test_requests.py` or `tests/models/test_settings_requests.py` (`SyncSettingsRequest`: hours 0–168, minutes 0–59, total 5–10080 inclusive, 0h4m and 0h0m refused, 168h0m ok, 169h refused, non-integers refused; `TimezoneSettingsRequest`: valid IANA name ok, unknown and empty refused). Watch them fail.
- [x] T002 `app/db/migrations/0011_account_sync_and_timezone.sql` (columns exactly as in data-model.md), `app/models/rows.py` Account fields, `app/db/accounts.py` update functions, `app/models/requests.py` request models, `pyproject.toml` add `tzdata`; `.venv/bin/pip install tzdata`.

## Phase 2: User Story 1 — Control the automatic sync (P1)

**Independent test**: save 1 h 30 min; the scheduler reports a 90-minute job; turn off; no job; manual sync still works.

- [x] T003 [US1] Tests first: `tests/services/test_scheduler.py` (`apply_sync_settings(True, 90)` leaves exactly one `strava_sync` job at 90 minutes; calling it again replaces it, not duplicates; `apply_sync_settings(False, …)` removes it; `start()` uses the saved account values, else `STRAVA_SYNC_INTERVAL_MINUTES`, else 30; when off at startup there is no sync job), `tests/services/test_settings_service.py` (`set_sync_settings` persists, applies to the scheduler, and logs a line without secrets; `effective_sync_interval`; manual `/sync/strava` path unaffected by the setting), `tests/routers/test_settings.py` (the panel shows the switch, Hours, Minutes and current values; save redirects 303 and shows "Every 1 h 30 min" or "Automatic sync is off"; bad input re-renders 422 with a message beside the field and changes nothing; unauthenticated is redirected to `/login`; `POST /sync/strava` still works when off). Watch them fail.
- [x] T004 [US1] `app/services/scheduler.py` (`apply_sync_settings`, `start()` reads the account), `app/services/settings_service.py` (`set_sync_settings`, `effective_sync_interval`, minutes ↔ hours/minutes helpers), `app/routers/settings.py` (`POST /settings/strava/sync`), `app/templates/settings/index.html` (sync form inside the Strava connection panel with a status line).

## Phase 3: User Story 2 — Time zone for display (P2)

**Independent test**: with `America/Los_Angeles`, a Strava ride at 18:00Z shows `10:00 PST`; a typed ride shows as typed; a future typed install moment in the zone is refused.

- [x] T005 [US2] Tests first: `tests/services/test_clock_service.py` (`format_utc("2026-01-15T18:00:00.000000Z")` in Los Angeles is `2026-01-15 10:00 PST`; July gives `PDT`; UTC gives `UTC`; zones without letters fall back to an offset; bad input returns the original text; `now_in_zone_moment()` equals the zone's wall clock), `tests/services/test_component_history_service.py` (typed install moments are compared with the zone's now: with a zone ahead of UTC a moment an hour before local now is accepted though it is after UTC now, and a moment an hour after local now is refused; blank installs and mileage results are unchanged), `tests/routers/test_settings.py` (Time zone section shows the current zone; `POST /settings/timezone` saves; unknown zone 422 with message beside `timezone`; connected-since is shown in the zone), `tests/routers/test_rides.py` (a Strava ride shows in the zone with abbreviation, a manual ride exactly as typed), `tests/routers/test_maintenance.py` (a completed task shows in the zone), `tests/test_ui_builder_assets.py`/`tests/routers/test_maintenance.py` (no `data-local` or `localtime.js` remain). Watch them fail.
- [x] T006 [US2] `app/services/clock_service.py` (cached zone name, `format_utc`, `now_in_zone_moment`, cache refreshed by `settings_service.set_timezone`); `app/services/component_history_service.py` `check_not_future` uses `now_in_zone_moment`; `app/main.py` registers filter `local_time`; templates `rides/log.html`, `maintenance/history_list.html`, `settings/index.html` use it and drop `data-local`; remove `app/static/localtime.js` and its `<script>` in `layout.html`; `app/routers/settings.py` `POST /settings/timezone`; Time zone section in `settings/index.html` (text input with a datalist of `zoneinfo.available_timezones()`).

## Phase 4: Polish

- [x] T007 `CLAUDE.md` (account settings; display-only zone and its consequence; `tzdata`), `specs/001-bike-maintenance-tracker/contracts/routes.md` see-also, README (`STRAVA_SYNC_INTERVAL_MINUTES` is the first-run default), `specs/006-feedback-round-2/spec.md` assumptions (browser-local conversion superseded).
- [x] T008 Full suite: 1028 passed. Analysis: FR-001..FR-013 each map to tests (db, request models, scheduler, settings service, clock service, settings/rides/maintenance routers, history-service future check); route contracts re-walked with no gaps. No CRITICAL/HIGH. LOW/not verified: the Settings page layout and the rendered zone abbreviations were not checked in a browser by Claude; `tzdata` is installed through `pyproject.toml` (the local venv has no pip, so the local run used the system zone files). Blank install dates still display in UTC (documented trade-off).

## Phase 5: Amendment from user testing (branch 025-timezone-picker)

- [x] T009 [US2] Tests first: `tests/services/test_clock_service.py` (`timezone_choices(current)`: about 30 entries ordered by offset; each label looks like `-05:00 EST` or just `+03:30` when the zone has no letter abbreviation; `-05:00 EST` is `America/New_York`, `-08:00 PST` is `America/Los_Angeles`, `+05:30 IST` is `Asia/Kolkata`, `+00:00 UTC` is `UTC`; Arizona is `-07:00 MST (no daylight saving)`; values are unique valid zones; a saved zone not in the list is added and flagged current), `tests/routers/test_settings.py` (Time zone is a `<select>` with these options and the current one selected; no `datalist` and no city list; an off-list saved zone stays selectable; saving a choice works; unknown still refused). Watch them fail.
- [x] T010 [US2] `app/services/clock_service.py` (`timezone_choices`), `app/routers/settings.py` (pass choices), `app/templates/settings/index.html` (`select_field`, updated copy and hint), run the suite, update `specs/023.../contracts/routes.md` and `CLAUDE.md`, PR, merge, confirm publish.

## Phase 6: Amendment from user testing (branch 027-timezone-label-format)

- [x] T011 [US2] Tests first: `tests/services/test_clock_service.py` (labels such as `(GMT-5) America/New York (EST)`, `(GMT-8) America/Los Angeles (PST)`, `(GMT+0) Europe/London (GMT)`, `(GMT+0) UTC`, `(GMT+5:30) Asia/Kolkata (IST)`, `(GMT-3) America/Sao Paulo` with no brackets, `(GMT-7) America/Phoenix (MST, no daylight saving)`; the offset is the standard one even for southern-hemisphere zones; an off-list zone reads `Current: ...`), `tests/routers/test_settings.py` (option texts, "Currently (GMT-5) America/New York (EST)."). Watch them fail.
- [x] T012 [US2] `app/services/clock_service.py` `_label`/`_offset_text`; update `CLAUDE.md` and the contract text; run the suite; PR; merge; confirm publish.

## Dependencies

- T001 → T002 → US1 (T003 → T004) and US2 (T005 → T006) in either order; US1 is the MVP.
- T007–T008 last.

Note (T010): full suite 1061 passed. The picker reuses the app's existing select component, so it matches the other dropdowns; not checked in a browser by Claude.
- [x] T0xx (049) Show system-recorded install/removal instants in the chosen zone (Install History, form prefill): tests in `tests/services/test_clock_service.py` and `tests/routers/test_component_history.py`; `clock_service.format_wall`/`to_wall` convert instants with seconds or microseconds.

