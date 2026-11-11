# BikeMaint

A single-user, self-hosted bike maintenance tracker. Sign in with Strava, record your bikes and
the components on them (nested arbitrarily deep: bike → wheel → rim → tire), let ride mileage sync
automatically from Strava, log maintenance, and get notified — in the app and via an outbound
webhook (e.g. a Discord channel) — before scheduled maintenance is due.

Built with FastAPI, HTMX, Jinja2 and SQLite (no ORM, no frontend build step). Design documents
live in [`specs/001-bike-maintenance-tracker/`](specs/001-bike-maintenance-tracker/).

## Setup

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in the values below
```

Register a Strava API application at <https://www.strava.com/settings/api>, setting its
Authorization Callback Domain to the host you will run this on (e.g. `localhost`).

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `STRAVA_CLIENT_ID` | yes | Strava API application client id |
| `STRAVA_CLIENT_SECRET` | yes | Strava API application client secret |
| `SESSION_SECRET_KEY` | yes | Random secret used to sign the session cookie |
| `DATABASE_PATH` | yes | Path to the SQLite database file (created and migrated on startup) |
| `STRAVA_SYNC_INTERVAL_MINUTES` | no | How often to poll Strava for new rides (default `30`) |
| `NOTIFICATION_CHECK_INTERVAL_MINUTES` | no | How often to check for due-soon maintenance (default `60`) |
| `LOG_LEVEL` | no | Python log level (default `INFO`) |

The outbound webhook URL and the notification lead time are configured in the app, under
**Settings**, not through environment variables.

## Run

Export the variables above (for example `set -a; source .env; set +a`), then:

```bash
uvicorn app.main:app --reload
```

The session cookie is marked `Secure`, so browsers only send it over HTTPS — run behind a TLS
terminating proxy, or use `localhost` (browsers treat it as a secure context).

## Test

```bash
pytest
```

## UI and styling

The interface is server-rendered Jinja2 with HTMX for in-place updates, styled by one hand-written
stylesheet, `app/static/styles.css`, with no framework and no build step (constitution v1.3.0).

- **Theme:** colors, spacing, radii and type sizes are CSS custom properties at the top of the file.
  Light is the default; the dark values live in the `prefers-color-scheme: dark` block, so the app
  follows the operating system automatically. Change a token there to re-theme everything.
- **Contrast:** `tests/test_ui_contrast.py` reads those tokens and fails if a text/background pair
  drops below WCAG AA in either theme, so check it after changing colors.
- **Reusable markup:** `app/templates/partials/` holds the icon, form-field and status-badge macros.
  The class vocabulary is documented in `specs/002-modern-ui/contracts/ui-contract.md`.
- **No JavaScript to maintain:** the component tree uses native `<details>`, and HTMX is only used
  for row updates and inline confirmations. Every flow still works with plain navigation.

## Layout

| Path | Responsibility |
|---|---|
| `app/routers/` | HTTP route handlers only |
| `app/services/` | Business logic (callable without FastAPI) |
| `app/models/` | Request schemas and row dataclasses |
| `app/db/` | Connection, migrations and parameterized queries |
| `app/templates/`, `app/static/` | Jinja2 templates and static assets |
| `tests/` | Mirrors `app/` one-to-one |
