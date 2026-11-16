# Tasks: Smoother Drag and Collapsible Parts in the Builder

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [contracts/ui-contract.md](contracts/ui-contract.md), [quickstart.md](quickstart.md)
**Tests**: required (constitution III, TDD). Write each failing test before its code.

## Phase 1: Setup

- [x] T001 Confirm the baseline suite is green on branch `073-builder-drag-collapse` (`.venv/bin/python -m pytest -q`)

## Phase 2: Foundational

- [x] T002 [P] Failing test: `BuilderNode.descendant_count` counts all sub-parts at every depth (0 for a leaf), in tests/services/test_builder_service.py
- [x] T003 Add the `descendant_count` property to `BuilderNode` in app/services/builder_service.py

## Phase 3: User Story 2 - Collapsible parts (markup first, because US1 and US3 rely on it)

- [x] T004 [P] [US2] Failing tests in tests/routers/test_builder.py:
  - a row with sub-parts has `button.twisty` with `aria-expanded="true"`, `aria-label="Collapse <name>"` and `title="Hide sub-parts"`, plus `.sub-count` reading "N parts" ("1 part" for one);
  - a leaf row has `span.twisty-space` and no `.sub-count`;
  - the button comes before the drag handle;
  - the button is `type="button"`, so without scripts it submits nothing (FR-010).
- [x] T005 [US2] Render the chevron, spacer and count in `render_nodes` in app/templates/partials/builder.html
- [x] T006 [P] [US2] Failing tests in tests/test_ui_builder_assets.py:
  - the script toggles `is-collapsed`, reads and writes `localStorage` key `bikemaint.collapsed` inside try/catch, and updates `aria-expanded`, `aria-label` and `title`;
  - the CSS hides `.sub-count` unless collapsed and hides the sub-parts of a collapsed part except a `.drop-slot`;
  - `.twisty` and `.twisty-space` have equal size.
- [x] T007 [US2] Collapse toggle (click, slide, remember, reapply on load and after `htmx:afterSwap`) in app/static/builder.js; styles in app/static/styles.css (section "specs/073")

## Phase 4: User Story 1 - Drag gap (P1)

- [x] T008 [P] [US1] Failing tests in tests/test_ui_builder_assets.py:
  - the script creates `drop-slot` without `innerHTML`, uses `is-lifted`, `.animate(` and `getAnimations`;
  - it uses a 0.3 zone with 0.12 stickiness;
  - it keeps the storage drop rule (a part already in storage can't be dropped on storage);
  - every class it sets (`is-dragging`, `is-lifted`, `is-over`, `is-valid`, `is-collapsed`, `is-closing`, `drop-slot`, `slot-row`, `slot-where`) is styled;
  - it stays ≤ 16 KB (raised from 12 KB; see research §5).
  
  Replace the 004 regex test for the old storage line and the `is-invalid` class check.
- [x] T009 [US1] Gap, FLIP glide, settled-box zones, stickiness, drop and cancel in app/static/builder.js; slot, lifted and holder styles in app/static/styles.css. Remove the now unused `is-invalid` styling.

## Phase 5: User Story 3 - Dragging with collapsed parts

- [x] T010 [US3] In app/static/builder.js:
  - collapsed parts take a drop as if they had no shown sub-parts;
  - hovering inside one for 700 ms opens it and makes the gap its first sub-part;
  - dropping inside one removes it from the collapsed set.
  
  Add the matching static checks to tests/test_ui_builder_assets.py.

## Phase 6: Polish

- [x] T011 Browser check against a local server, following quickstart.md steps 1–7, at about 1,200 px wide
- [x] T012 [P] Amend specs/020-free-placement-and-categories/contracts/ui-contract.md (pointer to 073), CLAUDE.md (feature note), and the 004 test docstring
- [x] T013 Full suite green

## Dependencies

- T002 → T003 → T004 → T005.
- T006 → T007.
- T008 → T009 → T010.
- T011 needs T005, T007, T009 and T010.
- Within a phase, write the test first and then the code.

## Parallel opportunities

T002, T004, T006 and T008 are test files and could be drafted together. The code tasks share builder.js and styles.css, so they run in sequence.

## Implementation strategy

The MVP is US1, the drag gap, which fixes the reported problem. The collapse markup lands first only because US3 and the slot CSS depend on its classes.
