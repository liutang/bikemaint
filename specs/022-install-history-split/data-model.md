# Data Model: 022 Install History Split

## Migration `0010_remove_part_event_entries.sql`

```sql
DELETE FROM maintenance_log_entry WHERE kind = 'event';
```

No other schema change. After this, no row with `kind = 'event'` exists and none is written.

## Read model: a bike's install history row

Built from `component_installation_period` joined to `component`:

| Field | Source |
|---|---|
| part name, part kind (display name) | `component.name`, `component.component_type` via `kind_name` |
| part link | `/components/{component_id}`, omitted when the part is soft-deleted |
| placed in | parent part's name if `parent_component_id` is set and that part exists; "a deleted part" if it was soft-deleted; otherwise the bike's name |
| installed | `installed_at` (date and `HH:MM`, as stored) |
| removed | `removed_at`, or "Still installed" when NULL |

Order: `installed_at DESC, id DESC`. Filter: `parent_bike_id = :bike_id` (the top bike, so nested parts are included).
