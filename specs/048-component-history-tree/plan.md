# Implementation Plan: 048 Component Maintenance History Includes Attached Parts

- `app/services/maintenance_service.py`: dataclass `HistoryRow(entry, part_id, part_name, is_own)`; `list_for_component_tree(component_id)` gathers the part's entries plus those of `components_db.get_descendants`, sorted with the same keys as `list_for_component` (date, time or recorded time, id; descending).
- `app/routers/maintenance.py` `_list_view`: component histories pass `rows` from the tree; bike histories pass rows with `is_own=True`.
- `app/templates/maintenance/history_list.html`: Part column (components only); Edit/Delete only when `row.is_own`.
- Tests first: `tests/services/test_maintenance_service.py`, `tests/routers/test_maintenance.py`.
Constitution v1.3.0: no new routes; logic in the service; pass.
