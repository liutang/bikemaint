# Tasks: 028 Storage Part Links

- [x] T001 [US1] Tests first in `tests/routers/test_builder.py`: on a bike screen and on a part screen each stored part's name is `<a href="/components/{id}">name</a>` inside the In storage card, the kind chip is outside the link, the list item is still `draggable="true"` with `data-source="storage"` and its "Add to…" form is unchanged; opening the link shows the breadcrumb Garage › Storage › the part (`Storage` links to `/components`). Watch them fail.
- [x] T002 [US1] `app/templates/partials/builder.html`: render the stored part's name as a link with class `node-name`; check `tests/test_ui_builder_assets.py` and the contrast test stay green.
- [x] T003 Suite: 1076 passed. Every FR maps to a test (links on bike and part screens, chip outside the link, drag and Add to… unchanged, target breadcrumb). FR-004 (keyboard/assistive) relies on a native anchor, asserted structurally. Not checked in a browser.
