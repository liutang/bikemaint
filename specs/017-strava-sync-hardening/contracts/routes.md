# Interface Contract: Strava Sync Hardening Routes

Extends [`001/contracts/routes.md`](../../001-bike-maintenance-tracker/contracts/routes.md). All routes require a signed-in session; unauthenticated requests are handled by the existing `require_account` dependency.

## Changed

| Method & Path | Change |
|---|---|
| `GET /login` (OAuth redirect to Strava) | Requested scope is `profile:read_all,activity:read_all` (was `activity:read_all`). The redirect URL carries `scope=profile%3Aread_all%2Cactivity%3Aread_all`. |
| `GET /bikes/{bike_id}/strava-pairing` | Gear options show the Strava name (id only if no name). Three non-form states: **profile access missing** (explanation + `POST /logout` "Sign out and reconnect"), **no unpaired gear** (explanation + link to Strava gear settings), and the unchanged stale-token message. |

## New

| Method & Path | Success | Errors |
|---|---|---|
| `POST /bikes/{bike_id}/strava-reimport` | `303` to `/bikes/{bike_id}` after the full backfill ran | `404 Bike not found`; `409 Bike is not paired with Strava`; `502` with "Strava did not answer in time, so nothing was re-imported. Please try again in a moment." when Strava times out or fails |
| `POST /bikes/{bike_id}/strava-unpair` | `303` to `/bikes/{bike_id}`; gear id and paired-at cleared, rides kept | `404 Bike not found`; `409 Bike is not paired with Strava` |

## UI

`app/templates/partials/part_actions.html` shows the two buttons ("Re-import Strava history", "Unpair from Strava") only when the bike has a `strava_gear_id`.

## Outbound (Strava)

| Call | Contract |
|---|---|
| `GET /athlete` | `bikes` key absent or null → `StravaGearAccessError`; `[]` → empty list |
| `GET /athlete/activities?page=N&per_page=200[&after=T]` | Repeated with `page` 1, 2, … until a response has fewer than 200 items; read timeout 60 s |
