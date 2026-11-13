# Tasks: 020 Free Part Placement and a Categorised Part Palette

**Input**: `specs/020-free-placement-and-categories/` (spec.md, plan.md, research.md, data-model.md, contracts/ui-contract.md, quickstart.md)

**Tests**: Required and written first (constitution III): rewrite or add the failing test, watch it fail, then the minimal code.

Format: `- [ ] ID [P] [Story] Description (file paths)`.

## Phase 1: Foundational — the catalog (blocks both stories)

- [x] T001 Rewrite `tests/models/test_component_kinds.py` for the new catalog: 34 offered kinds in the order of `data-model.md` grouped under Accessories, Brakes, Drivetrain, Frame, Wheels; each kind has a display `name` and `category`; legacy kinds `drivetrain`, `other`, `rim`, `spoke`, `bolt` are valid (`ALL_COMPONENT_TYPES`) but not offered; no `placement_error`/`can_mount`/`child_types_for`/`parent_types_for`/`MULTI_INSTANCE_COMPONENT_TYPES` remain. Watch it fail.
- [x] T002 Restructure `app/models/component_kinds.py`: `ComponentKind(type, name, category, offered)`; offered list with the 16 new ids (`accessories apparel computer lights brake_cable brake_lever bottom_bracket chainrings shifter_cable handlebar_tape headset shock axle trainer tube wheelset`) and reused ids (`pedal`→Pedals, `shifter`→Shift levers, `pad`→Brake Pads, plus hub, cassette, crankset, derailleur, stem, seatpost now offered); `CATEGORIES` ordered tuple; helpers `kind_name(type)` (falls back to the raw id) and `offered_by_category()`; delete placement rules and the multi flag. Update `app/models/requests.py` imports (drop `MULTI_INSTANCE_COMPONENT_TYPES`).
- Note: the count of offered parts is **34** (4+5+9+9+7), not 36 as first written; corrected everywhere.

## Phase 2: User Story 1 — Put any part on any part (P1)

**Independent test**: drag/add a chain onto a wheel, a saddle onto a tire, and two chains onto one bike; all succeed; a part into its own sub-tree is refused.

- [x] T003 [US1] Rewrite tests that assert the old rules so they assert free placement: `tests/services/test_component_service.py` (add/move any kind under any parent, any count; keep self/descendant refusal; `list_placement_targets` (replaces `list_type_targets`) and `list_move_targets` return every slot in scope, excluding the part and its sub-tree when moving), `tests/routers/test_component_rules.py` and `tests/routers/test_builder.py` (no "can be mounted"/"already installed there" refusals; HTTP 303/200 for previously refused placements). Watch them fail.
- [x] T004 [US1] `app/services/component_service.py`: remove `_validate_placement`, the one-per-kind check in `_validate_nesting`, `ComponentNestingConflictError` raising for placement, type-change child validation in `update_component`, and the kind filters in `_candidate_targets`/`valid_types_for_parent`; keep the "not inside itself or its own sub-tree" check and the offered-kind check on create/update. `list_type_targets` returns every slot in scope.
- [x] T005 [P] [US1] `app/routers/components.py` and `app/routers/builder.py`: stop special-casing `ComponentNestingConflictError` where it is no longer raised (keep `ValueError` handling for the cycle refusal); the type choice on the part form lists the offered kinds.
- [x] T006 [US1] `app/services/builder_service.py` and `app/templates/partials/builder.html`: every node and the root accept every type (drop `_accepts`/`data-accepts` filtering); `app/static/builder.js`: a drop target accepts any type except inside the dragged part's own sub-tree. Test in `tests/test_ui_builder_assets.py` that `builder.js` no longer reads `data-accepts`.

## Phase 3: User Story 2 — Categorised, collapsible palette (P2)

**Independent test**: a bike screen shows five collapsed categories; expanding Brakes and Wheels together lists their parts; all 34 parts appear on every screen.

- [x] T007 [US2] Tests first: `tests/services/test_builder_service.py` (palette is grouped by category in the supplied order, lists all 34 offered kinds on bike and part screens, each item has display name and target list = every slot), `tests/routers/test_builder.py` (rendered page has exactly five `details.palette-category` with no `open` attribute, the category names in order, and each part's display name), `tests/test_ui_icons.py` (new kinds render an icon without error; unknown kinds fall back to the wrench), and a `kind_name` display test (chip shows "Shift levers" for a `shifter` part) in `tests/routers/test_builder.py`. Watch them fail.
- [x] T008 [US2] `app/services/builder_service.py`: `PaletteCategory(name, items)` and `BuilderView.palette` grouped by category using `component_kinds.offered_by_category()`; `PaletteItem` carries the display name; no filtering by targets.
- [x] T009 [US2] Templates: `app/templates/partials/builder.html` renders one `<details class="palette-category"><summary>…</summary><ul class="side-list palette">…</ul></details>` per category, never `open`; chips, `app/templates/components/detail.html`, `app/templates/partials/storage_card.html` and `app/templates/components/form.html` show `kind_name`; register the `kind_name` Jinja filter in `app/main.py`; `app/static/styles.css` styles `.palette-category` (summary as a clickable header, marker kept, focus ring) using existing tokens; `tests/test_ui_contrast.py` must stay green.
- [x] T010 [P] [US2] `app/templates/partials/icons.html`: map new kinds to the nearest icon (brake_lever, brake_cable → brake; bottom_bracket, chainrings → drivetrain; shifter_cable → chain; axle, trainer → wheel; tube → tire; headset, shock → fork; handlebar_tape → handlebar) with the wrench as the fallback.

## Phase 4: Polish

- [x] T011 Run `.venv/bin/python -m pytest -q`; all tests pass.
- [x] T012 `CLAUDE.md`: update the UI paragraph (placement rules and one-per-kind removed; palette is categorised; catalog in `app/models/component_kinds.py` carries names and categories). Add "superseded for placement by 020" notes to the Assumptions of `specs/004-bike-builder/spec.md` and `specs/005-unified-bike-screen/spec.md`.
- [x] T013 Ran `/speckit-analyze` for 020: no CRITICAL or HIGH findings. MEDIUM: part count was 34 not 36 (fixed); removing the rules dropped the missing-parent refusal (fixed, T014). LOW: FR-006/FR-010 are native `<details>` behavior asserted structurally only. **Not done**: manual quickstart and a visual check of the new palette CSS in a browser (blocked in this session); verified by tests only.

## Added during implementation

- [x] T014 [US1] Regression found by the old tests: with the rules removed, a missing parent raised a database foreign-key error. Added `_require_parent_exists` in `app/services/component_service.py` (LookupError for create and move) with test `tests/services/test_free_placement.py::test_a_missing_parent_is_refused_cleanly_for_create_and_move`.
- [x] T015 Replaced the kind-based `list_type_targets` with `list_placement_targets` (no dummy kind argument) in `app/services/component_service.py` and `app/services/builder_service.py`.

## Phase 5: Amendment from user testing (branch 021-fix-palette-drag-and-style)

- [x] T016 [US2] Tests first: `tests/services/test_asset_service.py` (`static_url("styles.css")` returns `/static/styles.css?v=<token>`; the token changes when the file's content changes and is stable when it does not), `tests/test_ui_assets.py` (rendered pages link `styles.css`, `htmx.min.js`, `localtime.js` and `builder.js` with a `?v=` token; no template still uses a bare `url_for('static', …)` for css or js). Watch them fail.
- [x] T017 [US2] `app/services/asset_service.py` (`static_url`, content-hash token cached per file mtime and size, no FastAPI imports); register it as the Jinja global `static_url` in `app/main.py`; switch the css and js links in `app/templates/layout.html`, `app/templates/bikes/detail.html` and `app/templates/components/detail.html`.
- [x] T018 [US2] Dropped: after the browser refreshed its files the category headers already matched the app's style (rider confirmed with a screenshot), so no restyle or token test was needed.
- [ ] T019 Run the full suite, `/speckit-analyze`-style check of the amended spec, and note in the PR that the headers could not be eyeballed in a browser by Claude; the rider should hard refresh once.

## Dependencies

- T001 → T002 (red, green) → everything else.
- US1 (T003–T006) and US2 (T007–T010) both need Phase 1; US2's palette also needs T004's "targets = every slot". Deliver US1 first (MVP), then US2.
- T005 and T010 touch different files from their neighbours and can run in parallel with them.
- T011–T013 run last.

## Implementation Strategy

MVP is Phase 1 plus User Story 1: free placement works with the old flat palette untouched. Then add the categories. The suite stays green at the end of each phase.
