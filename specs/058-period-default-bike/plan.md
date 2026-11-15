# Plan
`component_history_service.default_bike_id(component_id)` (current top bike via `components_db.resolve_top_bike_id`, else latest period's bike if it exists). The new-period form passes it as the select default; routers stay thin.
