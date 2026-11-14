# Implementation Plan: 036 12-Hour Clock Setting

- **Migration** `app/db/migrations/0013_account_clock_format.sql`: `ALTER TABLE account ADD COLUMN clock_format TEXT NOT NULL DEFAULT '12' CHECK (clock_format IN ('12','24'))`.
- `app/models/rows.py` Account gains `clock_format`; `app/db/accounts.py` `update_clock_format`.
- `app/services/clock_service.py`: cached `clock_format()` / `remember_clock` like the zone; `format_utc` uses it; new `format_wall(value)` for typed `YYYY-MM-DD[T ]HH:MM` text (Jinja filter `wall_time`); a shared `_clock(dt)` helper (`%-I` is not portable: build hour by hand).
- `app/services/settings_service.py` `set_clock_format`; `app/models/requests.py` `ClockSettingsRequest` (Literal "12"|"24"); route `POST /settings/clock` in `app/routers/settings.py`; `settings/index.html` panel "Clock".
- Templates: replace `x[:10] x[11:16]` in `rides/log.html`, `components/install_history.html`, `bikes/install_history.html` with `|wall_time`.
- Contract: add the route to `specs/001-bike-maintenance-tracker/contracts/routes.md` (see-also) and CLAUDE.md note.
- Tests first: `tests/services/test_clock_service.py`, `tests/db/test_accounts.py`, `tests/models/test_settings_requests.py`, `tests/routers/test_settings.py`, `tests/routers/test_rides.py`.

Constitution v1.3.0: all gates pass (parameterized SQL, Pydantic validation, services free of FastAPI, no JS).
