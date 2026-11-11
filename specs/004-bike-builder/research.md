# Research: Bike Catalog and Interactive Builder

## 1. Drag and drop without a framework
**Decision**: Native HTML5 drag and drop in one hand-written `app/static/builder.js` (about 150 lines). Draggable items carry `data-kind` ("component" | "palette"), `data-id`/`data-type`; drop targets carry `data-parent-kind` and `data-parent-id` and a server-computed `data-accepts` list of component types. On dragstart the script marks valid targets (`.is-valid`) and dims the rest; on drop it POSTs to the same endpoint the Move-to form uses (via `htmx.ajax` targeting `#builder`, falling back to `fetch`), and the server returns the re-rendered builder fragment or a 422 fragment with the message.
**Why not a library (SortableJS etc.)**: avoids a new dependency and a constitution question; native DnD is enough for tree targets. Touch devices lack native DnD, hence the mandatory Move-to controls.
**Why not HTMX alone**: HTMX has no drag events; the script only turns drops into requests.

## 2. Compatibility catalog
**Decision**: `COMPONENT_KINDS: dict[type, Kind(label, allowed_parents, multi)]`, where `allowed_parents` is a set of `"bike"` and component types; storage is always allowed. `bolt` and `other` mount anywhere; `pad` on `brake` and the bike. Rules (simplified, documented in data-model.md):
frame, fork, wheel, drivetrain, brake, handlebar, stem, seatpost, saddle → bike; hub, rim, spoke → wheel; tire → rim; cassette, rotor → hub; crankset, chain, derailleur → bike or drivetrain; pedal → crankset; shifter → bike or handlebar; pad → brake or bike.
Existing types keep working: `wheel`, `hub`, `rim`, `tire`, `spoke`, `bolt`, `pad`, `drivetrain`, `chain`, `brake`, `frame`, `other` stay valid.
**Enforcement point**: `component_service._validate_placement` runs from create, update (type change) and move, before the existing single-instance check; messages come from the catalog ("A pedal can be mounted on a crankset, not on a wheel.").
**Alternative rejected**: a slot/cardinality rules engine (already rejected in feature 001).

## 3. Bike catalog
**Decision**: About 60 entries as frozen dataclasses (`id` slug like `trek-domane`, make, model, category in road/gravel/mountain/hybrid/e-bike). The form uses `<optgroup>` by category with make-model options; the service resolves the id, generates `name = "Make Model"` and adds " (2)", " (3)" for duplicates among active bikes. `bike.catalog_id` stores the id (NULL for legacy bikes). Edit shows "Keep current: <name>" as the first option for legacy bikes.
**Alternative rejected**: free-text with autocomplete (the rider explicitly does not want free text).

## 4. Ordering
**Decision**: `component.position INTEGER NOT NULL DEFAULT 0`; all sibling reads `ORDER BY position, id`; new and moved components get `max(position)+1` under their new parent; reorder takes `before_component_id` (or none = end), renumbers siblings 0..n in one transaction. Reads on the bike detail page and the builder use the same ordering.

## 5. Builder fragment
**Decision**: `GET /bikes/{id}/build` renders the full page; every builder action returns the `#builder` fragment (both panes) so counts, ordering, available targets and the storage list refresh together. Errors return the fragment with a `role="alert"` message and status 422 (HTMX is configured to swap 422 responses for `#builder` via `hx-on` / script handling).

## 6. Accessibility and no-JS
Each tree node and storage/palette item has a `<form>` with a `<select name="target">` of valid targets and a "Move"/"Add" button (keyboard accessible, works without JS). The script enhances but never replaces these.
