# Interface Contract: 023 Settings Routes

Extends `specs/001-bike-maintenance-tracker/contracts/routes.md` (Settings). All routes require sign-in.

| Method & Path | Form fields | Success | Errors |
|---|---|---|---|
| `POST /settings/strava/sync` | `sync_enabled` (checkbox, present = on), `interval_hours` (0–168), `interval_minutes` (0–59) | 303 to `/settings` | 422 settings page with a message beside the field: total under 5 minutes, over 7 days, not a whole number, minutes over 59 |
| `POST /settings/timezone` | `timezone` (IANA name) | 303 to `/settings` | 422 settings page with a message beside `timezone` when unknown or empty |

## Settings page

- **Strava connection** panel: connection status as before; a form with the "Sync automatically" switch, Hours and Minutes, and Save; a line "Every N h M min" or "Automatic sync is off".
- **Time zone** section: a `<select>` of about 30 entries such as `(GMT-5) America/New York (EST)` (standard offset, prominent city, abbreviation), ordered by offset, current choice selected (an off-list saved zone is added as the current choice), Save. The submitted value is still an IANA zone name (`timezone`).
- "Connected since" is shown in the saved zone.

## Display

A Jinja filter `local_time` renders a stored UTC string as `YYYY-MM-DD HH:MM ABBR` in the saved zone. Used for Strava rides on the ride log, completed-task times on maintenance history and connected-since. Typed values are rendered as stored.

## Scheduler

`strava_sync` job: absent when automatic sync is off; otherwise one interval job at the saved (or default) minutes. Replaced in place on save.
