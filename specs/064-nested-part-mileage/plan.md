# Plan
- `app/db/mileage.py`: a recursive CTE `win(period_id, component_id, bike_id, s, e)` (wall frame, open end '9999') expands each period: bike periods directly, parent-part periods by intersecting with the parent's windows (depth < 8). All ride/period queries (`recompute_component_total_mileage`, `list_rides_for_component`, `list_rides_for_period`, `component_mileage_at`, `usage_since`, `component_ids_with_history_on`) join it; sums count each ride once (DISTINCT ride id).
- `component_history_service`: describe_history miles use the CTE; log/update store NULL bike when an Inside part is chosen; after any period change recompute all live parts.
- Form hint on bike field. No schema change. Tests mirror.
