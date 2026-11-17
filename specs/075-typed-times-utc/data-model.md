# Data Model: 075 Store Typed Times in UTC

All instants are stored as UTC text `YYYY-MM-DDTHH:MM:SS.ffffffZ` (research §3).

## Changed meaning (no schema change)

| Table.column | Before | After |
|---|---|---|
| `ride_activity.occurred_at` (manual rides) | Local time as typed, whole minutes | UTC instant |
| `ride_activity.occurred_at` (Strava rides) | UTC instant | Unchanged |
| `component_installation_period.installed_at`, `removed_at` | Typed: local as typed (whole minutes); recorded: UTC with seconds | UTC instant either way |
| `maintenance_schedule.baseline_at` | Mixed: UTC "now", typed local, untimed local `T23:59:59.999999Z`, 1970 marker | UTC instant, or the 1970 marker, or NULL |
| `maintenance_schedule.baseline_date` | Local date | Unchanged |

## New column

**Migration `0018_maintenance_performed_instant.sql`**

```sql
ALTER TABLE maintenance_log_entry ADD COLUMN performed_instant TEXT;
```

| Column | Meaning |
|---|---|
| `performed_at` | Local date in the saved zone. For an untimed entry this is the truth. For a timed one it is kept in step with `performed_instant`. |
| `performed_time` | Local `HH:MM`, or NULL for untimed. Kept in step with `performed_instant`. |
| `performed_instant` | UTC. For a timed entry this is the truth. For an untimed one it is `end_of_day_utc(performed_at)`, derived from the date. Filled for every row by the conversion, and written by every log and edit. |

**When the saved zone changes** (`maintenance_service.follow_zone`):

- A timed entry gets its `performed_at` and `performed_time` recomputed from `performed_instant`.
- An untimed entry gets its `performed_instant` recomputed from `performed_at`.

## Run-once record

`schema_version` gains the row `0019_typed_times_utc` when the data step commits. It is written in the same transaction as the conversion.

## Pre-update copy

A file beside the database: `<stem>-before-075-<YYYY-MM-DD><suffix>`. It is written only when there is something to convert, and never deleted by the app.

## Backup format

`format: 2`. A format-1 file is restored and then converted with its own `timezone` setting (research §9).
