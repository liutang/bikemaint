# Phase 0 Research: Bike Maintenance Tracker

## 1. Strava sync strategy: polling vs. webhooks

- **Decision**: Use a scheduled polling job (APScheduler, in-process, interval-based — default every 30 minutes) that calls Strava's `GET /athlete/activities` for new activities since the last successful sync cursor, rather than subscribing to Strava's Webhook Events API.
- **Rationale**: This is a single-user, self-hosted app (per spec Assumptions). Strava's webhook events require a publicly reachable HTTPS callback endpoint plus a one-time subscription handshake (challenge/response and a verify token) that must survive as long as the app runs. For one rider's data, the operational cost of keeping a public webhook endpoint alive (reverse proxy, TLS, subscription re-validation) outweighs the benefit, and Strava's default rate limit (200 requests/15 min, 2,000/day) is far more than a single-user polling job at a 30-minute cadence will ever consume. Polling also keeps the "periodic sync" requirement (FR-007) simple and testable without mocking inbound webhook deliveries.
- **Alternatives considered**: Strava Webhook Events API (rejected: needs a stable public endpoint and subscription lifecycle management, disproportionate for one user); manual "sync now" button only (rejected: spec explicitly requires sync without manual triggering, FR-007).
- **Note for later**: Strava's Standard API tier now requires the developer's own account to carry an active Strava subscription (phased in through mid-2026), and the API base URL/auth-header format is scheduled to change by June 2027. Since the app owner is also the sole end user, this is an account-level prerequisite (documented in quickstart.md) rather than a code change; the HTTP client should isolate the base URL and auth-header construction in one place so that future change is a one-line update.

## 2. Strava OAuth & gear pairing

- **Decision**: Standard OAuth2 Authorization Code flow against Strava (`/oauth/authorize`, `/oauth/token`), with `activity:read_all` scope. The returned access/refresh tokens are stored server-side in SQLite (never exposed to the browser). A signed, `HttpOnly`, `Secure` session cookie (Starlette `SessionMiddleware` with a server-generated secret from environment config) identifies the logged-in session after the OAuth callback completes; there is no separate password (FR-021).
- **Rationale**: Matches "Sign in with Strava" clarification directly; keeps auth server-side per Constitution Principle IV (Security by Default).
- **Gear pairing**: The app's bikes are managed independently; pairing is a manual, explicit action where the user picks one of their Strava gear entries (`GET /athlete` → `bikes[]`) to associate with an app `Bike` row. Pairing triggers a one-time backfill sync (FR-022) that walks `GET /athlete/activities` (paginated, filtered by `gear_id` client-side, since the endpoint has no server-side gear filter) for the full history before switching to incremental polling.
- **Alternatives considered**: Auto-importing all Strava gear as bikes on connect (rejected explicitly by clarification Q2).

## 3. Component nesting & slot-uniqueness validation

- **Decision**: Model components as a self-referential adjacency list: each `Component` row has a nullable `parent_component_id` and a nullable `parent_bike_id` (exactly one of: no parent/storage, parent bike, or parent component, is set). Tree reads use a recursive CTE (`WITH RECURSIVE`) rooted at a bike or component. Each component carries a `component_type` (a small curated vocabulary, e.g. `frame`, `wheel`, `hub`, `rim`, `tire`, `spoke`, `drivetrain`, `brake`, `other`). A fixed, code-level set of "multi-instance" types (e.g. `spoke`, `bolt`, `pad`, `other`) may have more than one instance under the same parent at once; all other types are single-instance per parent, and the service layer rejects installing a second single-instance component of the same type under a parent that already has one (FR-024).
- **Rationale**: Adjacency list + recursive CTE is the simplest correct representation of arbitrary-depth nesting in SQLite (Constitution Principle I) and needs no extra library. A hardcoded multi-instance type set is far simpler than a general slot/cardinality rules engine, and the spec's edge cases (hub/rim/spokes vs. a second tire on a rim) are fully covered by "is this type inherently multiple, or singular" — no product need justifies a more general constraint system yet.
- **Alternatives considered**: Nested-set/materialized-path model (rejected: harder to update on move operations, no read-pattern in this app needs it); a fully generic parent/child cardinality-rules table (rejected as premature — no requirement calls for user-defined slot types).

## 4. Riding-pace estimation & due-date projection

- **Decision**: For each bike/component, compute a trailing riding pace from the last 90 days of attributed ride activity (distance ÷ elapsed days over that window, or since the item's install/creation date if shorter). Projected due date = today + (remaining miles ÷ daily pace), compared against the time-based interval (if set); the earlier of the two wins, per the spec's Assumptions. If fewer than a configurable minimum of ride-days of data exist (e.g., under 14 days or zero rides in the window), the projection falls back to the time-interval-only estimate, or is flagged low-confidence if no time interval exists either (FR-018).
- **Rationale**: A trailing window keeps projections responsive to changes in riding frequency (spec Assumptions) without needing a more elaborate statistical model; a fixed window and minimum-data threshold are simple, explainable, and testable.
- **Alternatives considered**: All-time average pace (rejected explicitly by spec Assumptions — not responsive to recent behavior); weighted/decaying average (rejected as unnecessary complexity for a single-user tool).

## 5. Due-soon notification de-duplication

- **Decision**: Each `MaintenanceSchedule` has a monotonically incrementing `cycle_number`, bumped every time the schedule is completed (FR-016) and rebuilding its due-date baseline. A `Notification` row is uniquely keyed on `(schedule_id, cycle_number)`. The scheduled check job only inserts a new notification (and fires the in-app alert + webhook POST) if no row exists yet for the current cycle.
- **Rationale**: A cycle counter is a simpler dedup key than a due-date-based key (due dates can shift as pace re-estimates, which would otherwise cause duplicate notifications for the "same" cycle under a date-based key).
- **Alternatives considered**: Deduping by due-date value (rejected: due date can recompute/drift within the same uncompleted cycle, causing duplicate sends).

## 6. Outbound webhook delivery

- **Decision**: Deliver due-soon notifications via a plain HTTP POST (JSON body) to the user-configured webhook URL using `httpx`, with a short timeout (e.g. 5s) and up to 2 retries on failure; delivery failures are logged (Principle V) but never block the in-app notification from being recorded.
- **Rationale**: Single user, low volume (at most a handful of due-soon events at a time) — no queue/broker is justified.
- **Alternatives considered**: Background task queue (Celery/RQ) (rejected: adds infra and a new moving part disproportionate to the load; APScheduler's in-process jobs are sufficient).

## 7. Background scheduling

- **Decision**: Use APScheduler's `BackgroundScheduler`, started from a FastAPI `startup` event, running two interval jobs: (a) Strava activity sync (default every 30 min), (b) maintenance due-date recompute + notification check (default every 60 min). Both intervals are read from environment configuration.
- **Rationale**: In-process scheduling avoids standing up a separate worker process/infra for a single-user app, while still decoupling periodic work from request/response handling.
- **Alternatives considered**: OS-level cron calling a CLI entrypoint (rejected: splits deployment into two moving parts instead of one process; APScheduler in-process is simpler to develop and test against).

## 8. Persistence approach (no ORM)

- **Decision**: Use the standard library `sqlite3` module directly through a small connection-management helper in `app/db/`, with hand-written parameterized SQL functions per entity (matching the Constitution's explicit `app/db/` responsibility: "connection setup, parameterized query functions, and migrations"). Schema evolution is handled via sequential, idempotent `.sql` migration files applied at startup, tracked in a `schema_version` table.
- **Rationale**: Constitution Principle I (Simplicity) and the fixed Technology Stack section do not call for an ORM; the domain's SQL (including recursive CTEs for the component tree) is straightforward enough to write directly, and avoiding an ORM avoids a second abstraction to reason about the same rows through.
- **Alternatives considered**: SQLAlchemy Core/ORM (rejected: extra dependency/abstraction not justified by this domain's needs); Alembic for migrations (rejected: a handful of sequential `.sql` files is sufficient for this project's scope and keeps the tech stack from diversifying without a constitution amendment).

## 9. Testing approach

- **Decision**: `pytest` with FastAPI's `TestClient` (Starlette `TestClient`, built on `httpx`) for router-level tests, direct function calls against `app/services/*` for business-logic unit tests (per Constitution Principle II, services must be callable without HTTP), and a temporary on-disk SQLite file (or `:memory:` where a single connection suffices) per test for `app/db/*` tests. Strava HTTP calls are mocked via `httpx`'s `MockTransport` / `respx` so tests never hit the real API.
- **Rationale**: Matches the Constitution's mandated `tests/` layout mirroring `app/`, and keeps tests fast/offline.
- **Alternatives considered**: Hitting a real Strava sandbox in tests (rejected: no such sandbox exists publicly; would make tests network-dependent and rate-limited).

All NEEDS CLARIFICATION items from the Technical Context are resolved above; none remain outstanding.
