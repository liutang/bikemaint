# Implementation Plan: Bike Maintenance Tracker

**Branch**: `001-bike-maintenance-tracker` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-bike-maintenance-tracker/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A single-user, self-hosted web app for tracking bikes, their arbitrarily-nested components, maintenance history, and predictive maintenance schedules. Riders sign in with Strava (no separate password); the app periodically polls Strava's activity API to attribute ride mileage to the correct bike and its currently-installed components (including nested ones), lets the user log completed maintenance, and projects due dates for scheduled maintenance from recent riding pace, notifying the user in-app and via a configurable outbound webhook when something is due soon. Built on the project's fixed stack — FastAPI + HTMX + Jinja2 + SQLite — as a single modular application (routers/services/models/db/templates), with no ORM, using raw parameterized SQL and an in-process APScheduler for the periodic Strava sync and due-date/notification checks.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Jinja2, Starlette `SessionMiddleware` (cookie session auth), `httpx` (Strava API client, outbound webhook delivery), APScheduler (in-process background sync/notification jobs), HTMX (loaded as a static asset, no build pipeline)

**Storage**: SQLite, accessed via the standard library `sqlite3` module with hand-written parameterized query functions (no ORM); schema managed via sequential `.sql` migration files tracked in a `schema_version` table

**Testing**: `pytest`, Starlette `TestClient` for router tests, direct calls for service-layer unit tests, `respx`/`httpx.MockTransport` to stub Strava HTTP calls

**Target Platform**: Linux server, single long-running process (self-hosted, single user)

**Project Type**: Web application — single project (per the constitution's fixed layout; HTMX + server-rendered Jinja2 means there is no separate frontend project)

**Performance Goals**: Single-user scale only; page loads well under 200ms p95 against local SQLite; Strava sync/notification jobs run on a 30–60 minute cadence, not user-request-latency-sensitive

**Constraints**: Must stay within Strava's default rate limits (200 req/15 min, 2,000 req/day) — satisfied trivially by low-frequency polling for one user (research.md §1); outbound webhook delivery must not block notification recording on failure (research.md §6)

**Scale/Scope**: One rider, on the order of a handful of bikes and dozens of components, years of ride history (thousands of `ride_activity` rows) — no multi-user or concurrency design needed (spec Assumptions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Status | Notes |
|---|---|---|
| I. Simplicity Over Cleverness | PASS | No ORM, no task queue, no webhook-subscription infra — polling + APScheduler chosen explicitly over more complex alternatives (research.md §1, §6, §7, §8). Component nesting validated via a small hardcoded type list rather than a generic rules engine (research.md §3). |
| II. Modular, Non-Monolithic Design | PASS | Routes (`app/routers`) contain no business logic; all bike/component/mileage/schedule/notification logic lives in `app/services`, callable without HTTP, per contracts/routes.md. |
| III. TDD (NON-NEGOTIABLE) | PASS (process gate, enforced at implementation) | `tasks.md` (next phase) must sequence a failing test before each behavior; not evaluated further at plan time. |
| IV. Security by Default | PASS | Strava OAuth server-side only, tokens never sent to the browser; all input validated via Pydantic request models at router boundaries; all SQL parameterized (data-model.md); every route requires a session except `/login` and the OAuth callback (FR-021). |
| V. Human-Readable Observability | PASS | Webhook delivery failures and sync errors logged with identifiers (schedule id, activity id) per research.md §6; stale-connection state surfaced instead of silent failure. |
| Technology Stack (fixed) | PASS | FastAPI + HTMX + Jinja2 + SQLite only; added libraries (`httpx`, APScheduler) are plumbing, not a second templating engine/frontend framework/alternate database, so no amendment is needed. |
| Project Structure (fixed) | PASS | See below — matches `app/routers`, `app/services`, `app/models`, `app/db`, `app/templates`, `app/static`, `tests/` mirroring `app/`. |

No violations identified; **Complexity Tracking** table below is empty.

*Post-Phase-1 re-check*: data-model.md and contracts/ were designed within the same constraints (adjacency-list SQLite tables, no new libraries beyond those listed above, routers/services split preserved in contracts/routes.md). Constitution Check still PASSES with no changes.

## Project Structure

### Documentation (this feature)

```text
specs/001-bike-maintenance-tracker/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── routes.md
│   └── webhook-payload.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── main.py                  # FastAPI app factory, startup event wiring APScheduler jobs
├── routers/
│   ├── auth.py               # /login, /auth/strava/callback, /logout
│   ├── bikes.py               # bikes + strava-pairing routes
│   ├── components.py          # components + move routes
│   ├── mileage.py              # /sync/strava, mileage adjustment routes
│   ├── maintenance.py          # maintenance log routes
│   ├── schedules.py            # schedules, /maintenance/due
│   └── settings.py             # account settings routes
├── services/
│   ├── strava_client.py        # OAuth token exchange/refresh, activity/gear API calls (httpx)
│   ├── sync_service.py         # incremental + backfill sync, mileage attribution
│   ├── bike_service.py
│   ├── component_service.py    # tree operations, move, nesting validation (FR-024)
│   ├── maintenance_service.py  # log entries
│   ├── schedule_service.py     # due-date projection (research.md §4), completion/cycle logic
│   ├── notification_service.py # dedup + webhook delivery (research.md §5, §6)
│   └── scheduler.py            # APScheduler job definitions/registration
├── models/
│   ├── requests.py             # Pydantic request schemas per form
│   ├── responses.py            # Pydantic view models passed to templates
│   └── rows.py                 # typed row/table dataclasses returned by app/db
├── db/
│   ├── connection.py            # sqlite3 connection helper, schema_version bootstrap
│   ├── migrations/               # 0001_initial.sql, 0002_...sql, ...
│   ├── bikes.py                  # parameterized query functions
│   ├── components.py
│   ├── mileage.py
│   ├── maintenance.py
│   ├── schedules.py
│   └── notifications.py
├── templates/
│   ├── layout.html
│   ├── bikes/ ... components/ ... maintenance/ ... schedules/ ... settings/
│   └── partials/                 # HTMX fragment templates reused across routes
└── static/
    ├── htmx.min.js
    └── styles.css

tests/
├── routers/       # mirrors app/routers/
├── services/      # mirrors app/services/
└── db/            # mirrors app/db/
```

**Structure Decision**: Single-project web application per the constitution's fixed layout (no `backend/`/`frontend/` split — HTMX + Jinja2 is server-rendered from the same FastAPI app). `app/services/scheduler.py` and `app/services/strava_client.py` are new modules within the existing `app/services/` responsibility (business logic / external integration), not new top-level directories, so no constitution amendment is triggered.

## Complexity Tracking

*No Constitution violations — table intentionally empty.*
