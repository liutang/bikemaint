# Plan: Sync Rules
- Migration 0017: `ride_activity.sport_type`, `ride_type`, `activity_name`, `filtered_out`; table `sync_rule(bike_id | component_id, sports, ride_types, keywords)`.
- `app/models/sync_rules.py`: option lists and the pure matcher `ride_matches` (unknown details match).
- `app/db/sync_rules.py`: get/save; `mileage_db.apply_bike_rule` sets `filtered_out`; every live-ride query adds `filtered_out = 0`; part queries add the SQL function `part_ride_ok(component_id, ...)` (registered in `app/db/frames.py` style) so part rules are read per call and never stale.
- `app/services/sync_rule_service.py`: validate, save, re-apply, recompute bike/part (and the bike's parts). `sync_service` stores the new ride fields and applies bike rules after each upsert.
- Routers `bikes.py` and `components.py` (or a small `sync_rules.py`) with the two POST routes; templates get a shared `partials/sync_rules.html` section on both Edit screens. No JS.
Constitution: raw parameterized SQL, logic in services, thin routers, tests first.
