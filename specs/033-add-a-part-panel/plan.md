# Implementation Plan: 033 "Add a part" Panel With Storage

Template and CSS only; no route, service, data or script change. The drag script already finds drop targets by `.drop-target` and `data-ref`, and `closest()` finds an enclosing element, so a `<details>` that is the storage drop target works for drops on its summary or list, collapsed or open.

- `app/templates/partials/builder.html`: delete the separate storage `<section>`; the palette section is retitled "Add a part"; after the categories, one more `<details class="palette-category storage-drop drop-target" data-ref="storage" data-accepts="">` with `<summary>In storage (N)</summary>` and the same list, rows and empty message as before.
- `app/static/styles.css`: a dashed highlight for `.storage-drop` while dragging reuses the existing `.is-valid` rules; no new tokens.
- Tests: `tests/routers/test_builder.py` (panel markup, order, collapsed, count, rows, empty message, drop-target attributes), `tests/test_ui_builder_assets.py` (the script still reads only attributes the markup emits), existing storage helper updated.

Constitution (v1.3.0): I Simplicity (native `<details>`, no script), II Modular (template only), III TDD, IV Security (unchanged routes), V n/a. All pass.
