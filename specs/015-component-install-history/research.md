# Research: 015 Component Install Dates and Manual History (Retrospective)

Decisions recorded as built (PR #16).

## 1. Existing attribution is reused, not rebuilt

- **Decision**: Keep `recompute_component_total_mileage` as the single mileage calculation (baseline + rides on each period's bike within `[installed_at, removed_at)` + adjustments). This feature only adds inputs (install dates, manual periods) and calls recompute after changes.
- **Rationale**: Per-period attribution already worked; the gaps were missing inputs and a missing recompute after back-dating.
- **Alternatives**: A second "manual mileage" path (two sources of truth).

## 2. Moment parsing

- **Decision**: `component_history_service.moment(day, time)`: both blank = now; a date alone = 00:00; a time without a date is an error. Stored as typed with no zone conversion, matching rides.
- **Rationale**: Consistency with the ride log and no per-rider timezone setting.
- **Alternatives**: UTC conversion in the server (needs a timezone setting).

## 3. Validation

- **Decision**: Install and removal moments cannot be in the future; removal must be after install; periods of one part may not overlap (touching ends allowed); a logged period must be closed (the live period comes from installing); the open period cannot be deleted by hand.
- **Rationale**: Overlaps would double-count rides; an open period created by hand would contradict the part's real location.
- **Alternatives**: Allow overlaps and de-duplicate rides at read time (hidden complexity).

## 4. Parts added to storage

- **Decision**: The install date is ignored for stored parts.
- **Rationale**: Nothing is installed; storage has no mileage clock.

## 5. History events

- **Decision**: Adding or deleting a period writes "Installed on X" and "Removed from X" `event` entries (feature 006 kinds) dated at the logged moment.
- **Rationale**: Keeps the part's maintenance history consistent with its install history.

## 6. Layout

- **Decision**: New router `app/routers/component_history.py` and service `component_history_service.py`; periods queries stay in `app/db/components.py`.
- **Rationale**: Constitution II; keeps `component_service` from growing.
