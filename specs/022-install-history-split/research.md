# Research: 022 Install History Split

## 1. Delete versus hide existing entries

- **Decision**: Delete (`DELETE … WHERE kind = 'event'`) in migration `0010`. Decided with the rider.
- **Rationale**: Install periods already hold the same facts, so nothing is lost; hiding would leave dead rows and a filter forever.
- **Alternatives**: Hide in the UI (permanent extra code); keep and count (contradicts the rider's wish).
- **Risk**: A migration deletes data. It is safe because events are fully derivable from periods and are identified by the `kind` column, not by text, so services the rider logged are untouched even if their text starts with "Added".

## 2. Stop writing at the source

- **Decision**: Remove `_log_event`, `_log_added`, `_log_removed` from `component_service` and `_log_event` from `component_history_service`, with their call sites (create, move, delete, detach-to-storage, hand-logged and deleted periods).
- **Rationale**: Filtering at read time would keep writing junk rows and keep the `has_entries` special-casing alive.
- **Alternatives**: Keep writing but never show (pointless).

## 3. Source of a bike's history

- **Decision**: `component_installation_period` rows with `parent_bike_id = bike`, newest installed first, joined to `component` (including soft-deleted rows) for name and kind.
- **Rationale**: Periods record the top bike, so nested parts are already included and a part moved between bikes shows once on each bike with the right moments.
- **Alternatives**: Walk each bike's current tree (misses removed parts, which is the point of a history).

## 4. Place label

- **Decision**: The direct parent part's name if it still exists, "a deleted part" if the parent is soft-deleted, otherwise the bike's name.
- **Rationale**: Matches the part-level history (`place_name`), adding the deleted case that only bike history can hit often.

## 5. Read-only

- **Decision**: No edit or delete controls; each row links to the part, where its Install History is editable.
- **Rationale**: One editing place avoids two screens that could disagree.

## 6. `kind` column

- **Decision**: Keep the `kind` column and the `has_entries_for_*` filter on `kind = 'service'`.
- **Rationale**: Dropping a column needs a table rebuild in SQLite for no user benefit; after this change every row is a service, so the filter is a harmless no-op.
