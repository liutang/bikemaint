# Data Model: 023 Strava Sync Settings and Time Zone

## Migration `0011_account_sync_and_timezone.sql`

```sql
ALTER TABLE account ADD COLUMN strava_sync_enabled BOOLEAN NOT NULL DEFAULT 1;
ALTER TABLE account ADD COLUMN strava_sync_interval_minutes INTEGER;          -- NULL = never saved
ALTER TABLE account ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC';
```

| Column | Rule |
|---|---|
| `strava_sync_enabled` | 1 = automatic sync on (default), 0 = off |
| `strava_sync_interval_minutes` | NULL until saved; otherwise 5 to 10080 (7 days), whole minutes |
| `timezone` | An IANA zone name that `zoneinfo` resolves; default `UTC` |

Effective interval = saved minutes, else `STRAVA_SYNC_INTERVAL_MINUTES`, else 30. The form splits minutes into hours (0–168) and minutes (0–59).

No stored time value changes.
