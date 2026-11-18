# Data Model: 079 Archive Bikes and Parts

## Migration `0021_archived_items.sql`

```sql
ALTER TABLE bike ADD COLUMN archived_at TEXT;
ALTER TABLE component ADD COLUMN archived_at TEXT;
```

- `archived_at`: UTC instant text (075 format) when the item was archived, or NULL when active.
- Set by `archive_service.archive_*` and cleared by `unarchive_*`.
- Rows: `Bike.archived_at` and `Component.archived_at` (`str | None`).

## Lock

A bike is locked when its `archived_at` is set. A part is locked when its own `archived_at` is set, or any part up its `parent_component_id` chain or the top bike has one (one recursive CTE, `components_db.is_in_archived_tree`).

## Effects of archiving (one transaction)

| Step | Tables |
|---|---|
| Move option: direct children to storage, sub-parts inside | `component` (parents), `component_installation_period` (close, re-open nested) |
| Turn off schedules: the item's own, plus its tree's with Keep | `maintenance_schedule.is_active = 0` |
| Unpair a paired bike | `bike.strava_gear_id`, `strava_paired_at` cleared |
| Mark archived | `bike.archived_at` or `component.archived_at` |

Unarchiving clears `archived_at` only.

## Backups

`backup_service` is schema-driven, so `archived_at` is exported and restored with no format change. Format-1 and older format-2 files have no such column and restore as active.
