# Implementation Plan: Feedback Round 2

Three milestones, each a PR merged and deployed on completion. Python 3.13, FastAPI, Jinja2, HTMX, vanilla static JS (builder.js; a tiny localtime.js in M2). SQLite migrations `0008` (M2: maintenance entry `kind`, `performed_time`) and `0009` (M3: ride table rebuilt to allow manual rides). Constitution v1.3.0: PASS (no new framework; logic in services; validation at the boundary; TDD).

## M1 (fixes and storage)
`component_service.delete_component` re-parents direct children to storage before soft-deleting; `bike_service.delete_bike` likewise. `component_kinds`: rotor offered (parents wheel, hub). `builder_service.build_view` palette filtered to kinds with targets; `add_part` accepts a storage target; `builder.js` allows palette→storage. `components/form.html` loses parent ID fields. Garage page lists bikes only; Storage page gets breadcrumbs and an add button; nav gets Storage. `DueItem.bike_name`.

## M2 (history and polish)
`maintenance_log_entry.kind` (`service`|`event`) and `performed_time`; events written by `component_service` on create/move/delete; `has_entries_for_*` count only `service`. History templates show date+time (`<time data-local>` converted by `localtime.js`). `schedule_service.complete_schedule` ignores a repeat within 5 seconds; the board shows a success notice and highlights the completed item; forms use `hx-disabled-elt`. New icon macros per part kind and a redrawn bike.

## M3 (ride log)
Migration rebuilds `ride_activity` (nullable `strava_activity_id`, `source`, `note`, `user_modified`, `deleted_by_user`); upsert skips user-modified rows; recompute queries exclude user-deleted rides and recompute every bike and part with history on the affected bikes. `ride_service` (CRUD, running totals), router `/bikes/{id}/rides…`, read-only `/components/{id}/rides`; Rides button replaces Adjust mileage.
