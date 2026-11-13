# Tasks: 028 Storage Part Links

- [ ] T001 [US1] Tests first in `tests/routers/test_builder.py`: on a bike screen and on a part screen each stored part's name is `<a href="/components/{id}">name</a>` inside the In storage card, the kind chip is outside the link, the list item is still `draggable="true"` with `data-source="storage"` and its "Add to…" form is unchanged; opening the link shows the breadcrumb Garage › Storage › the part (`Storage` links to `/components`). Watch them fail.
- [ ] T002 [US1] `app/templates/partials/builder.html`: render the stored part's name as a link with class `node-name`; check `tests/test_ui_builder_assets.py` and the contrast test stay green.
- [ ] T003 Run the suite; add a line to `CLAUDE.md` if useful; PR; merge; confirm the publish job.
