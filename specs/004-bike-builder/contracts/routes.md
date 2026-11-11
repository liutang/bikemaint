# Route contract: Bike Catalog and Interactive Builder

All routes require sign-in (303 to `/login` otherwise), like the rest of the app.

## M1: bikes
- `GET /bikes/new`, `GET /bikes/{id}/edit`: form with `<select name="catalog_id">` (optgroups by category). Legacy bikes on edit get `value="__keep__"` ("Keep current: NAME").
- `POST /bikes` fields: `catalog_id` (required, allow-listed), `manual_baseline_mileage`. No `name`/`bike_type` accepted. Invalid/unknown → 422 with field error, nothing saved. Success → 303 `/bikes/{id}`.
- `POST /bikes/{id}` same fields; `__keep__` allowed only for a legacy bike.

## M2: placement rules (existing routes)
- `POST /components`, `POST /components/{id}` (type change), `POST /components/{id}/move`: unchanged fields; invalid placement → 422 with message naming allowed parents; the component forms offer only types valid for the chosen parent.

## M3: builder
- `GET /bikes/{bike_id}/build`: split-screen page (404 if no bike).
- `POST /bikes/{bike_id}/build/add` fields: `component_type` (known type), `target` (`bike:ID` or `component:ID` on this bike), optional `before_component_id`. Creates a part with the type's default name.
- `POST /bikes/{bike_id}/build/move` fields: `component_id` (in storage or on this bike), `target` (`storage`, `bike:ID` or `component:ID` on this bike), optional `before_component_id`. Mounts, moves (with sub-tree), unmounts, or re-orders (target = current parent). Moving onto the current parent never touches installation periods.
- `POST /components/{id}/move` additionally accepts `target` (the Move-to select) next to the legacy `parent_bike_id`/`parent_component_id` fields.
- No extra route is needed for valid targets: each drop target carries a server-computed `data-accepts` list, and each Move-to / Add-to select lists only valid targets.

Responses: with `HX-Request: true` the whole `#builder` fragment (200, or 422 with a `role="alert"` reason); otherwise 303 back to the builder (or the full page with 422). Malformed ids, unknown types, targets on another bike and rule violations are all 422 and change nothing.
