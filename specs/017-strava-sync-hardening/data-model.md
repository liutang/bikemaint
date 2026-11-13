# Data Model: 017 Strava Sync Hardening (Retrospective)

No schema change and no migration. The feature reads and writes existing columns.

## Bike (`bike`)

| Field | Role in this feature |
|---|---|
| `strava_gear_id` | Set by pairing; **cleared by unpair**; its presence decides whether the re-import and unpair actions are offered |
| `strava_paired_at` | Set by pairing; **cleared by unpair** |
| `updated_at` | Refreshed when unpair clears the pairing |

### State transitions

```text
unpaired --pair--> paired --unpair--> unpaired
                     |  ^
                     +--+  re-import (no change to the bike row; rides updated in place)
```

Invalid transitions: re-import or unpair while unpaired → rejected (409).

## Ride (`ride_activity`, source `strava`)

- Keyed by Strava activity id; re-import upserts, so the count after N re-imports equals the count after one.
- Unpair does not touch rides. Rides the rider edited or deleted stay protected (feature 006).

## Strava gear (external, not stored)

- Source: the athlete's `bikes` list. Absent or null = profile access not granted; empty = no bikes.
- Shown in the pairing screen by name, falling back to id.
