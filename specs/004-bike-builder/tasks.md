---

description: "Task list for the Bike Catalog and Interactive Builder feature"
---

# Tasks: Bike Catalog and Interactive Builder

**Input**: Design documents from `/specs/004-bike-builder/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/routes.md, quickstart.md

**Tests**: REQUIRED (constitution Principle III): write each test first and watch it fail. Drag behavior itself is verified manually at the M3 checkpoint; everything the server does is tested.

**Milestones** (each ends green, committed, with a tagged Docker image and a checkpoint report):
- **M1** Bike catalog (US1) → image `bikemaint:m1-bike-catalog`
- **M2** Placement rules (US2) → image `bikemaint:m2-placement-rules`
- **M3** Interactive builder (US3) → image `bikemaint:m3-builder`

## Format: `[ID] [P?] [Story] Description`

---

## Milestone 1: Bike catalog (US1, P1)

- [X] T001 [US1] Create `tests/services/test_bike_catalog.py` (about 60 entries; unique slugs; categories only road/gravel/mountain/hybrid/e-bike; grouping by category then make; `display_name`; `get(id)` returns None for unknown) and implement `app/services/bike_catalog.py`
- [X] T002 [US1] Create migration `app/db/migrations/0005_bike_catalog_id.sql`; extend `tests/db/test_bikes.py`-style coverage (`catalog_id` stored and read) in `tests/db/test_bikes_catalog_id.py`; update `app/models/rows.py` `Bike` and `app/db/bikes.py`
- [X] T003 [US1] Extend `tests/services/test_bike_service.py`: `create_bike_from_catalog` sets name/type/catalog_id, numeric suffix for duplicates ("(2)", "(3)", ignoring soft-deleted bikes), unknown id raises; `update_bike_from_catalog` and keep-current for legacy bikes only; implement in `app/services/bike_service.py`
- [X] T004 [US1] Update `tests/models/test_requests.py` (`BikeCatalogRequest` accepts only catalog ids or `__keep__`, rejects blank/forged) and `app/models/requests.py`
- [X] T005 [US1] Update `tests/routers/test_bikes.py` and `tests/test_ui_pages.py`/`tests/test_quickstart.py` where bikes are created with a free-text `name`: new form markup (no `name`/`bike_type` inputs, `<select name="catalog_id">` with optgroups), create/edit success and 422 paths, legacy keep-current, duplicate suffix through HTTP; then update `app/routers/bikes.py` and `app/templates/bikes/form.html`
- [X] T006 [US1] Keep the existing service/test helpers working (tests and the seed use `bike_service.create_bike(name=...)`): leave `create_bike` for internal/legacy use and document it; confirm the full suite passes
- [X] T007 [US1] M1 checkpoint: full suite green, `docker build -t bikemaint:m1-bike-catalog .`, verify the image runs and the add-bike flow works in the browser, mark tasks, commit, report

## Milestone 2: Placement rules (US2, P2)

- [X] T008 [US2] Create `tests/services/test_component_kinds.py` (every type has a label; allowed parents reference real types or "bike"; spec examples: pedal→crankset not wheel, tire→rim not bike, rim/hub/spoke→wheel, bolt/other anywhere, storage always allowed; message text names allowed parents; `valid_parent_types(type)`; existing types all present) and implement `app/models/component_kinds.py`
- [X] T009 [US2] Update `app/models/requests.py` `COMPONENT_TYPES`/`MULTI_INSTANCE_COMPONENT_TYPES` from the catalog (single source of truth) with tests
- [X] T010 [US2] Extend `tests/services/test_component_service.py`: create/update-type/move refuse invalid placements with the catalog message; single-instance rule still applies; pre-existing invalid arrangements stay readable; moving to storage always ok; then implement `_validate_placement` in `app/services/component_service.py`
- [X] T011 [US2] Update `tests/routers/test_components.py` and affected UI/quickstart tests for 422 messages and for forms offering only valid types/parents (component create form lists types valid under the chosen parent; move form shows valid parents); update `app/routers/components.py` and `app/templates/components/*.html`
- [X] T012 [US2] Fix any existing tests that built now-invalid trees (document each change in the commit message)
- [X] T013 [US2] M2 checkpoint: full suite green, `docker build -t bikemaint:m2-placement-rules .`, verify manually (pedal on wheel refused, tire on rim ok), mark tasks, commit, report

## Milestone 3: Interactive builder (US3, P3)

- [X] T014 [US3] Create migration `0006_component_position.sql` and tests (`tests/db/test_components_position.py`): backfill by id, new children get max+1, `list_children`/tree reads ordered by `position, id`, `reorder_before` renumbers siblings; implement in `app/db/components.py`
- [X] T015 [US3] Extend `tests/services/test_component_service.py`: `move_component(..., before_component_id=)` re-orders within a parent and inserts before a sibling in a new parent; no-op when unchanged; cannot reference a non-sibling; unmount to storage; `mount_new_component(bike_id, type, parent)` creates with the type's default name and validates placement; implement in `app/services/component_service.py`
- [X] T016 [US3] Add `valid_targets_for(component_or_type, bike_tree)` and the builder view model (tree nodes with `accepts`, storage list, palette grouped by kind, per-item valid-target options) with tests in `tests/services/test_builder_service.py`; implement `app/services/builder_service.py`
- [X] T017 [US3] Router tests `tests/routers/test_builder.py`: `GET /bikes/{id}/build` (404, markup: two panes, drop targets with `data-accepts`, draggable items, palette, Move-to selects listing only valid targets, empty-bike state), `POST /bikes/{id}/build/add`, `POST /components/{id}/move` with `before_component_id` and `return=builder`, HTMX fragment vs redirect, 422 with alert message, auth required; implement `app/routers/components.py`/`bikes.py` routes and templates `bikes/build.html`, `partials/builder_tree.html`, `partials/builder_side.html`
- [X] T018 [US3] Tree ordering on the bike detail and component pages uses `position` (tests in `tests/test_ui_pages.py`); link "Build" from the bike detail and garage card
- [X] T019 [US3] Add `app/static/builder.js` (vanilla DnD: dragstart marks valid targets from `data-accepts`, drop posts via `htmx.ajax` to the move/add endpoints, reorder via nearest sibling `before_component_id`, status messages in an `aria-live` region) with static tests `tests/test_ui_builder_assets.py` (served, no external URLs, no framework, references the data attributes the templates emit); builder CSS in `app/static/styles.css` (split panes stacking under 64rem, valid/invalid target states, drag handle, reduced motion) with contrast/asset-budget checks
- [X] T020 [US3] Update `tests/test_ui_contrast.py` budgets if needed; update README, CLAUDE.md and `specs/004-bike-builder/contracts/routes.md` to match what was built
- [X] T021 [US3] M3 checkpoint: full suite green, `docker build -t bikemaint:m3-builder .`, verify drag/drop, invalid drop message, reorder persistence and keyboard Move-to in the browser, mark tasks, commit, report

## Dependencies and Order

M1 → M2 → M3 (M3 uses the catalog from M2 and the position migration). Within a milestone: tests first, then implementation. T001–T004 can run in parallel with each other only where files differ; T005 depends on T003 and T004.
