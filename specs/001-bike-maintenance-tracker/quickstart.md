# Quickstart: Bike Maintenance Tracker

Validates the feature end-to-end against the User Story acceptance scenarios in `spec.md`. Assumes the implementation described in `plan.md`, `data-model.md`, and `contracts/` is built.

## Prerequisites

1. Python 3.12+, project dependencies installed (`pip install -r requirements.txt` or equivalent).
2. A Strava API application registered at https://www.strava.com/settings/api, with:
   - Authorization Callback Domain matching where you'll run this app (e.g. `localhost`).
   - The app owner's Strava account carrying an active Strava subscription (required for Standard-tier API access as of 2026 — see research.md §1).
3. Environment variables set (e.g. in `.env`, loaded at startup — never committed):
   - `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`
   - `SESSION_SECRET_KEY` (random, used to sign the session cookie)
   - `DATABASE_PATH` (defaults to a local `.sqlite3` file)
   - `NOTIFICATION_WEBHOOK_URL` is **not** an env var — it's configured in-app via `/settings/webhook` (FR-023), per-account.
4. Run the app: `uvicorn app.main:app --reload`.

## Scenario 1 — Garage inventory (User Story 1, SC-002)

1. Sign in via `/login` → Strava OAuth.
2. `POST /bikes` to add "Gravel Bike". Confirm it appears at `GET /` with 0 mileage.
3. `POST /components` three times to build `Gravel Bike → Wheel → Rim → Tire`, nesting each under the previous.
4. `GET /bikes/{id}` and confirm the tree renders in the correct nested order.
5. Move the tire to storage (`POST /components/{tire_id}/move` with no parent), confirm it now appears in `GET /components` and no longer under the bike.
6. Move the tire onto a second bike's rim; confirm its mileage/history (initially empty) travels with it.

**Pass condition**: tree nesting always matches the moves made, and the whole flow (steps 2–4) takes well under 2 minutes by hand.

## Scenario 2 — Strava mileage sync (User Story 2)

1. `GET /bikes/{bike_id}/strava-pairing`, select a Strava gear entry, submit.
2. Confirm the historical backfill populates `total_mileage` on the bike and its currently-installed components from that gear's full ride history (FR-022).
3. Record a new ride in Strava against that gear.
4. Either wait for the scheduled sync job or call `POST /sync/strava` directly; confirm the ride's distance is added to the bike and every component installed at the time of the ride, but not to a component installed only afterward (Acceptance Scenario US2-2).
5. `POST /bikes/{bike_id}/mileage/adjust` with a negative `delta_miles` and a `reason`; confirm the total reflects it and the adjustment is visible in an audit view.
6. Revoke the app's access from Strava's settings, trigger a sync, and confirm `account.strava_connection_stale` flips true and the UI surfaces a reconnect prompt without deleting existing data (Acceptance Scenario US2-3).

## Scenario 3 — Maintenance log (User Story 3)

1. On a component, `POST .../maintenance` with a description and date.
2. Confirm it appears in `GET .../maintenance` with the mileage captured at that time.
3. Move the component to a different bike; confirm the log entry is still listed under the component, not the original bike.
4. Edit, then delete, a log entry; confirm the history list updates accordingly.

## Scenario 4 — Scheduled maintenance & notifications (User Story 4, SC-004, SC-005)

1. `POST .../schedules` on a component with `interval_miles=1500`.
2. With enough synced ride history, `GET /maintenance/due` and confirm a projected due date appears, combining remaining mileage with recent pace (Acceptance Scenario US4-1).
3. Set `notification_lead_time_days` low enough (via `/settings/notifications`) that the item falls inside the window; run the notification check job and confirm exactly one `notification` row is created and the configured webhook receives the POST described in `contracts/webhook-payload.md`. Run the check again and confirm no duplicate is sent for the same cycle.
4. `POST /schedules/{id}/complete`; confirm a maintenance log entry is created (Scenario 3 view), the schedule's due projection resets, and its `cycle_number` increments.
5. Move the component to a different bike (or into storage) and confirm the projection recalculates from the component's own mileage/pace, not the old bike's (Acceptance Scenario US4-4).
6. Create a schedule on a brand-new component with no ride history yet; confirm `GET /maintenance/due` marks its projection low-confidence / time-only rather than showing a misleading mileage-based date (Acceptance Scenario US4-5).

## Cross-cutting checks

- Every route above returns `401`/redirects to `/login` when hit without a session (FR-021).
- Attempting to install a second single-instance component (e.g. a second tire) onto a rim that already has one returns a validation error, not a silent duplicate (FR-024, Edge Case).
- Deleting a bike or component with maintenance history or an active schedule requires confirmation before it proceeds (FR-020).
