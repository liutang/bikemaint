# Research: 079 Archive Bikes and Parts

## 1. One lock rule

- **Decision**: `archive_service.is_locked(conn, kind, id)`.
  - **A bike is locked** when it is archived.
  - **A part is locked** when it is archived, or when any part above it, or the bike at the top of its chain, is archived.

  `require_unlocked(...)` raises `ArchivedError(owner_name, kind)` for a locked item. Every mutating service calls it.
- **Rationale**:
  - **Inside parts:** the rider said the only thing possible on an archived bike or part is taking parts off to storage. Parts kept inside it are part of what is archived, so they're locked too until taken off.
  - **One function:** a new route can't forget a rule it never had to write.
- **Consequence to confirm with the rider:** while a kept part sits on an archived bike, its details, maintenance and schedules can't be changed either. Taking it off unlocks it.

## 2. What a locked item still allows

- **Decision**: three changes only.
  1. **Moving a locked part to storage:** builder move with target `storage`, `/components/{id}/move` to storage, or ending its still-installed period. Sub-parts stay inside it, as everywhere (spec, 2026-11-18).
  2. **Deleting the archived bike or part itself**, with the existing confirmations. Deleting a part merely inside a locked tree is refused.
  3. **Unarchiving it.**
- **Rationale**: spec FR-006, FR-007 and FR-011.

## 3. Refusal

- **Decision**: `ArchivedError` maps to HTTP 409.
  - **Page forms:** re-render with the message "This bike is archived. Unarchive it to change it." ("part" for a part, naming the archived item when it is an ancestor: "This part is on an archived bike, 2014 Trek Madone 2.1. Take it off to storage, or unarchive the bike.").
  - **Builder (HTMX):** `render_screen` with the message, as other builder errors are shown, status 409.
- **Rationale**: 409 Conflict says the request is valid but the item's state forbids it. It's kept apart from validation's 422.
- **Routes guarded**: every POST under `bikes`, `components`, `builder`, `rides`, `maintenance`, `schedules`, `mileage` (adjust), `sync_rules` and `component_history` that changes a locked item, plus Strava pairing and re-import of an archived bike. A test walks each router's `.router.routes` and fails for any POST not on the "checked" or "not about a bike or part" list.

## 4. Archiving

- **Decision**: `archive_service.archive_bike(bike_id, attached)` and `archive_part(component_id, attached)`, each in one transaction:
  1. **Check:** the item is active. A part must also be in storage (no parent), otherwise `ValueError("Take this part off to storage before archiving it.")`. `attached` is required when parts are attached.
  2. **Move option:** each direct child goes to storage with `component_service.detach_to_storage(conn, child, removed_at=now)`, keeping its sub-parts and schedules.
  3. **Keep option:** every active schedule of the item and of every part in its tree is turned off, as Delete does today (`schedules_db.deactivate`). With the move option, only the item's own schedules are turned off.
  4. **Strava:** a paired bike is unpaired with `bikes_db.clear_strava_pairing`, and its rides are kept.
  5. **Archive:** `archived_at` is set to now (UTC).
  6. **Totals:** part totals are recomputed.
- **Rationale**: this is the same soft "delete" the Schedules page uses, so completed-cycle history in the maintenance log stays.

## 5. Unarchiving

- **Decision**: `unarchive_bike` and `unarchive_part` set `archived_at = NULL`. Nothing else changes: schedules stay off, and the bike stays unpaired.

## 6. Lists and pickers

- **Decision**:
  - `bikes_db.list_active` and `components_db.list_active` keep meaning "not deleted".
  - New service lists: `bike_service.list_bikes()` returns active and not archived (used by the Garage grid, the ride Bike list, the period Bike list and pairing), and `list_archived_bikes()`.
  - `component_service.list_in_storage()` leaves archived parts out (Storage grid, Garage count, builder palette), and `list_archived_parts()` lists them.
  - `component_history_service.parent_options` leaves out every locked part.
- **Rationale**: spec FR-008.
- **Kept as today**: bike name uniqueness still counts archived bikes, so an unarchived bike can't clash.

## 7. Strava

- **Decision**: `mileage.upsert_ride_activity`'s update clause adds `AND NOT EXISTS (SELECT 1 FROM bike b WHERE b.id = ride_activity.bike_id AND b.archived_at IS NOT NULL)`.
- **Rationale**: spec FR-010. Re-importing the same gear onto another bike would otherwise move an archived bike's rides.
- **Not needed**: archived bikes are unpaired, so sync doesn't map new rides to them, and the pairing route refuses an archived bike.

## 8. Screens

- **Builder on an archived root**: nodes render without the `drop-target` class, and the palette shows only the storage section. `builder.js` drops only on `.drop-target`, so no script change is needed. Verify this in the tasks; if a change is needed, it stays inside the 16 KB budget.
- **Rides, Install History and Maintenance history of a locked item**: no Add, Log, Edit or Delete controls, apart from Edit on still-installed periods, which offers only the removal fields.
- **Edit screens**: a template branch on `archived_at`:
  - **Active**: the Archive card, `grid-column: 1 / -1` below Strava and Delete. Without Strava, it sits beside Delete.
  - **Archived**: read-only details and sync rules, an Unarchive card and Delete.
- **Garage and Storage**: `<details class="archived-section">`, closed, with summary "Archived (N)" and the same card grid. Each card reads "Archived YYYY-MM-DD", the local date of `archived_at`.
