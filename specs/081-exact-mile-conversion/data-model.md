# Data Model: 081 Exact Mile Conversion

No schema change.

| Table | Column | Rows | Change |
|---|---|---|---|
| `ride_activity` | `distance_miles` | `source = 'strava' AND user_modified = 0` | × 1609.34 / 1609.344, once (data step `0022_exact_miles`) |

New Strava rides: `distance_miles = distance_m / 1609.344`.
