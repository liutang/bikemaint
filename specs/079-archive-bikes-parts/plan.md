# Implementation Plan: Archive Bikes and Parts

**Branch**: `079-archive-bikes-parts` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

## Summary

Bikes and parts gain an `archived_at` column (migration `0021_archived_items.sql`). A new `archive_service` owns:
- archiving and unarchiving;
- the keep-or-move choice for attached parts;
- the one rule every other service asks before changing anything: `is_locked`.

An item is locked when it is archived, or sits anywhere inside an archived bike or part. A locked item allows only one change: taking a part off to storage.

Every mutating service checks the rule and raises `ArchivedError`. Routers answer that with 409 and the form's message, or an HTMX error fragment. Lists, pickers and counts leave archived items out. The Garage and Storage get a collapsed `<details>` "Archived (N)" section.

Edit screens:
- **Active bike or part:** a full-width Archive card below Strava and Delete (mock-up Option B).
- **Archived bike or part:** shown read-only, with an Unarchive card beside Delete.

Strava upserts skip rides of archived bikes.

Decisions are in [research.md](research.md), storage in [data-model.md](data-model.md), routes in [contracts/routes.md](contracts/routes.md), and markup in [contracts/ui-contract.md](contracts/ui-contract.md).

## Technical Context

**Language/Version**: Python 3.12 (container 3.13-slim)
**Primary Dependencies**: FastAPI, Pydantic v2, Jinja2, HTMX. Nothing new.
**Storage**: SQLite. Migration `0021_archived_items.sql` adds `archived_at TEXT NULL` to `bike` and `component`. Backups are schema-driven, so they carry it with no format change.
**Testing**: pytest.
- Each service rule is tested in `tests/services/test_archive_service.py`.
- Every guarded route gets a refusal test, walking each router's `.router.routes` against a list of allowed routes, so a new route can't skip the check.

**Target Platform**: self-hosted Linux container
**Project Type**: web service (server-rendered)
**Performance Goals**: `is_locked` is one recursive CTE up a part's parent chain (depth 8 at most), run once per mutation. Negligible.
**Constraints**:
- no JavaScript beyond `builder.js`, and none is expected to change: an archived screen renders no drop targets except storage;
- the collapsed sections use `<details>`, closed on load.

**Scale/Scope**: about 15 app modules, 10 templates, and amendments to specs 001, 006, 015/030, 017, 020/033, 029 and 067.

## Constitution Check

- **Fixed stack**: no new library. `<details>` needs no script. PASS
- **Layout**:
  - `app/services/archive_service.py` holds the business rules.
  - `app/db/bikes.py` and `components.py` hold parameterized queries (`set_archived`, `list_archived`, `locked_ids`).
  - Routers only translate `ArchivedError` to 409.
  - Templates hold the markup.
  - Tests mirror the files: `tests/services/test_archive_service.py`, `tests/routers/test_archive.py`, `tests/db/test_archive_queries.py`.

  PASS
- **I. Simplicity**: one lock rule in one function, rather than per-route conditions. The "move" choice reuses `component_service.detach_to_storage`. PASS
- **III. TDD**: each story starts with failing service tests, then route and template tests. PASS
- **IV. Security**: refusals are enforced server-side on every route, including HTMX endpoints (`/builder/*`, `/sync-rules`), not only by hiding buttons. The archive choice is validated by Pydantic (`Literal["keep", "move"]`). PASS
- **V. Observability**: archiving and unarchiving each log one line, for example `bike archived bike_id=3 schedules_deleted=2 attached=move parts_moved=4 unpaired=true`. A refusal logs at info with the route and id. PASS
- **Git**: one branch, one PR; atomic commits per story. PASS

Re-checked after design: PASS. Nothing to track under Complexity.

## Project Structure

### Documentation (this feature)

```text
specs/079-archive-bikes-parts/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/routes.md       # new routes and the 409 refusal
├── contracts/ui-contract.md  # Archive / Unarchive cards, Archived sections, read-only screens
├── checklists/requirements.md
└── tasks.md                  # /speckit-tasks
```

Amended outside this folder:

| Spec | What changes |
|---|---|
| 001 `contracts/routes.md` | new archive and unarchive routes; 409 for locked items |
| 006 | rides of an archived bike are read-only |
| 015 / 030 | periods placed in a locked item can only be ended |
| 017 | archiving unpairs, and Strava never changes an archived bike's rides |
| 020 / 033 | an archived screen's builder offers only the storage drop; the palette leaves archived parts out |
| 029 | deleting an archived bike works as today |
| 067 | backups carry `archived_at` |
| `CLAUDE.md` | one paragraph for 079 |

### Source Code (repository root)

```text
app/db/migrations/0021_archived_items.sql   # NEW
app/db/bikes.py, app/db/components.py       # archived_at in rows; set_archived, list_archived, locked_ids; list_active stays "not deleted"
app/models/rows.py                          # Bike.archived_at, Component.archived_at
app/models/requests.py                      # ArchiveRequest(attached: Literal["keep","move"] | None)
app/services/archive_service.py             # NEW: archive/unarchive, is_locked, require_unlocked, ArchivedError
app/services/bike_service.py, component_service.py, builder_service.py, component_history_service.py,
  ride_service.py, maintenance_service.py, schedule_service.py, sync_rule_service.py, sync_service.py
                                            # call require_unlocked; active-only lists for pickers
app/db/mileage.py                           # upsert_ride_activity skips rides of archived bikes
app/routers/archive.py                      # NEW: POST /bikes/{id}/archive|unarchive, /components/{id}/archive|unarchive
app/routers/*.py                            # ArchivedError -> 409 (shared helper in app/routers/screen.py)
app/templates/bikes/list.html, components/list.html            # Archived (N) <details>
app/templates/partials/bike_row.html, storage_card.html        # "Archived <date>" line
app/templates/bikes/form.html, components/form.html            # Archive card (active) / read-only + Unarchive card (archived)
app/templates/partials/archive_card.html                       # NEW: shared Archive and Unarchive cards
app/templates/partials/builder.html, rides/log.html, maintenance/history_list.html,
  components/install_history.html, bikes/install_history.html  # locked: no add/edit/delete controls
app/static/styles.css                       # .archived-section, .archive-card spanning the grid
tests/... mirroring each file above
```

**Structure Decision**: the existing layout, plus one service, one router, one partial and one migration.

## Before building the screens

The Garage and Storage "Archived (N)" sections and the archived bike screen haven't been mocked up yet. Per the rider's rule for visual changes, they are mocked up and approved before their template tasks start. The Edit screens were approved on 2026-11-18 (Option B, and the Unarchive card).

## Complexity Tracking

None.
