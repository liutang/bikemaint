# Tasks: 036 12-Hour Clock Setting

- [ ] T001 Tests first: `tests/services/test_clock_service.py` (`format_utc` and `format_wall` in 12h and 24h; noon, midnight, single-digit hour), `tests/db/test_accounts.py` (default `12`, `update_clock_format`), `tests/models/test_settings_requests.py` (`ClockSettingsRequest` accepts 12/24 only), `tests/routers/test_settings.py` (panel, save, invalid 422), `tests/routers/test_rides.py` (typed and Strava times default 12h). Watch fail.
- [ ] T002 Migration 0013, `rows.py`, `accounts.py`.
- [ ] T003 `clock_service` (`clock_format`, `remember_clock`, `format_wall`, 12/24 in `format_utc`); `app/main.py` filter `wall_time`.
- [ ] T004 `settings_service.set_clock_format`, request model, `POST /settings/clock`, Settings panel.
- [ ] T005 Templates use `wall_time`; update older tests that assert 24-hour text (default is now 12h).
- [ ] T006 Docs: routes contract, CLAUDE.md; full suite; PR; merge; confirm publish.
