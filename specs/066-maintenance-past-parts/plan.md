# Plan
- `app/db/maintenance.py`: `list_past_for_bike(conn, bike_id)` uses `mileage._WINDOWS`; `list_past_for_component(conn, id)` uses a similar recursive `anc` CTE (component, ancestor, start, end). Entry moment in SQL: `performed_at || 'T' || COALESCE(performed_time,'23:59') || ':00'` against the windows' wall text.
- `maintenance_service` merges them (skipping ids already listed, names via `get_including_deleted`).
- Template: Part cell shows plain name when the part is deleted. No schema or route change.
