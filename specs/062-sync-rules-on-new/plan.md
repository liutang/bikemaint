# Implementation Plan: Sync Rules When Adding

**Spec**: [spec.md](spec.md)

- `partials/sync_rules.html`: split into `sync_rules_fields(sync)` (error, fieldsets, keywords) and the existing panel which wraps it in its own form.
- `forms` for new bike (`bikes/form.html`) and new part (`components/form.html`) include the fields inside the main form when no owner exists.
- `routers/sync_rules.sync_context(kind, owner_id=None, ...)` returns an empty rule for a new item.
- `sync_rule_service.validate_rule(sports, ride_types, keywords)` builds a `SyncRule` (ValueError on bad input); `save_rule` reuses it.
- Create routes: read `sport`, `ride_type`, `keywords`; validate before creating; save a non-empty rule after.
- No new routes, tables or scripts. Constitution: logic in services, router thin, tests mirror.
