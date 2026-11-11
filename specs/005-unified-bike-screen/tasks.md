---

description: "Task list for the Unified Bike Screen and Simpler Parts feature"
---

# Tasks: Unified Bike Screen and Simpler Parts

**Tests**: REQUIRED, written first (constitution Principle III). Milestones end green, committed, with a tagged image.

## Milestone 1: Bike entry and simpler parts (US1, US2) → `bikemaint:m1-bike-entry`

- [X] T001 [US1] Migration `0007_bike_year_make_model.sql`; tests in `tests/db/test_bikes_year_make_model.py`; update `app/models/rows.py`, `app/db/bikes.py`
- [X] T002 [US1] Remove `app/services/bike_catalog.py` and its tests; `bike_service.create_bike_from_details` / `update_bike_from_details` with tests (derived name, suffix, legacy keep/replace/mixed)
- [X] T003 [US1] `BikeDetailsRequest` in `app/models/requests.py` (year 1900..next year, make/model 1..60 trimmed, category allow-list) with tests
- [X] T004 [US1] Router + `bikes/form.html` (Year, Make, Model text; Category select; legacy hint) with tests in `tests/routers/test_bikes.py`; migrate tests that used `catalog_id`
- [X] T005 [US2] `component_kinds`: offered flag, simplified kinds, new parents/multi rules, `COMPONENT_TYPES` offered only, `ALL_COMPONENT_TYPES`; tests rewritten in `tests/models/test_component_kinds.py`
- [X] T006 [US2] Boundary and forms offer only offered kinds (create/palette/edit), legacy kinds still readable and movable; update service/router/UI tests that create rim/hub/spoke over HTTP
- [X] T007 M1 checkpoint: full suite green, build `bikemaint:m1-bike-entry`, verify, commit

## Milestone 2: Unified screen (US3) → `bikemaint:m2-unified-screen`

- [X] T008 [US3] `builder_service`: root-based `build_view`, scope checks in `add_part`/`move_part`/`delete_part`, `breadcrumbs`; tests in `tests/services/test_builder_service.py`
- [X] T009 [US3] Router `app/routers/builder.py`: `/builder/add|move|delete`, confirmation panel, root redirects; build-page redirect; tests in `tests/routers/test_builder.py`
- [X] T010 [US3] Templates: unified `bikes/detail.html` and `components/detail.html`, `partials/breadcrumb.html`, `partials/part_actions.html`, row Garage/Trash buttons, builder fragment with `data-root`; remove `bikes/build.html`, Build/Add component buttons, Move form; update `builder.js` to send `root`; UI tests
- [X] T011 [US3] CSS for breadcrumb, action bar, row buttons, confirmation panel; asset/contrast tests
- [X] T012 Docs (README, CLAUDE.md, contracts), mark tasks, full suite, build `bikemaint:m2-unified-screen`, verify drag/drop and drill-down in the browser, commit
