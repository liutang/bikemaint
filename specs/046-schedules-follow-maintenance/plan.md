# Implementation Plan: 046 Schedules Follow Logged Maintenance

Projections are already computed on read, so rides and usage need no change (FR-003, covered by an existing-behaviour test). The stored starting point is what goes stale, so it is updated when maintenance is logged:

- `app/services/maintenance_service.py`: `entry_moment(entry)` (shared with `schedule_service._baseline_for`); `_rebase_matching_schedules(conn, entry, new_cycle)` runs after `log_maintenance` (only when `schedule_id` is None, new cycle) and `update_entry` (no new cycle): for active schedules of the owner with `service_type == entry.description` and a starting moment earlier than the entry's, call `schedules_db.complete(...)` (new cycle) or `schedules_db.rebase(...)` (no cycle bump).
- `app/db/schedules.py`: `rebase(conn, id, baseline_mileage, baseline_date, baseline_at)`.
- Tests first: `tests/services/test_schedule_follow_maintenance.py`.
Constitution v1.3.0: logic in services, parameterized SQL in db; pass.
