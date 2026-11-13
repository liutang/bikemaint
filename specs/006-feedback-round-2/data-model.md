# Data Model: 006 Feedback Round 2 (Retrospective)

Two migrations: `0008_maintenance_entry_kind_and_time.sql` (M2) and `0009_rides_become_a_log.sql` (M3). M1 changes no schema.

## `maintenance_log_entry` (0008)

| Column | Type | Rule |
|---|---|---|
| `kind` | TEXT NOT NULL DEFAULT `'service'` | `service` = work the rider logs or completes; `event` = part added/moved/removed, recorded automatically |
| `performed_time` | TEXT, nullable | Optional `HH:MM` the rider typed; system entries use `created_at` |

Rules: only `service` entries count toward "has maintenance history" (delete confirmations). Events are created by component create/move/delete on both the parent and the part.

## `ride_activity` (0009, rebuilt)

| Column | Type | Rule |
|---|---|---|
| `source` | TEXT NOT NULL DEFAULT `'strava'` | `strava` or `manual` |
| `strava_activity_id` | INTEGER UNIQUE, nullable | NULL for manual rides |
| `strava_gear_id` | TEXT | Strava rides only |
| `bike_id` | INTEGER → bike | Re-assignable by the rider |
| `distance_miles` | REAL NOT NULL | Request validation: more than 0 and at most 5000 |
| `occurred_at` | TEXT NOT NULL | `YYYY-MM-DDTHH:MM:00.000000Z`, stored as typed; no time = 12:00 |
| `note` | TEXT | At most 200 characters |
| `is_deleted_upstream` | BOOLEAN NOT NULL DEFAULT 0 | Strava removed it |
| `deleted_by_user` | BOOLEAN NOT NULL DEFAULT 0 | Rider deleted it; sync must not restore it |
| `user_modified` | BOOLEAN NOT NULL DEFAULT 0 | Rider edited it; sync must not overwrite it |
| `synced_at` | TEXT | |

Indexes: `idx_ride_activity_bike_id`, `idx_ride_activity_occurred_at`. Existing rows are copied as `source='strava'`.

### Derived values

- Bike total = starting (baseline) mileage + non-deleted rides + adjustments.
- Part total = baseline + rides on each installation period's bike within the period + adjustments.
- Recompute runs after every ride create, edit, re-assign and delete for the old bike, the new bike, and every part with history on them.

### Ride lifecycle

```text
created (manual) ─edit/re-assign─> user_modified ─delete─> deleted_by_user (hidden, kept)
synced (strava)  ─edit/re-assign─> user_modified ─delete─> deleted_by_user (hidden, kept)
```
