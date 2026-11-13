# Implementation Plan: 022 Install History Split From Maintenance History

**Branch**: `022-install-history-split` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

## Summary

Stop writing automatic "added/removed" entries into maintenance history, delete the ones already there (a one-statement migration), and add a read-only Install History screen per bike built from the installation periods that already exist.

## Technical Context

**Language/Version**: Python 3 (CPython 3.13)

**Primary Dependencies**: FastAPI, Jinja2, HTMX (unchanged)

**Storage**: SQLite. One migration, `0010_remove_part_event_entries.sql`: `DELETE FROM maintenance_log_entry WHERE kind = 'event'`. The `kind` column and its default stay (it is harmless and keeps the migration to a single statement).

**Testing**: pytest (`tests/db`, `tests/services`, `tests/routers`)

**Target Platform**: Self-hosted container (unchanged)

**Project Type**: web-service

**Performance Goals**: A bike's history is one indexed query (`component_installation_period.parent_bike_id`); tens to low hundreds of rows

**Constraints**: Install periods store the **top bike** (`parent_bike_id`) and the direct parent part (`parent_component_id`), so a bike's history is exactly the periods with that `parent_bike_id`, including nested parts

**Scale/Scope**: One rider

## Constitution Check (v1.3.0)

| Principle | Result | Notes |
|---|---|---|
| I Simplicity | Pass | Removes code (event writers); the new screen reuses periods and the existing table style |
| II Modular design | Pass | Query in `app/db/components.py`, assembly in `component_history_service`, thin route in `app/routers/component_history.py`, template under `app/templates/bikes/` |
| III TDD | Pass (planned) | Each task test-first; tests that assert event entries are rewritten before the code is removed |
| IV Security | Pass | Route requires sign-in via `require_account`; parameterised SQL; the migration has no input |
| V Observability | Pass | No new failure paths |
| Stack / layout | Pass | One migration file in the existing directory; no new dependency |

## Project Structure

### Documentation (this feature)

```text
specs/022-install-history-split/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/routes.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
app/
├── db/
│   ├── migrations/0010_remove_part_event_entries.sql   # delete existing automatic entries
│   └── components.py                                    # list_periods_for_bike(bike_id)
├── services/
│   ├── component_service.py          # delete _log_event/_log_added/_log_removed and their calls
│   └── component_history_service.py  # delete _log_event and its two calls; describe_bike_history(bike_id)
├── routers/
│   └── component_history.py          # GET /bikes/{bike_id}/install-history
├── templates/
│   ├── bikes/install_history.html    # read-only table
│   ├── partials/part_actions.html    # "Install history" button for a bike
│   └── maintenance/history_list.html # drop the event row styling and "Parts" tag
└── static/styles.css                 # drop the now-unused .entry-event / .entry-tag rules if present
tests/                                # mirrors app/
```

**Structure Decision**: Existing layout; the bike's screen lives beside the part's in `component_history`.

## Design Decisions (detail in research.md)

1. Delete by `kind = 'event'`, never by text.
2. Stop writing events at their source (five call sites) rather than filtering at read time.
3. Bike history is derived from periods (`parent_bike_id = bike`), joined to the part for name and kind, including soft-deleted parts (shown without a link).
4. Places: parent part's name, else the bike itself; deleted parent shown as "a deleted part".
