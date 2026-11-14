# Implementation Plan: 039 Ride Moving Time

- Migration `0014_ride_moving_time.sql`: `ALTER TABLE ride_activity ADD COLUMN moving_time_seconds INTEGER CHECK (moving_time_seconds IS NULL OR moving_time_seconds > 0)`.
- `app/models/rows.py` RideActivity gains `moving_time_seconds`.
- `app/db/mileage.py`: `upsert_ride_activity(..., moving_time_seconds=None)` (set on insert and conflict update, same `user_modified = 0` guard); `create_manual_ride` and `update_ride` take it.
- `app/services/sync_service._upsert_activities` passes `activity.get("moving_time")`.
- `app/services/ride_service.py`: `create_ride`/`update_ride` take `moving_seconds`; `RideRow.moving_seconds`; helpers `parse_duration("1:30") -> 5400` and `format_duration(5400) -> "1:30"` (Jinja filter `duration`).
- `app/models/requests.py` `RideRequest.moving_time` (`^\d{1,2}:[0-5]\d$`, not `0:00`).
- `app/routers/rides.py` passes it; templates `rides/form.html` (field) and `rides/log.html` (column).
- Tests first: `tests/services/test_ride_service.py`, `tests/services/test_sync_service.py`, `tests/db/test_mileage.py`, `tests/models/test_ride_request.py`, `tests/routers/test_rides.py`.

Constitution v1.3.0: parameterized SQL, validation at the boundary, services free of FastAPI, no JS. Pass.
