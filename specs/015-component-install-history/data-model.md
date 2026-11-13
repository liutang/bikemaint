# Data Model: 015 Component Install Dates and Manual History (Retrospective)

No schema change and no migration. Uses `component_installation_period` from migration 0001.

## `component_installation_period`

| Column | Type | Role |
|---|---|---|
| `id` | INTEGER PK | |
| `component_id` | INTEGER NOT NULL → component | The part |
| `parent_bike_id` | INTEGER → bike | The bike (chosen on a logged period) |
| `parent_component_id` | INTEGER → component | Optional parent part on that bike; must not equal `component_id` |
| `installed_at` | TEXT NOT NULL | `YYYY-MM-DDTHH:MM:00.000000Z`, as typed; not in the future |
| `removed_at` | TEXT, nullable | NULL = currently installed (the open period); otherwise after `installed_at` and not in the future |

### Rules (see spec FR-005..FR-009)

- Periods of one part do not overlap; touching ends are fine.
- A manually logged period must have a removal moment (closed).
- The open period may change only its install moment and place; it cannot be deleted.
- After any add, edit or delete, the part's mileage is recomputed.

### Mileage example

Saddle on bike A 1 Jan–1 Jul 2025, bike B from 1 Sep 2025: total = baseline + A's rides in the first window + B's rides since 1 Sep + adjustments.

### Events

Add and delete of a period write `event` entries ("Installed on <place>", "Removed from <place>") on the part's maintenance history, dated at the logged moment.
