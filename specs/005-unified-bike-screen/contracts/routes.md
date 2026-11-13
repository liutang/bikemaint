# Routes: Unified Bike Screen and Simpler Parts

- `GET /bikes/new`, `GET /bikes/{id}/edit`, `POST /bikes`, `POST /bikes/{id}`: fields `year`, `make`, `model`, `category` (road|gravel|mountain|hybrid|e-bike|other), `manual_baseline_mileage`. Legacy bike edit: blank year/make/model keeps the name.
- `GET /bikes/{id}` and `GET /components/{id}`: the unified screen (breadcrumb, actions, tree, storage, palette). 404 if missing.
- `GET /bikes/{id}/build`: 303 to `/bikes/{id}`.
- `POST /builder/add` fields `root`, `component_type` (offered kinds), `target`, optional `before_component_id`.
- `POST /builder/move` fields `root`, `component_id`, `target`, optional `before_component_id`.
- `POST /builder/delete` fields `root`, `component_id`, optional `confirmed=true`, optional `keep_history` (checkbox). Without `confirmed` it always returns the confirmation (what will happen, an unchecked "Keep install history" checkbox, Delete and Cancel); with `confirmed=true` it deletes the part, and deletes the part's install history unless `keep_history` is present (specs/030-install-history-cleanup).
  `root` and `target` are `bike:ID` / `component:ID` (`storage` also valid for move targets). HTMX → the `#builder` fragment (200, or 422 with a `role="alert"` reason, or a confirmation panel); otherwise 303 back to the root's screen. Deleting the root part: `HX-Redirect` / 303 to the level above.
- Removed: `GET /bikes/{id}/build` page, `POST /bikes/{id}/build/add|move`, the separate Move form on part pages (the `POST /components/{id}/move` route stays for compatibility).
