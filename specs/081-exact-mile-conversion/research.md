# Research: 081 Exact Mile Conversion

## 1. Rescaling instead of re-fetching

- **Decision**: multiply stored miles by 1609.34 / 1609.344, which gives meters ÷ 1609.344 exactly, up to float rounding.
- **Rationale**:
  - It needs no network.
  - It covers bikes that are unpaired or archived, which Re-import can't reach.
  - The original meters are recoverable from the stored miles.
- **Alternative considered**: an automatic Re-import of every paired bike. Rejected: it misses unpaired and archived bikes and depends on Strava answering.

## 2. Which rows

- **Decision**: `source = 'strava' AND user_modified = 0`, including rows with `deleted_by_user = 1`, `is_deleted_upstream = 1` or `filtered_out = 1`.
- **Rationale**:
  - Those rows' miles still come straight from Strava.
  - Rescaling a deleted or left-out ride is harmless, and keeps it right if it's restored or the rule changes.
  - An edited ride may hold typed miles, and the app can't tell which (rider-confirmed).

## 3. Running it

- **Decision**: a data step, `("0022_exact_miles", typed_times.exact_miles, False)`: one transaction, recorded in `schema_version`, no copy. Totals are recomputed at startup (`app/main.py`).
- **Rationale**: this is the mechanism 075 and 076 already use.
