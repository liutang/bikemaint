# Interface Contract: HTTP Routes

This app is server-rendered (FastAPI + Jinja2 + HTMX, per the constitution's fixed stack) — there is no separate JSON API for a frontend to consume. The "contract" is therefore the set of HTTP routes: full-page GET routes render a complete Jinja2 page, and mutation routes accept form-encoded POST bodies and return an HTMX partial fragment (`HX-Request` requests) or a redirect (full-page form fallback). All routes below require an authenticated session (FR-021) except the auth routes themselves and the Strava webhook-free callback.

Route handlers live only in `app/routers/`; they call into `app/services/` for all business logic per Constitution Principle II.

## Auth

| Method & Path | Purpose |
|---|---|
| `GET /login` | Renders the "Sign in with Strava" page. |
| `GET /auth/strava/callback` | Strava OAuth2 redirect target; exchanges `code` for tokens, upserts the `account` row, establishes the session cookie, redirects to `/`. |
| `POST /logout` | Clears the session cookie. |

## Bikes (User Story 1, 2)

| Method & Path | Purpose |
|---|---|
| `GET /` | Garage overview: all bikes + top-level in-storage components. |
| `GET /bikes/{bike_id}` | Bike detail: full nested component tree, mileage, upcoming schedules. |
| `GET /bikes/new` | New-bike form fragment/page. |
| `POST /bikes` | Create a bike (`name`, `bike_type`, `manual_baseline_mileage`). Returns updated garage list fragment. |
| `GET /bikes/{bike_id}/edit` | Edit-bike form fragment. |
| `POST /bikes/{bike_id}` | Update a bike. |
| `POST /bikes/{bike_id}/delete` | Soft-delete a bike; if it has installed components, maintenance history, or an active schedule, first returns a confirmation fragment (FR-020) unless `confirmed=true` is included. |
| `GET /bikes/{bike_id}/strava-pairing` | Form to pick one of the account's unpaired Strava gear entries. |
| `POST /bikes/{bike_id}/strava-pairing` | Pairs the bike to a `strava_gear_id`; triggers the one-time historical backfill sync (FR-022) as a background task and returns a "syncing" status fragment. |

> **See also**: `specs/017-strava-sync-hardening/contracts/routes.md` for `POST /bikes/{bike_id}/strava-reimport`, `POST /bikes/{bike_id}/strava-unpair`, the pairing screen states, and the `profile:read_all` sign-in scope.

## Components (User Story 1)

| Method & Path | Purpose |
|---|---|
| `GET /components` | In-storage components list. |
| `GET /components/new?parent_bike_id=&parent_component_id=` | New-component form, pre-scoped to a parent (or storage if neither given). |
| `POST /components` | Create a component (`name`, `component_type`, optional parent, `manual_baseline_mileage`). Validates the single-instance/multi-instance rule (FR-024); returns `422` + inline error fragment on violation. |
| `GET /components/{component_id}` | Component detail: sub-tree, mileage, maintenance history, schedules. |
| `GET /components/{component_id}/edit` | Edit-component form fragment. |
| `POST /components/{component_id}` | Update a component's own fields (not its parent — see move route). |
| `POST /components/{component_id}/move` | Move a component (and its sub-tree) to a new `parent_bike_id`, `parent_component_id`, or into storage (both null). Closes the current `component_installation_period` and opens a new one (or none, for storage). Validates FR-024 at the destination. |
| `POST /components/{component_id}/delete` | Soft-delete (recursively for sub-tree); confirmation-gated like bikes (FR-020). |

## Mileage (User Story 2)

| Method & Path | Purpose |
|---|---|
| `POST /sync/strava` | Manually trigger an incremental sync outside the scheduled interval (useful for demos/tests); same code path the background job uses. |
| `GET /bikes/{bike_id}/mileage/adjust` | Manual mileage adjustment form fragment (also reachable for a component via `/components/{id}/mileage/adjust`). |
| `POST /bikes/{bike_id}/mileage/adjust` / `POST /components/{component_id}/mileage/adjust` | Records a `mileage_adjustment` row (`delta_miles`, `reason`) and recomputes `total_mileage` (FR-009). |

## Maintenance log (User Story 3)

| Method & Path | Purpose |
|---|---|
| `GET /bikes/{bike_id}/maintenance` / `GET /components/{component_id}/maintenance` | Chronological maintenance history (FR-011). |
| `GET /bikes/{bike_id}/maintenance/new` / `GET /components/{component_id}/maintenance/new` | New log-entry form fragment. |
| `POST /bikes/{bike_id}/maintenance` / `POST /components/{component_id}/maintenance` | Create a log entry (`description`, `performed_at`; `mileage_at_service` defaults to current total but is editable). |
| `GET /maintenance/{entry_id}/edit` | Edit form fragment. |
| `POST /maintenance/{entry_id}` | Update a log entry; if it is tied to a schedule (`schedule_id`), does not change the schedule's cycle. |
| `POST /maintenance/{entry_id}/delete` | Delete a log entry; triggers schedule due-date recompute if `schedule_id` was set (FR-012, FR-017). |

## Maintenance schedules & the due-soon dashboard (User Story 4)

| Method & Path | Purpose |
|---|---|
| `GET /maintenance/due` | Single dashboard of all upcoming/overdue items across the garage (FR-019, SC-005), each row showing projected due date/mileage and a confidence flag (FR-018). |
| `GET /bikes/{bike_id}/schedules/new` / `GET /components/{component_id}/schedules/new` | New-schedule form fragment. |
| `POST /bikes/{bike_id}/schedules` / `POST /components/{component_id}/schedules` | Create a schedule (`name`, `interval_miles` and/or `interval_days`). |
| `GET /schedules/{schedule_id}/edit` | Edit-schedule form fragment. |
| `POST /schedules/{schedule_id}` | Update a schedule's intervals or active flag. |
| `POST /schedules/{schedule_id}/complete` | Check off a schedule: creates a `maintenance_log_entry` (FR-016), bumps `cycle_number`, resets `baseline_mileage`/`baseline_date`, returns the updated due-soon row fragment. |
| `POST /schedules/{schedule_id}/delete` | Delete a schedule (history of past completions in `maintenance_log_entry` is preserved; their `schedule_id` reference is kept for traceability). |
| `POST /notifications/{notification_id}/acknowledge` | Dismisses an in-app due-soon alert (sets `acknowledged_at`); redirects back to `/maintenance/due`. Added during implementation: FR-015's in-app alert needs a way to be dismissed. |

## Account settings

| Method & Path | Purpose |
|---|---|
| `GET /settings` | Shows Strava connection status (incl. stale-connection flag), webhook URL, notification lead time. |
| `POST /settings/webhook` | Set/edit/remove `notification_webhook_url` (FR-023). |
| `POST /settings/notifications` | Set `notification_lead_time_days`. |
| `POST /settings/strava/reconnect` | Re-initiates the OAuth flow when the connection is stale/expired. |

## Background jobs (not HTTP routes, listed for completeness)

- **Strava sync job** — calls the same service function as `POST /sync/strava`, on an interval (research.md §7).
- **Due-date/notification check job** — recomputes every active schedule's projection, inserts a `notification` row (subject to the `(schedule_id, cycle_number)` uniqueness) when a projection newly enters the lead-time window, and POSTs the outbound webhook payload (see `webhook-payload.md`).
