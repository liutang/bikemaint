# Implementation Plan: 038 Maintenance Mileage From Ride History

- `app/db/mileage.py`: `bike_mileage_at(conn, bike_id, at)` and `component_mileage_at(conn, component_id, at)` — same queries as the two `recompute_*` functions with an added `occurred_at <= ?` bound (ISO strings compare correctly), adjustments in full.
- `app/services/maintenance_service.py` `log_maintenance`: when `mileage_at_service is None`, compute via those functions with `at = performed_at + "T" + (performed_time or "23:59:59.999999")` using the stored format; typed values untouched.
- `app/templates/maintenance/form.html`: hint text for the new (not edit) form; edit keeps its hint.
- Tests first: `tests/db/test_mileage_at.py`, `tests/services/test_maintenance_service.py` (past date excludes later rides; part installed partially; blank time = end of day; typed value kept; today equals current total), `tests/routers/test_maintenance.py` (hint).
- Contract: note in `specs/001-bike-maintenance-tracker/contracts/routes.md` that a blank mileage is computed at the date performed.

Constitution v1.3.0: parameterized SQL in `app/db`, logic in services, no router logic, TDD. All gates pass.
