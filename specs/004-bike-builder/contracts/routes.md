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
- `POST /bikes/{bike_id}/build/add` fields: `component_type`, exactly one of `parent_bike_id`/`parent_component_id`, optional `before_component_id`. Creates a component with the type's default name. Returns the `#builder` fragment (200) or the fragment with an alert (422).
- `POST /components/{id}/move` gains optional `before_component_id` (re-order / insert before) and `return=builder` (returns the builder fragment for `bike_id` form field instead of redirecting).
- No extra route is needed for valid targets: each drop target carries a server-computed `data-accepts` list of component types, and each Move-to select lists only valid targets.

Responses for HTMX requests (`HX-Request: true`) are fragments; otherwise 303 back to `/bikes/{id}/build`.
