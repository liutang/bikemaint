# Data Model: 076 Four-Digit Years, Two-Digit Typing

No table or column changes.

## Stored instant (amended)

- Format: `YYYY-MM-DDTHH:MM:SS.ffffffZ` (075), with `YYYY` always four digits, zero-padded.
- Written by `frames.stored` (through `to_utc` and `end_of_day_utc`) and by the "now" helpers.

## Typed date

- A date field sends `YYYY-MM-DD`, where a short typed year arrives zero-padded (`0026`).
- `typed_dates.full_year` maps the year as follows:

| Year sent | Read as |
|---|---|
| 0–99 | 2000 + year |
| 100–1899 | refused, "Enter a valid date" |
| 1900 and up | as sent |

## Data step `0020_four_digit_years`

- Recorded in `schema_version` like `0019_typed_times_utc`, one transaction, runs once, no copy.
- Repairs short years in these columns:

| Table | Columns | Rows |
|---|---|---|
| `ride_activity` | `occurred_at` | `source = 'manual'` only |
| `component_installation_period` | `installed_at`, `removed_at` | all |
| `maintenance_log_entry` | `performed_at` (local date), `performed_instant` | all |
| `maintenance_schedule` | `baseline_at`, `baseline_date` (local date) | all |

- It returns counts per table, which are logged.
- An unrepairable value stays unchanged and is logged as a warning with its table and id.

## Backups

- No format change (still 2).
- Restore runs the same repair on the restored rows before recomputing totals.
