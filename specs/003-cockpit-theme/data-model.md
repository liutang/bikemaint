# Data Model: Cockpit Theme

No schema changes and no migrations.

## Derived (read-only) values

| Value | Source | Used by |
|-------|--------|---------|
| `days_until` | `projection.due_at - today` (negative = days late; `None` if no date) | ring label |
| `ring_fraction` | overdue → 1.0; due soon → `max(0.08, 1 - days_left / lead_time_days)` | ring arc |
| urgent set | `DueItem.status in {overdue, due_soon}` | attention cards |
| other set | `on_track`, `no_estimate` | compact list |
| `overflow_count` | urgent count − 5 when urgent > 6 and not `show_all` | "+N more" tile |
| last sync time | `MAX(ride_activity.synced_at)` | top-bar indicator |

`DueItem` gains `days_until: int | None` (computed in `_due_item`).
