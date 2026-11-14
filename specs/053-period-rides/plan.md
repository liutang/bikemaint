# Implementation Plan: Rides for an Install Period

**Branch**: `053-period-rides` | **Spec**: [spec.md](spec.md)

## Summary
A read-only page per install period listing the rides that count toward it, reached from a Rides button on both Install History screens. No schema change.

## Constitution check
Stack unchanged (FastAPI, Jinja2, SQLite). The query is parameterized and lives in `app/db/mileage.py`; the log is built in `app/services/ride_service.py`; the route in `app/routers/rides.py` holds no logic. Tests first, mirrored under `tests/`. Passes.

## Design
- `mileage_db.list_rides_for_period(conn, period)`: live rides on `period.parent_bike_id` with `ride_wall(...) >= period_wall(installed_at)` and `< period_wall(removed_at)` when removed (015 FR-013), oldest first.
- `ride_service.get_log_for_period(period_id)` returns a `RideLog` of kind `period` (with the period attached), running totals from zero, no start row, no adjustments; `_build_rows` gains `with_start`.
- Route `GET /install-periods/{period_id}/rides` in `rides.py`: 404 for an unknown period; breadcrumb back to the part's install history, or the bike's with `?from_bike=ID`.
- `rides/log.html`: for kind `period` show the part, the period times (`wall_time`) and an empty state; no Add button, no Actions column.
- Rides button added to `components/install_history.html` and `bikes/install_history.html` (the bike's passes `from_bike`).
- Contract `contracts/routes.md` gets the new route.
