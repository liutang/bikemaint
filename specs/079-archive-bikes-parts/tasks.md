---
description: "Task list for 079 archive bikes and parts"
---

# Tasks: Archive Bikes and Parts

**Input**: `specs/079-archive-bikes-parts/` (spec.md, plan.md, research.md, data-model.md, contracts/routes.md, contracts/ui-contract.md, quickstart.md)

**Tests**: required by the constitution (TDD). Write each test first and watch it fail before changing code.

**Mock-ups first**: T003 must be approved by the rider before any template task (T012, T013, T016, T026, T030, T034).

## Phase 1: Setup

- [x] T001 Confirm the branch `079-archive-bikes-parts` (master merged in) and that `.specify/feature.json` points at `specs/079-archive-bikes-parts`. Run the full suite as the baseline.
- [x] T002 Check `app/static/builder.js`: drops land only on `.drop-target` elements, and a dragged node with no drop target other than storage can still be dropped on storage. Record the result here. If a change is needed, it must keep the file under 16 KB. *Result: drops are decided by `.node-row`, `.builder-root` and `.storage-drop`, not `.drop-target`, and a drag opens a gap at the part's own place. So a locked screen needs a small change: when `#builder` has `data-locked`, only `.storage-drop` accepts a drop, and no start gap opens. Done in T017.*
- [x] T003 Mock up for the rider and record their approval here:
  - the Garage with a closed and an open "Archived (N)" section;
  - Storage with an "Archived (N)" section;
  - an archived bike's main screen (the archived notice, its part tree, and the "Add a part" panel showing only "In storage"). *Approved by the rider on 2026-11-18 ("Approve and build").*

## Phase 2: Foundational (blocks every story)

**Purpose**: the archived state, the lock rule and the refusal (research §1–§3).

- [x] T004 [P] Tests first in new `tests/db/test_archive_queries.py`:
  - **Migration:** after `0021_archived_items.sql`, `bike.archived_at` and `component.archived_at` exist and are NULL by default.
  - **Writing:** `bikes_db.set_archived(conn, id, at)` and `components_db.set_archived` set and clear it.
  - **Listing:** `bikes_db.list_archived` lists only archived bikes, newest archived first.
  - **Tree check:** `components_db.is_in_archived_tree(conn, id)` is true for an archived part, for a part inside one (depth 3), and for a part whose top bike is archived. It is false otherwise, and false for a part in storage under nothing archived.
- [x] T005 Implement T004:
  - new `app/db/migrations/0021_archived_items.sql`;
  - the queries in `app/db/bikes.py` and `app/db/components.py`, parameterized, with a recursive CTE capped at depth 8;
  - `archived_at` on `Bike` and `Component` in `app/models/rows.py`.
- [x] T006 [P] Tests first in new `tests/services/test_archive_service.py`:
  - **`is_locked("bike", id)`** and **`is_locked("component", id)`** follow T004.
  - **`require_unlocked`** raises `ArchivedError` with the wording of research §3:
    - "This bike is archived. Unarchive it to change it."
    - "This part is archived. …"
    - "This part is on an archived bike, NAME. Take it off to storage, or unarchive the bike."
- [x] T007 Implement T006 in new `app/services/archive_service.py`.
- [x] T008 [P] Tests first in new `tests/routers/test_screen.py` (mirrors `app/routers/screen.py`): `archived_response(request, exc, ...)` returns 409 with the message, for both a page form and an HTMX builder request. *Done as `render_screen(..., status_code=409)` for the builder (tested through the builder routes in T020) and per-router re-renders for page forms (tested in T012, T014, T022); no separate helper was needed.*
- [x] T009 Implement T008 in `app/routers/screen.py`.

**Checkpoint**: nothing is archived yet, and behavior is unchanged.

## Phase 3: User Story 1 - Archive a bike (P1) MVP

**Goal**: archive a bike from its Edit screen, with keep or move; the Garage shows it in a collapsed section; its rides are read-only; Strava leaves it alone.

**Independent Test**: quickstart steps 1 to 4.

- [x] T010 [P] [US1] Tests first in `tests/services/test_archive_service.py`:
  - **`archive_bike(id, attached="move")`**:
    - each part directly on the bike goes to storage now, with its sub-parts still inside;
    - every one of them keeps its active schedules;
    - the bike's own schedules are turned off;
    - a paired bike is unpaired and keeps its rides;
    - `archived_at` is set, and part totals are recomputed.
  - **`attached="keep"`**: parts stay, and the schedules of the bike and of every part in its tree are turned off.
  - **`attached=None`** with parts attached raises `ValueError`.
  - **Archiving an archived bike** raises `ArchivedError`.
  - **Logging:** one info line with the counts.
- [x] T011 [US1] Implement T010 in `app/services/archive_service.py`, reusing `component_service.detach_to_storage`, `schedules_db.deactivate` and `bikes_db.clear_strava_pairing`, in one transaction.
- [x] T012 [P] [US1] Route and template tests first in new `tests/routers/test_archive.py`:
  - **`POST /bikes/{id}/archive`**:
    - with `attached=move`, answers 303 to `/`;
    - without `attached` when parts are attached, answers 422, re-renders the Edit screen, and changes nothing;
    - on an archived bike, answers 409.
  - **The active Edit screen** has `section.archive-card` after the Strava and Delete cards. It shows the real schedule and part counts, two unchecked required radios `attached`, and "Archive bike". It has no radios when no parts are attached.
  - **`GET /`**:
    - the active grid leaves the bike out;
    - `details.archived-section` (not `open`) has summary "Archived (1)", and the card reads "Archived YYYY-MM-DD";
    - with no archived bikes, there's no section.
- [x] T013 [US1] Implement T012:
  - new `app/routers/archive.py` (registered in `app/main.py`) and `ArchiveRequest` in `app/models/requests.py`;
  - new `app/templates/partials/archive_card.html`;
  - `app/templates/bikes/form.html` and `bikes/list.html`, `partials/bike_row.html`;
  - `bike_service.list_bikes()` (active only) and `list_archived_bikes()`;
  - `.archive-card` (`grid-column: 1 / -1`) and `.archived-section` in `app/static/styles.css`, per T003.
- [x] T014 [P] [US1] Tests first, guards for an archived bike (409, nothing changed):
  - `tests/services/test_ride_service.py` and `tests/routers/test_rides.py`: add, edit and delete a ride; moving a ride onto an archived bike; the Rides list shows no Add, Edit or Delete.
  - `tests/services/test_bike_service.py`: update details, pair, re-import.
  - `tests/services/test_sync_rule_service.py`: save rule.
  - `tests/services/test_maintenance_service.py`: log, edit, delete.
  - `tests/services/test_schedule_service.py`: create.
  - Mileage adjust (`tests/routers/test_mileage.py`).
- [x] T015 [US1] Implement T014: call `archive_service.require_unlocked` in each service; one app-wide exception handler (`app/main.py`, `archived_refusal.html`) answers `ArchivedError` with 409, instead of a mapping in each of `rides.py`, `bikes.py`, `sync_rules.py`, `maintenance.py`, `schedules.py` and `mileage.py`. Hide the controls in `rides/log.html` and `maintenance/history_list.html` for locked owners.
- [x] T016 [P] [US1] Tests first:
  - **Archived bike's Edit screen** (`tests/routers/test_archive.py`): `p.archived-notice`, `dl.readonly-details` with no Save and no sync-rules form, `section.unarchive-card`, and the Delete card. No Archive card and no Strava card.
  - **Archived bike's main screen** (`tests/routers/test_builder.py`): the archived notice; only the storage drop zone in the palette; no `drop-target` on nodes or the root; no Add or Delete controls.
- [x] T017 [US1] Implement T016 in `bikes/form.html`, `partials/builder.html`, `partials/archive_card.html` and `builder_service` (a `locked` flag on the view), per T003.
- [x] T018 [P] [US1] Test first in `tests/db/test_mileage.py` and `tests/services/test_sync_service.py`: re-importing the same Strava activity with another bike's gear doesn't move or change a ride on an archived bike; it still updates rides on active bikes.
- [x] T019 [US1] Implement T018 in `app/db/mileage.py` `upsert_ride_activity` (research §7).

**Checkpoint**: a bike can be archived end to end.

## Phase 4: User Story 2 - Take parts off an archived bike or part (P1)

**Goal**: the only change on a locked item is taking a part off to storage (FR-006, FR-007).

**Independent Test**: quickstart steps 5 and 6.

- [x] T020 [P] [US2] Tests first (written as route tests in `tests/routers/test_archive.py`, which exercise the services):
  - On an archived bike, a part moves to storage (`/builder/move` target storage, and `/components/{id}/move` to storage) with its sub-parts inside, removed now.
  - Moving it elsewhere, adding a part onto or into it, reordering, and `/builder/delete` of a part in the tree all answer 409 and change nothing.
- [x] T021 [US2] Implement T020 in `component_service.move_component`, `builder_service` add and delete, and `app/routers/builder.py` and `components.py`.
- [x] T022 [P] [US2] Tests first (route tests in `tests/routers/test_archive.py`):
  - Ending a still-installed period whose place is locked moves the part to storage at the typed moment, sub-parts inside.
  - Changing that period's place or install moment is refused.
  - Logging, editing or deleting a closed period placed in a locked item is refused.
  - The Edit form of such a still-installed period shows only the removal fields.
  - The archived bike's Install History has no Log or Delete controls.
  - `parent_options` and the period Bike list leave out locked items.
- [x] T023 [US2] Implement T022 in `component_history_service`, `app/routers/component_history.py`, `components/install_period_form.html`, `components/install_history.html` and `bikes/install_history.html`.
- [x] T024 [P] [US2] Test first in new `tests/routers/test_archive_route_walk.py`:
  - Walk every router's `.router.routes`. Every POST must be on one of two lists: "checks the lock" (each one tested in T014, T020 and T022 with a locked item), or "not about one bike or part" (settings, auth, backup, sync, notifications).
  - A new POST fails the test until it's listed.
- [x] T025 [US2] Make T024 pass by listing the routes; add any guard it finds missing.

## Phase 5: User Story 3 - Archive a part (P2)

**Goal**: a part in storage can be archived and is left out of pickers and counts.

**Independent Test**: quickstart steps 7 and 8.

- [x] T026 [P] [US3] Tests first:
  - **`archive_part` and its route:**
    - in storage, with keep or move, behaving as for bikes;
    - an installed part raises `ValueError("Take this part off to storage before archiving it.")`, answers 422, and nothing changes.
  - **Edit screens** (`components/form.html`): an installed part's Archive card shows that sentence and no button. An archived part shows read-only details, an Unarchive card and Delete.
  - **`GET /components`:** `details.archived-section` "Archived (N)".
  - **Left out of pickers and counts:** the builder's "In storage (N)", the Garage's Storage (N), and `parent_options`.
- [x] T027 [US3] Implement T026 in `archive_service`, `app/routers/archive.py`, `component_service.list_in_storage` and `list_archived_parts`, `components/form.html`, `components/list.html`, `partials/storage_card.html` and `builder_service`.

## Phase 6: User Story 4 - Unarchive (P2)

**Goal**: Unarchive on the Edit screen returns the item to active; schedules don't come back.

**Independent Test**: quickstart step 9.

- [x] T028 [P] [US4] Tests first:
  - `unarchive_bike` and `unarchive_part` clear `archived_at`. Schedules stay off, and the bike stays unpaired.
  - `POST /bikes/{id}/unarchive` and `/components/{id}/unarchive` answer 303 to the Edit screen, which is editable again. On an active item, they answer 409.
  - After unarchiving, pairing runs the full backfill.
- [x] T029 [US4] Implement T028 in `archive_service` and `app/routers/archive.py`.
- [x] T030 [US4] Test first, then fix: the Unarchive card's wording matches the approved mock-up (effects list, "Unarchive bike" / "Unarchive part").

## Phase 7: Polish and cross-cutting

- [x] T031 [P] Tests first in `tests/services/test_backup_service.py`: `archived_at` round-trips through export and restore. A file without the column restores as active.
- [x] T032 [P] Test first: deleting an archived bike (typed name) and an archived part still works. Parts go to storage with their sub-parts inside.
- [x] T033 [P] Amend the specs named in plan.md (001 `contracts/routes.md`, 006, 015/030, 017, 020/033, 029, 067) with Amendments lines, and add the new routes to `specs/001-bike-maintenance-tracker/contracts/routes.md`.
- [x] T034 [P] `CLAUDE.md`: an "Archive (feature 079)" paragraph naming `archive_service.is_locked` and `require_unlocked`, the 409 refusal, `archived_at`, the routes, the Archived sections, and the route-walk test.
- [x] T035 Run the full suite. Then run `quickstart.md` by hand in the browser on a local server, and record the result here. *Result (2026-11-18): full suite 1,683 passed. Local server, seeded with a paired 2014 Madone (groupset with chain, wheelset with tires, three schedules), an active SLR7 and a spare saddle:*
  - *The Edit screen showed the full-width Archive card below Strava and Delete, with 2 schedules, 4 parts and the two unchecked choices. "Keep them on the bike" archived it and landed on the Garage, where "Archived (1)" was closed and, opened, read "Archived 2026-11-18".*
  - *Every schedule was off and the bike unpaired.*
  - *The archived screen showed the notice, no Schedules or Pair button, and only "In storage". A real drag of the groupset to storage took it off with its chain still inside; a drag of the tires onto the bike did nothing.*
  - *The archived Edit screen was read-only with Unarchive beside Delete. Unarchive returned to an editable Edit screen (Save, Archive bike).*
- [x] T036 Run `/speckit-analyze` for 079 and resolve any CRITICAL or HIGH finding. *Result: none. MEDIUM, fixed: the spec now says parts kept on an archived item are locked until taken off (approved in the plan, research §1). LOW, noted: the part Edit screen gains a Delete card only when archived (FR-011 asks for Delete from Edit; active parts keep Trash on their screen).*

## Dependencies

- **Before templates:** T003 (mock-ups approved) blocks every template task.
- **Foundation:** Phase 2 blocks every story.
- **US1** is the MVP. US2 needs US1's archiving and guards (T011, T015).
- **US3** needs Phase 2 and T013's route and partial.
- **US4** needs US1 or US3.
- **Polish** comes last.

## Parallel examples

- T004, T006 and T008 (different files).
- T010, T012, T014 and T018, written together; implement them in order.
- T020, T022 and T024.

## Implementation strategy

US1 first, which lets the rider archive a sold bike. Then US2, so kept parts can come off. Then US3 and US4. The route walk (T024) closes any guard a story missed.
