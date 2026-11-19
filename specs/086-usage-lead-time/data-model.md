# Data Model: 086 Usage Lead Time

## Migration `0024_usage_leads.sql`

```sql
ALTER TABLE account ADD COLUMN lead_miles REAL NOT NULL DEFAULT 20;
ALTER TABLE account ADD COLUMN lead_rides INTEGER NOT NULL DEFAULT 2;
ALTER TABLE account ADD COLUMN lead_hours REAL NOT NULL DEFAULT 2;
```

- Each is 0 or more; 0 turns that unit's rule off.
- They're exported and restored with the other non-secret settings. An older backup without them keeps the defaults.

## Projection (computed, not stored)

- `on_bike: bool`: the schedule's bike, or the part's top bike, exists.
- `trigger` (when due soon): `date`, `miles`, `rides` or `hours`.
