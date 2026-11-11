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
- **Cockpit look (feature 003):** charcoal dark theme and cool-grey light theme, amber accent
  `#FFA800` (`--primary`; light-mode links and focus use the darker `--link`). Space Grotesk and
  Inter are vendored in `app/static/fonts/`, so pages make no third-party requests.
- **Maintenance due page:** "What needs attention" shows urgent tasks as ring cards (at most six
  tiles; extras collapse into "+N more tasks", and `/maintenance/due?all=1` shows all). Mark done
  swaps the whole `#attention` board in place. Contract: `specs/003-cockpit-theme/contracts/ui-contract.md`.
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

## Bikes, parts and the unified screen

- **Add a bike** by typing Year, Make and Model and choosing a Category (road, gravel, mountain,
  hybrid, e-bike, other). The name is "Year Make Model" (a numeric suffix for duplicates). Bikes
  from before keep their single name; edit one and leave the three blank to keep it.
- **One screen per bike and per part.** Open a bike from the garage and you get breadcrumbs
  (Garage > bike > part), the actions (Edit, Maintenance history, Add schedule, Adjust mileage,
  Pair with Strava for bikes), the part tree, storage, and a palette of new parts, all on one page.
  Click a part to drill in: same layout scoped to that part, with its own actions, a Garage button
  (move to storage) and a Trash button (delete, with an in-place confirmation when needed).
- **Part categories** are deliberately few: frame, fork, wheel, tire, brake, drivetrain, chain,
  pedal, saddle, handlebar, other. Older finer kinds (rim, hub, spoke...) still work on existing
  parts but are never offered. Placement rules live in `app/models/component_kinds.py` and are
  enforced on the server for every action.
- **Drag and drop** (`app/static/builder.js`, plain JavaScript, no library) mounts, moves,
  re-orders and unmounts parts; every drag has a keyboard/no-JS form equivalent ("Move to…",
  "Add to…", up/down, Garage, Trash). Actions post to `/builder/add|move|delete` with a `root`.

## Running in Docker

```bash
docker build -t bikemaint:local .
docker run -d --name bikemaint -p 8000:8000 -v bikemaint-data:/data \
  -e SESSION_SECRET_KEY=change-me -e STRAVA_CLIENT_ID=... -e STRAVA_CLIENT_SECRET=... bikemaint:local
```

The SQLite database lives in the `bikemaint-data` volume (`/data/bikemaint.sqlite3`).
