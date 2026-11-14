# Implementation Plan: 040 Schedule Service Types and Intervals

**Migration `0015_schedule_types_and_intervals.sql`**: rebuild `maintenance_schedule` (the old table-level CHECK needs `interval_miles` or `interval_days`, which Rides/Hours/Months/Years schedules lack) with `PRAGMA foreign_keys=OFF` around the rebuild; new columns `service_type TEXT`, `interval_kind TEXT CHECK in ('usage','period')`, `interval_value REAL`, `interval_unit TEXT CHECK in ('miles','rides','hours','years','months','weeks')`, `is_recurring INTEGER NOT NULL DEFAULT 1`, `notify INTEGER NOT NULL DEFAULT 1`, `baseline_at TEXT`; new CHECK: legacy interval present or `interval_kind` present. Rows and ids are copied; indexes recreated; `foreign_key_check` must be empty.

**Schedule representation**: legacy rows keep `interval_miles`/`interval_days`. New rows store `interval_kind/value/unit`; Usage/Miles also writes `interval_miles` and Period/Weeks writes `interval_days = value*7` so existing projection paths and the 001 contract keep working. Rides, hours, months and years use the new columns.

**Services**
- `app/models/rows.py` MaintenanceSchedule gains the new fields.
- `app/db/schedules.py` create/update/complete take them; `complete` also sets `baseline_at`.
- `app/db/mileage.py`: `usage_since(conn, bike_id|component_id, since)` -> (rides, seconds) using the bike filter or the installation-period join; `recent_usage_for_bike(conn, bike_id, since)` -> (rides, seconds, ride_days).
- `app/services/schedule_service.py`: `SERVICE_TYPES`, `USAGE_UNITS`, `PERIOD_UNITS`; `create_schedule`/`update_schedule` accept the new arguments (old call shape still works); `_project` generalised: period due via `add_period(date, value, unit)`; usage remaining via miles/rides/hours; `Projection` gains `remaining` and `remaining_unit` (`remaining_miles` kept for miles); `next_due_text` handles units; `complete_schedule` ends non-recurring schedules (`deactivate`) after logging.
- `app/services/notification_service.py`: skip schedules with `notify` off; payload gains `projected_remaining` and `projected_remaining_unit`; summary uses the unit.
- `app/models/requests.py` `ScheduleRequest`: `service_type` Literal, `interval_kind`, `interval_value` (gt 0, le 100000), `interval_unit_usage`/`interval_unit_period` -> a validator picks the unit for the kind and rejects mismatches; `is_recurring`, `notify`, `is_active`.
- `app/routers/schedules.py`: parse the new fields (checkboxes: present = on); legacy schedule edit prefill in `_form_context`.
- `app/templates/schedules/form.html`: select, radios, number, two unit selects, two checkboxes; `styles.css`: `.interval:has(#interval-usage:checked) .unit-period` etc. to show the matching unit select only (no script); `other_row.html` and `due_dashboard` show the unit.
- Contracts: `specs/040-schedule-types-and-intervals/contracts/routes.md` (form fields and statuses) and webhook payload additions; update `specs/001-.../contracts/webhook-payload.md` with a see-also.

**Tests first**: `tests/db/test_schedules.py`, `tests/db/test_migration_0015.py`, `tests/models/test_schedule_request.py`, `tests/services/test_schedule_service.py`, `tests/services/test_notification_service.py`, `tests/routers/test_schedules.py`, `tests/test_ui_schedule_form.py`; update existing tests that post `name`/`interval_*` to the form.

Constitution v1.3.0: parameterized SQL in `app/db`, logic in services, Pydantic at the boundary, no JS (CSS `:has`), TDD. Pass. Amendment risk: none (stack unchanged).
